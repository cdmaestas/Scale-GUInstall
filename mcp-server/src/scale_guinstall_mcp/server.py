"""
MCP tool registrations, wrapping scale-server.py's REST/SSE endpoints.
Every tool here is a thin, stateless passthrough: its parameters mirror
the corresponding backend endpoint's parameters exactly (decision 4 in
the design — "thin 1:1 wrappers"), and it holds no state of its own
beyond the shared ScaleBackendClient (token + base URL).

Read-only tools are simple request/response. Mutating ("start_*") tools
are shaped differently: a dry run is bounded and fast (the backend never
spawns a subprocess for one — see stream_process's dry_run short-circuit)
so it's fully drained and returned as a complete preview, same as a
read-only tool. A real run can take minutes, so it uses a fire-and-forget
pattern instead — see _mutate() below.
"""
from __future__ import annotations

import asyncio
import logging

from mcp.server.mcpserver import MCPServer

from .client import ScaleBackendClient, read_next_sse_event

mcp = MCPServer(
    "scale-guinstall",
    instructions=(
        "Tools for driving an IBM Storage Scale (GPFS) cluster install/admin session "
        "via the Scale GUInstall backend (scale-server.py), running on the installer "
        "node and reached over an SSH tunnel you set up yourself first "
        "(see SCALE_BACKEND_URL). Read-only tools are always safe to call. Mutating "
        "tools ('start_*') default to a dry run and must be explicitly told not to."
    ),
)

logger = logging.getLogger(__name__)

# A single shared client for the process's lifetime. Deliberately not using
# the SDK's Context/lifespan injection here — that machinery only resolves
# inside a real protocol session, which makes tool functions much harder to
# unit test directly (see mcp-server/tests/). A lazily-created module-level
# client keeps every tool function a plain, directly-callable async
# function.
_client: ScaleBackendClient | None = None


def get_client() -> ScaleBackendClient:
    global _client
    if _client is None:
        _client = ScaleBackendClient()
    return _client


def _events(events) -> list[dict]:
    return [{"type": e.type, "line": e.line} for e in events]


# asyncio.create_task() only holds a *weak* reference to the task it
# creates — with nothing else referencing it, the event loop is free to
# garbage-collect (and silently cancel) a still-running background drain.
# Keeping a strong reference here, released via the task's own
# done-callback, is exactly what the asyncio docs recommend for
# fire-and-forget tasks.
_background_tasks: set[asyncio.Task] = set()


def _track(task: asyncio.Task) -> None:
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _drain_stream(resp, line_iter) -> None:
    """Keep reading (and discarding) SSE lines from an already-open mutating
    response until the backend closes it, then close our end. Nothing reads
    the return value — the backend's operation buffer (check_operation) is
    the source of truth for progress and outcome, not this. Without this,
    abandoning the connection after reading just the first event would
    leave the backend's stream_process() generator suspended mid-yield.

    The client now opens this stream with no read timeout (see
    ScaleBackendClient.open_stream), so a healthy-but-quiet operation no
    longer ends up here on its own. If this loop does raise, it's a real
    failure — tunnel drop, backend restart, this process's own event loop
    stalling — and asyncio's default unhandled-task-exception handling
    would otherwise only log it (if at all) whenever this task happens to
    be garbage collected. Logging it explicitly, immediately, makes that
    failure visible instead of silently leaving check_operation as the
    only (much later) sign anything went wrong."""
    try:
        async for _ in line_iter:
            pass
    except Exception:
        logger.exception("Lost the drain connection for an in-progress operation")
    finally:
        await resp.aclose()


async def _mutate(
    method: str, path: str, dry_run: bool, params: dict | None = None, json_body: dict | None = None
) -> dict:
    """Shared shape for every start_* tool below.

    dry_run=True: fully drain the SSE response and return every event, same
    as a read-only tool — a dry run is validate-only and returns almost
    immediately, so there's no reason to truncate it.

    dry_run=False: read only the first SSE event (which tells us whether
    the backend accepted the request or rejected it as busy/invalid), then
    hand the still-open connection to a background task that keeps it
    drained for the operation's full duration, and return right away. Use
    check_operation to observe progress and the eventual result.
    """
    client = get_client()
    if dry_run:
        if method == "GET":
            return {"events": _events(await client.get_sse(path, params=params))}
        return {"events": _events(await client.post_sse(path, json_body=json_body))}

    resp = await client.open_stream(method, path, params=params, json_body=json_body)
    line_iter = resp.aiter_lines().__aiter__()
    first = await read_next_sse_event(line_iter)
    if first is None:
        await resp.aclose()
        return {"started": False, "message": "Backend closed the connection without sending any events."}
    if first.type in ("error", "busy"):
        await resp.aclose()
        return {"started": False, "message": first.line}

    _track(asyncio.create_task(_drain_stream(resp, line_iter)))
    return {"started": True, "message": first.line or "Operation started."}


# --- Simple JSON endpoints ---------------------------------------------------

@mcp.tool()
async def ping() -> dict:
    """Check that the backend is reachable and responding."""
    return await get_client().get_json("/api/ping")


@mcp.tool()
async def check_file(path: str) -> dict:
    """Check whether a file exists on the installer node. path must resolve
    under an allowed root (/tmp, /opt, /usr, /home, /root, /var, /srv, /mnt,
    /data, /ibm)."""
    return await get_client().get_json("/api/check-file", params={"path": path})


@mcp.tool()
async def browse_files(dir: str, ext: str = "") -> dict:
    """List filenames in a directory on the installer node, optionally
    filtered by extension (e.g. "zip"). dir must resolve under an allowed
    root."""
    return await get_client().get_json("/api/browse/files", params={"dir": dir, "ext": ext})


@mcp.tool()
async def probe_mmfs() -> dict:
    """Check /usr/lpp/mmfs for installed IBM Storage Scale versions; returns
    the latest version found and the path to the spectrumscale binary."""
    return await get_client().get_json("/api/probe/mmfs")


@mcp.tool()
async def probe_interfaces() -> dict:
    """Return non-loopback IPv4 addresses visible on the installer node."""
    return await get_client().get_json("/api/probe/interfaces")


@mcp.tool()
async def probe_cluster_nodes() -> dict:
    """Parse `mmlscluster` output on the installer node and return the
    cluster's node list as JSON."""
    return await get_client().get_json("/api/probe/cluster-nodes")


@mcp.tool()
async def spectrumscale_running() -> dict:
    """List any currently-running `spectrumscale` CLI invocations on the
    installer node (the toolkit only allows one at a time)."""
    return await get_client().get_json("/api/spectrumscale/running")


@mcp.tool()
async def list_nodes(toolkit: str) -> dict:
    """List nodes already configured in the cluster definition
    (`spectrumscale node list`). toolkit is the path to the spectrumscale
    binary on the installer node."""
    return await get_client().get_json("/api/list/nodes", params={"toolkit": toolkit})


@mcp.tool()
async def list_nsds(toolkit: str) -> dict:
    """List NSDs already configured in the cluster definition
    (`spectrumscale nsd list`)."""
    return await get_client().get_json("/api/list/nsds", params={"toolkit": toolkit})


@mcp.tool()
async def list_filesystem(toolkit: str) -> dict:
    """List filesystems already configured in the cluster definition
    (`spectrumscale filesystem list`)."""
    return await get_client().get_json("/api/list/filesystem", params={"toolkit": toolkit})


@mcp.tool()
async def list_config(toolkit: str) -> dict:
    """List GPFS cluster config settings already configured
    (`spectrumscale config gpfs --list`)."""
    return await get_client().get_json("/api/list/config", params={"toolkit": toolkit})


@mcp.tool()
async def get_config() -> dict:
    """Read the persisted GUI working state (configured nodes, NSDs,
    filesystem settings) shared with the web UI. Read-only in v1 — there is
    no save_config tool yet."""
    return await get_client().get_json("/api/config")


@mcp.tool()
async def check_operation() -> dict:
    """Check the single current-operation slot: what the most recent
    mutating operation is doing (or did), and whether it was started via
    the web UI or an MCP client. Returns {"status": "idle"} when nothing
    is running. This is the only way to observe a "start_*" tool's
    progress and output — those tools return as soon as the operation is
    accepted, not when it finishes."""
    return await get_client().get_json("/api/operation/current")


# --- SSE endpoints, fully drained (all fast: read-only, no long-running
#     orchestration commands in this group) -----------------------------

@mcp.tool()
async def checksum(dir: str) -> list[dict]:
    """Verify the Scale package's checksum files (`md5sum -c *.md5`) in the
    given working directory on the installer node."""
    return _events(await get_client().get_sse("/api/stream/checksum", params={"dir": dir}))


@mcp.tool()
async def checkpython() -> list[dict]:
    """Search the installer node for a Python >= 3.10 installation."""
    return _events(await get_client().get_sse("/api/stream/checkpython"))


@mcp.tool()
async def test_connection(node: str, user: str = "root", port: str = "22") -> list[dict]:
    """Test SSH connectivity and GPFS daemon state (`mmgetstate -a`) on a
    remote node from the installer node."""
    return _events(await get_client().get_sse(
        "/api/stream/test-connection", params={"node": node, "user": user, "port": port}))


@mcp.tool()
async def list_devices(node: str) -> list[dict]:
    """List block devices (`lsblk`) on a remote node, reached via SSH from
    the installer node — candidates for NSD creation."""
    return _events(await get_client().get_sse("/api/stream/list-devices", params={"node": node}))


@mcp.tool()
async def ccr_status() -> list[dict]:
    """Check whether CCR (Cluster Configuration Repository) is enabled on
    the cluster (`mmlscluster`)."""
    return _events(await get_client().get_sse("/api/stream/ccr-status"))


@mcp.tool()
async def check_ansible() -> list[dict]:
    """Check the installed ansible-core version for compatibility with the
    toolkit (2.24+ is incompatible)."""
    return _events(await get_client().get_sse("/api/stream/check-ansible"))


@mcp.tool()
async def check_locale() -> list[dict]:
    """Check the installer node's LC_ALL locale setting."""
    return _events(await get_client().get_sse("/api/stream/check-locale"))


# --- Mutating endpoints. Every tool takes dry_run=True by default — call
#     again with dry_run=False only once the preview looks right. -----------

@mcp.tool()
async def start_format_disk(node: str, device: str, dry_run: bool = True) -> dict:
    """Wipe a block device on a remote node (`wipefs -a`) so it's ready for
    NSD use. Destructive on the real run — always inspect the dry_run
    preview first. Only one mutating operation may be in flight at a time;
    use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/format-disk", dry_run,
        json_body={"node": node, "device": device, "dry_run": dry_run},
    )


@mcp.tool()
async def start_nsd_add(toolkit: str, nsds: list[dict], dry_run: bool = True) -> dict:
    """Add one or more NSDs to the cluster definition (`spectrumscale nsd
    add`). Each entry in nsds is a dict with keys: disk (required device
    path), server (required primary server hostname), backups (optional
    list of backup server hostnames, max 7), usage (dataAndMetadata,
    dataOnly, metadataOnly, descOnly, or logOnly), failureGroup, pool, and
    filesystem. Use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/nsd-add", dry_run,
        json_body={"toolkit": toolkit, "nsds": nsds, "dry_run": dry_run},
    )


@mcp.tool()
async def start_nsd_clear(toolkit: str, dry_run: bool = True) -> dict:
    """Wipe the toolkit's entire staged NSD list in one shot (`spectrumscale
    nsd clear -f`) — everything nsd add has configured, gone, so the next
    nsd add starts from empty. This only edits the toolkit's staged cluster
    definition, the same thing node add/delete edit; it does not touch the
    live GPFS filesystem or the disks themselves. There's no per-NSD delete
    tool yet — this is all-or-nothing. Use check_operation to see the
    result of a real run."""
    return await _mutate(
        "POST", "/api/stream/nsd-clear", dry_run,
        json_body={"toolkit": toolkit, "dry_run": dry_run},
    )


@mcp.tool()
async def start_config_populate(
    toolkit: str, node: str, skip_nsd: bool = False, overwrite: bool = False, dry_run: bool = True
) -> dict:
    """Sync the toolkit's staged cluster definition from a live GPFS cluster
    (`spectrumscale config populate -N <node>`) — reads the actual cluster
    state via the given already-a-member node instead of hand-staging nodes/
    NSDs. skip_nsd (`--skip nsd`) populates nodes only, skipping NSD
    discovery. overwrite answers the toolkit's own confirmation prompt when
    a cluster definition already exists (y if True, n if False) — the
    process never sits waiting on invisible interactive input either way.
    Use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/populate", dry_run,
        json_body={
            "toolkit": toolkit, "node": node, "skip_nsd": skip_nsd,
            "overwrite": overwrite, "dry_run": dry_run,
        },
    )


@mcp.tool()
async def start_node_config(toolkit: str, nodes: list[dict], dry_run: bool = True) -> dict:
    """Configure nodes in the cluster definition (`spectrumscale node add`,
    replacing any prior definition of the same node). Each entry in nodes
    is a dict with keys: hostname (required) and roles (list of zero or
    more of: nsd, manager, quorum, admin, protocol, gui, ems, callhome).
    Use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/nodes", dry_run,
        json_body={"toolkit": toolkit, "nodes": nodes, "dry_run": dry_run},
    )


@mcp.tool()
async def kill_spectrumscale(dry_run: bool = True) -> dict:
    """Kill any running `spectrumscale` CLI invocations on the installer
    node (SIGTERM, then SIGKILL after 2s if still alive). Never touches the
    backend service itself. This is a synchronous JSON call, not a stream —
    it returns once the kill (or its dry-run preview) is complete."""
    return await get_client().post_json("/api/spectrumscale/kill", {"dry_run": dry_run})


@mcp.tool()
async def start_cluster_config_apply(
    toolkit: str,
    gpfs_flags: list[dict] | None = None,
    callhome: bool = False,
    perfmon: bool = True,
    perfmon_node: str = "",
    fileaudit: bool = False,
    fileaudit_fs: str = "",
    dry_run: bool = True,
) -> dict:
    """Apply cluster-wide GPFS configuration: a batch of `spectrumscale
    config gpfs <flag> [value]` calls (gpfs_flags is a list of dicts with
    keys flag and value), plus optionally enabling call home, performance
    monitoring (perfmon_node required if perfmon is true), and file audit
    logging (fileaudit_fs required if fileaudit is true). perfmon defaults
    to True — performance monitoring should be on by default; pass
    perfmon=False to explicitly turn it off instead. Every gpfs_flags/
    callhome/perfmon/fileaudit value is always applied explicitly (on or
    off) each call, not left unchanged, so a call that only needs to set a
    gpfs flag will also explicitly disable callhome/fileaudit and enable
    perfmon unless told otherwise. Use check_operation to see the result
    of a real run."""
    return await _mutate(
        "POST", "/api/stream/apply-cluster-config", dry_run,
        json_body={
            "toolkit": toolkit,
            "gpfs_flags": gpfs_flags or [],
            "callhome": callhome,
            "perfmon": perfmon,
            "perfmon_node": perfmon_node,
            "fileaudit": fileaudit,
            "fileaudit_fs": fileaudit_fs,
            "dry_run": dry_run,
        },
    )


@mcp.tool()
async def start_phase(
    toolkit: str, phase: str, skip_ssh: bool = False, confirm: bool = False, dry_run: bool = True
) -> dict:
    """Run one install/deploy/upgrade phase of the spectrumscale toolkit.
    phase is one of: precheck-install, install, postcheck-install,
    enable-daemon, nodeid-define, precheck-deploy, deploy, postcheck-deploy,
    upgrade-precheck, upgrade-run, upgrade-postcheck, upgrade-showversions.
    skip_ssh only applies to phases that support it. confirm answers "y" to
    an interactive confirmation prompt some phases raise — confirmed live:
    upgrade-run asks "Do you want to continue the parallel offline upgrade
    process? [y/N]" when every node is designated offline (via
    start_upgrade_offline_nodes); without confirm=true it hits EOF on
    stdin and fails with "An unexpected error occurred" instead of
    running. Use check_operation to see the result of a real run."""
    return await _mutate(
        "GET", "/api/stream/phase", dry_run,
        params={
            "toolkit": toolkit, "phase": phase, "skip_ssh": skip_ssh,
            "confirm": confirm, "dry_run": dry_run,
        },
    )


@mcp.tool()
async def start_upgrade_offline_nodes(toolkit: str, nodes: list[str], dry_run: bool = True) -> dict:
    """Designate nodes for an offline upgrade (`spectrumscale upgrade config
    offline -N <node1,node2,...>`). A subsequent start_phase(phase=
    "upgrade-run") will upgrade these nodes' packages WITHOUT restarting
    GPFS on them — `mmstartup` must be run manually on each afterward.
    Nodes not designated offline get the toolkit's normal automatic
    rolling/online upgrade instead. There is no corresponding "mark online
    again" toolkit subcommand, so this only designates nodes offline, never
    reverts it. Use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/upgrade/offline-nodes", dry_run,
        json_body={"toolkit": toolkit, "nodes": nodes, "dry_run": dry_run},
    )


@mcp.tool()
async def start_gpfs_shutdown(nodes: list[str], dry_run: bool = True) -> dict:
    """Run `mmshutdown -N <node1,node2,...>` to stop the GPFS daemon on the
    given nodes. Required before start_upgrade_offline_nodes will accept a
    node — confirmed live, it refuses with "cannot be designated for
    offline upgrade until the GPFS daemon running on the node is stopped"
    otherwise. Use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/gpfs/shutdown", dry_run,
        json_body={"nodes": nodes, "dry_run": dry_run},
    )


@mcp.tool()
async def start_gpfs_startup(nodes: list[str], dry_run: bool = True) -> dict:
    """Run `mmstartup -N <node1,node2,...>` to start the GPFS daemon on the
    given nodes. The manual step an offline-upgraded node needs afterward
    — start_phase(phase="upgrade-run") deliberately never restarts GPFS on
    nodes designated offline via start_upgrade_offline_nodes. Use
    check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/gpfs/startup", dry_run,
        json_body={"nodes": nodes, "dry_run": dry_run},
    )


@mcp.tool()
async def start_release_latest(dry_run: bool = True) -> dict:
    """Run `mmchconfig release=LATEST -i` to activate the highest cluster
    functionality level supported by every currently-installed node's
    packages. Only meaningful after every node has already been upgraded
    (start_phase(phase="upgrade-run") only upgrades packages — it never
    bumps the cluster's effective release level itself). Use
    check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/postupgrade/release-latest", dry_run,
        json_body={"dry_run": dry_run},
    )


@mcp.tool()
async def start_filesystem_version(device: str, version: str = "full", dry_run: bool = True) -> dict:
    """Run `mmchfs <device> -V full|compat` to activate the on-disk
    filesystem format matching the cluster's current release level (full)
    or the latest format still compatible with older, not-yet-upgraded
    nodes (compat). version must be exactly "full" or "compat". Typically
    run after start_release_latest. Use check_operation to see the result
    of a real run."""
    return await _mutate(
        "POST", "/api/stream/postupgrade/filesystem-version", dry_run,
        json_body={"device": device, "version": version, "dry_run": dry_run},
    )


@mcp.tool()
async def start_callhome(toolkit: str, enable: bool = False, dry_run: bool = True) -> dict:
    """Run `spectrumscale callhome enable|disable`. Call home is enabled
    by default in the install toolkit (5.0.0+) but must be either
    disabled or configured before `install --precheck` will pass — it
    fails with a FATAL if call home is enabled with no settings
    configured. enable=False (the default) disables it. Use
    check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/callhome", dry_run,
        json_body={"toolkit": toolkit, "enable": enable, "dry_run": dry_run},
    )


@mcp.tool()
async def start_protocols_config(
    toolkit: str,
    filesystem: str,
    mountpoint: str,
    interface: str = "",
    export_ip_pool: str = "",
    dry_run: bool = True,
) -> dict:
    """Run `spectrumscale config protocols -f <filesystem> -m <mountpoint>
    [-i <interface>] [-e <export_ip_pool>]` to set the CES shared-root
    filesystem/mountpoint and (optionally) the network interface and a
    comma-separated list of additional CES export IPs. Required before
    start_protocols_enable will actually bring NFS/SMB/S3 up — a
    successful start_phase(phase="deploy") only installs and activates CES
    infrastructure, it never runs this itself. Use check_operation to see
    the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/protocols/config", dry_run,
        json_body={
            "toolkit": toolkit, "filesystem": filesystem, "mountpoint": mountpoint,
            "interface": interface, "export_ip_pool": export_ip_pool, "dry_run": dry_run,
        },
    )


@mcp.tool()
async def start_protocols_enable(toolkit: str, protocols: list[str], dry_run: bool = True) -> dict:
    """Run `spectrumscale enable <protocol> [<protocol> ...]` to turn on
    one or more of s3/smb/nfs/hdfs. Requires start_protocols_config (CES
    shared-root filesystem/mountpoint) to already be set. Use
    check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/protocols/enable", dry_run,
        json_body={"toolkit": toolkit, "protocols": protocols, "dry_run": dry_run},
    )


@mcp.tool()
async def start_setup(dir: str, ip: str, bin: str = "", dry_run: bool = True) -> dict:
    """Run `spectrumscale setup -s <ip>`, installing the toolkit's
    installation service. dir is the working directory containing the
    extracted toolkit (spectrumscale is found under ansible-toolkit/,
    installer/, or dir itself); bin overrides this with a full path to the
    spectrumscale binary. This is the longest-running v1 operation. Use
    check_operation to see the result of a real run."""
    return await _mutate(
        "GET", "/api/stream/setup", dry_run,
        params={"dir": dir, "ip": ip, "bin": bin, "dry_run": dry_run},
    )


# ---------------------------------------------------------------------------
# Post-configuration tools — mirror the web UI's "Post Configuration" page,
# which had all six of these wired but was never ported to MCP.
# ---------------------------------------------------------------------------

@mcp.tool()
async def start_profiled(binpath: str = "/usr/lpp/mmfs/bin", dry_run: bool = True) -> dict:
    """Create /etc/profile.d/gpfs.sh so GPFS binaries are on PATH for all
    users after login. Use check_operation to see the result of a real
    run."""
    return await _mutate(
        "GET", "/api/stream/postconfig/profiled", dry_run,
        params={"binpath": binpath, "dry_run": dry_run},
    )


@mcp.tool()
async def start_guiuser(username: str, password: str, role: str = "SecurityAdmin", dry_run: bool = True) -> dict:
    """Create a GUI admin/user account (`/usr/lpp/mmfs/gui/cli/mkuser`).
    role must be one of: SecurityAdmin, SystemAdmin, CopyAdmin, DataAccess,
    Monitor. Use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/postconfig/guiuser", dry_run,
        json_body={"username": username, "password": password, "role": role, "dry_run": dry_run},
    )


@mcp.tool()
async def start_mmchconfig_tunables(
    max_files_to_cache: str = "",
    max_stat_cache: str = "",
    pagepool: str = "",
    max_mbps: str = "",
    dry_run: bool = True,
) -> dict:
    """Apply GPFS runtime performance tunables via `mmchconfig <key>=<value>
    -i` — one call per non-empty value given (maxFilesToCache, maxStatCache,
    pagepool, maxMBpS). At least one must be set. Named distinctly from
    start_cluster_config_apply's gpfs_flags (a different, allowlisted set
    of config flags) to avoid confusion between the two. Use
    check_operation to see the result of a real run."""
    return await _mutate(
        "GET", "/api/stream/postconfig/mmchconfig", dry_run,
        params={
            "maxFilesToCache": max_files_to_cache, "maxStatCache": max_stat_cache,
            "pagepool": pagepool, "maxMBpS": max_mbps, "dry_run": dry_run,
        },
    )


@mcp.tool()
async def start_healthinterval(interval: str = "DEFAULT", nodes: str = "all", dry_run: bool = True) -> dict:
    """Set the `mmhealth` monitoring check interval (`mmhealth config
    interval <interval> -N <nodes>`). interval must be one of: OFF, LOW,
    MEDIUM, DEFAULT, HIGH. nodes defaults to "all". Use check_operation to
    see the result of a real run."""
    return await _mutate(
        "GET", "/api/stream/postconfig/healthinterval", dry_run,
        params={"interval": interval, "nodes": nodes, "dry_run": dry_run},
    )


@mcp.tool()
async def start_nfs_core_dump(toolkit: str, mode: str = "enable", dry_run: bool = True) -> dict:
    """Enable or disable NFS core dump collection on protocol nodes
    (`spectrumscale nfs_core_dump enable|disable`, 6.0.1+) — useful for
    troubleshooting NFS Ganesha crashes. mode must be "enable" or
    "disable". Use check_operation to see the result of a real run."""
    return await _mutate(
        "POST", "/api/stream/nfs-core-dump", dry_run,
        json_body={"toolkit": toolkit, "mode": mode, "dry_run": dry_run},
    )


@mcp.tool()
async def start_afmgateway(
    fs: str,
    fileset: str,
    node: str,
    proto: str = "nfs",
    mode: str = "ro",
    nfs_target: str = "",
    s3_url: str = "",
    s3_bucket: str = "",
    s3_key: str = "",
    s3_secret: str = "",
    dry_run: bool = True,
) -> dict:
    """Create an AFM (Active File Management) fileset on fs linked to an
    NFS or S3 home target, run from the given gateway node: creates the
    independent fileset (`mmcrfileset`), points it at the target
    (`mmafmconfig` — nfs_target required when proto="nfs"; s3_url/
    s3_bucket/s3_key/s3_secret all required when proto="s3"), then links
    it under /ibm/<fs>/<fileset> (`mmlinkfileset`). mode must be one of:
    ro, rw, sw, iw, lg. Use check_operation to see the result of a real
    run."""
    return await _mutate(
        "POST", "/api/stream/postconfig/afmgateway", dry_run,
        json_body={
            "fs": fs, "fileset": fileset, "node": node, "proto": proto, "mode": mode,
            "nfs_target": nfs_target, "s3_url": s3_url, "s3_bucket": s3_bucket,
            "s3_key": s3_key, "s3_secret": s3_secret, "dry_run": dry_run,
        },
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
