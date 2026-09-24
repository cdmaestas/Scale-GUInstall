# IBM TechZone Runbook: Install → Deploy via MCP

End-to-end guide for standing up an IBM Storage Scale (GPFS) cluster on an
IBM TechZone VSI environment, driven entirely through the `scale-guinstall`
MCP tools rather than the web UI. Written from a real run against a fresh
TechZone environment; every step and every gotcha in here was hit live, not
theorized.

**Assumes**: the IBM Storage Scale software is already extracted on the
installer node (typically the "bastion" host in TechZone's naming), and you
have SSH access to the bastion with a private key.

## 0. TechZone topology, at a glance

TechZone VSI environments follow a predictable naming and network pattern:

- A **bastion** node (`scale-bastion-*`) — public-facing, reachable from your
  workstation, but **not** a GPFS cluster member. It's the installer node
  only. Don't add it to the cluster.
- Cluster nodes on a private subnet, named by role: `scale-server*` (storage/
  NSD nodes), `scale-proto*` (protocol/CES nodes), `scale-gui*` (GUI/admin
  node), `scale-client*` (plain GPFS clients).
- Protocol nodes typically have **two interfaces**: a primary (`eth0`, same
  private subnet as everything else) and a secondary (`eth1`) that's the
  external-facing interface for CES export IPs.
- `/etc/hosts` on the bastion lists every node with multiple aliases per
  line — grep it for `scale` to get your node inventory and IPs before doing
  anything else.

## 1. Start the backend, then the SSH tunnel

### Keep `scale-server.py` running independently of your SSH session

**Don't run `./start.sh` directly in the foreground of the SSH session
you're about to tunnel through.** If that session drops or times out —
which an idle TechZone bastion connection will eventually do — the
backend dies with it, and any long-running operation you're polling
(install, deploy, upgrade) becomes unreachable via `check_operation`
even though it's still running fine as its own process on the installer
node. (Confirmed live: `ping` and `check_operation` both started
hard-failing mid-deploy with no tunnel-side symptom, traced back to the
`start.sh` session itself having been dropped.)

Run it in `tmux`/`screen` instead, so it survives your SSH session:

```bash
tmux new -s scale-guinstall
./start.sh
# Ctrl-b d to detach; tmux attach -t scale-guinstall to reattach
```

The more durable option, if you have package-manager access on the
installer node, is installing the packaged RPM/DEB
(`packaging/build-pkg.sh` output) and using its systemd unit
(`scale-guinstall.service`, installed but not enabled by default) —
`systemctl enable --now scale-guinstall` keeps it running independent of
any SSH session entirely, which is how a real (non-TechZone-demo)
deployment should run it.

**Restarting `scale-server.py` loses operation tracking, even though the
underlying toolkit operation keeps running.** The single-slot "current
operation" `check_operation` reads from is in-memory, not persisted to
disk. If the backend restarts (crash, session drop, manual restart) while
`install`/`deploy`/`upgrade` is still running on the installer node, the
new backend process comes up with `check_operation` reporting `"status":
"idle"` — it has no idea anything was ever running. The toolkit operation
itself is unaffected (it's a separate process tree), but you lose the
ability to see its progress or final result through this MCP/GUI
interface.

There's no tool here that reads the toolkit's own log files (`browse_files`
only lists filenames, `check_file` only checks existence) to recover the
lost state, so if this happens: `spectrumscale_running` tells you whether
the toolkit process is still going, and if it's finished, the safest
recovery is to just re-run the same phase — `install`/`deploy` are
idempotent Ansible-based operations, so re-running is safe and gives you a
fresh, trustworthy result rather than leaving you guessing at stale logs.

### SSH tunnel

The MCP server talks to `scale-server.py` over `http://127.0.0.1:5001`,
reached through an SSH tunnel you set up by hand:

```bash
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -L 5001:127.0.0.1:5001 \
    -i <path-to-key>.pem -p <ssh-port> itzuser@<bastion-public-ip>
```

The `ServerAliveInterval`/`ServerAliveCountMax` keepalive options matter —
without them, an idle NAT or firewall can silently drop the tunnel during
the long quiet stretches install/deploy/upgrade phases have, and you won't
notice until the next command fails.

### Known TechZone gotcha: `administratively prohibited`

If the tunnel connects but every port-forward request fails with:

```
channel 3: open failed: administratively prohibited: open failed
```

this is **not a network firewall** — it's the bastion's own `sshd` refusing
the forward. TechZone bastions are commonly built from a security-hardened
base image via a ComplianceAsCode/OpenSCAP-style Ansible role that sets:

```
DisableForwarding yes
```

in a drop-in under `/etc/ssh/sshd_config.d/` (commonly
`00-complianceascode-hardening.conf`). This directive overrides *every*
other forwarding-related setting, including any `AllowTcpForwarding yes`
elsewhere — and because `/etc/ssh/sshd_config`'s `Include` line pulls in
`sshd_config.d/*.conf` before the rest of the main file, the drop-in wins
regardless of what's in the main config.

**Fix**, on the bastion:

```bash
sudo grep -rn "DisableForwarding" /etc/ssh/sshd_config.d/
# comment out the "DisableForwarding yes" line found there, e.g.:
sudo sed -i 's/^DisableForwarding yes/#DisableForwarding yes/' \
    /etc/ssh/sshd_config.d/00-complianceascode-hardening.conf
sudo sshd -t && sudo systemctl restart sshd
```

**Then reconnect with a brand-new SSH session** — an already-open tunnel
was negotiated against the old config and won't pick up the fix on its own;
a `systemctl restart` doesn't retroactively fix a live connection.

Verify effective config directly rather than hand-tracing `Include` order:

```bash
sudo sshd -T | grep -i forward
# want: allowtcpforwarding yes / disableforwarding no
```

### Confirm connectivity

Once the tunnel is up, from the MCP client:

```
ping                    → {"ok": true}
```

If `ping` fails outright (not a normal tool error), suspect the tunnel
before suspecting the backend — check the local end is actually listening
(`lsof -nP -iTCP:5001`) and whether a raw `curl http://127.0.0.1:5001/`
connects-then-resets (classic sign of the sshd issue above) vs. hangs
(classic sign the tunnel itself never came up).

## 2. Confirm prerequisites

```
probe_mmfs           → confirms the extracted version and toolkit_path
check_ansible         → confirms ansible-core is present and compatible
probe_interfaces       → the installer node's own IP, for setup -s
```

`probe_mmfs` doubles as your extraction check: `{"found": false}` means the
software archive hasn't been extracted on the installer node yet, not a
bug. If you hit that on a "fresh" environment, confirm with whoever set it
up whether extraction is still in progress before searching around for the
archive yourself.

## 3. Toolkit setup

```
start_setup(dir=<extracted-path>, ip=<installer-node-ip>, dry_run=true)   # preview
start_setup(dir=<extracted-path>, ip=<installer-node-ip>, dry_run=false)  # real
```

This installs the toolkit's Ansible-based installation service. It's fast
(seconds), despite being documented as the longest-running v1 operation —
that description is about worst-case, not typical.

## 4. Node configuration

Read `/etc/hosts` (grep for `scale`) to get your node list and decide
roles. A reasonable default split for a 7-node TechZone environment
(2 storage, 2 protocol, 1 GUI, 2 clients), **excluding the bastion**:

| Node | Roles |
|---|---|
| `scale-server1`, `scale-server2` | `nsd`, `manager`, `quorum` |
| `scale-gui1` | `gui`, `quorum`, `admin` |
| `scale-proto1`, `scale-proto2` | `protocol`, `manager` |
| `scale-client1`, `scale-client2` | *(none)* |

Three quorum nodes (odd number, standard practice). Confirm your own
topology's actual role split with whoever owns the environment before
committing to this — it's a real architectural decision, not a default to
apply blindly.

```
start_node_config(
  toolkit=<toolkit_path>,
  nodes=[
    {"hostname": "scale-server1", "roles": ["nsd","manager","quorum"]},
    {"hostname": "scale-server2", "roles": ["nsd","manager","quorum"]},
    {"hostname": "scale-gui1",    "roles": ["gui","quorum","admin"]},
    {"hostname": "scale-proto1",  "roles": ["protocol","manager"]},
    {"hostname": "scale-proto2",  "roles": ["protocol","manager"]},
    {"hostname": "scale-client1", "roles": []},
    {"hostname": "scale-client2", "roles": []}
  ],
  dry_run=false
)
```

Expect two harmless lines per node in the output: a `[FATAL] Node ... does
not exist` (from the tool's delete-before-add pattern, normal on first
run) and a `[WARN] Found a mis-ordered line in the /etc/hosts file` — the
toolkit wants `<IP> <FQDN> <ALIAS>` order and TechZone's hosts entries
often put the short alias first. It's usually safe to ignore for install,
but if `install`/`deploy` later fails on something DNS/hostname-shaped,
fix `/etc/hosts` ordering on the affected node first.

## 5. Storage discovery and NSD/filesystem design

```
list_devices(node="scale-server1")
list_devices(node="scale-server2")
```

On TechZone VMs, expect `vda`/`vdb`/`vdc` (OS, install media, swap — in
use) plus a few unused `vdd`/`vde`/`vdf`-style virtio disks. These are
**node-local virtual disks**, not shared storage — confirm this if you
need certainty (no reliable way to check `/dev/disk/by-id` from these
tools; ask whoever built the environment, or check on the node directly).

Design NSDs/failure groups around that: one failure group per server node
is the natural split for node-local disks. A common pattern — a small
`cesSharedRoot` filesystem for protocol nodes, and a `fs1` with separate
system (metadata) and data pools:

```
start_nsd_add(
  toolkit=<toolkit_path>,
  nsds=[
    {"disk":"/dev/vdd","server":"scale-server1","failureGroup":"1","usage":"dataAndMetadata","pool":"system","filesystem":"cesSharedRoot"},
    {"disk":"/dev/vde","server":"scale-server1","failureGroup":"1","usage":"dataAndMetadata","pool":"system","filesystem":"fs1"},
    {"disk":"/dev/vdf","server":"scale-server1","failureGroup":"1","usage":"dataOnly","pool":"data","filesystem":"fs1"},
    {"disk":"/dev/vdd","server":"scale-server2","failureGroup":"2","usage":"dataAndMetadata","pool":"system","filesystem":"cesSharedRoot"},
    {"disk":"/dev/vde","server":"scale-server2","failureGroup":"2","usage":"dataAndMetadata","pool":"system","filesystem":"fs1"},
    {"disk":"/dev/vdf","server":"scale-server2","failureGroup":"2","usage":"dataOnly","pool":"data","filesystem":"fs1"}
  ],
  dry_run=false
)
```

If you need to redo this (wrong assignment, want to start over):
`start_nsd_clear` wipes the whole staged list — all or nothing, no
per-NSD delete.

## 6. First precheck — expect a callhome FATAL

```
start_phase(toolkit=<toolkit_path>, phase="precheck-install", dry_run=false)
```

**Expect this to fail the first time**, with:

```
[ FATAL ] With 5.0.0.0 and onward, callhome is enabled by default...
There are currently no configured callhome settings.
```

Call home is on by default since Storage Scale 5.0.0 and has no config —
disable it (or configure it properly, if you actually want call home):

```
start_callhome(toolkit=<toolkit_path>, enable=false, dry_run=false)
```

Also worth setting while you're touching cluster config — the precheck
output usually recommends an ephemeral port range too:

```
start_cluster_config_apply(
  toolkit=<toolkit_path>,
  gpfs_flags=[{"flag":"--ephemeral_port_range","value":"60000-61000"}],
  perfmon=true,
  dry_run=false
)
```

(`perfmon=true` is the tool's default — pass it explicitly if you want to
be sure, or `false` if you don't want performance monitoring.)

Re-run `precheck-install` — should now pass cleanly (`Pre-check successful
for install.`). Remaining WARNs (OS repos, NSD load-balancing, single-GUI-
server) are cosmetic/expected for a node-local-disk, single-GUI TechZone
layout.

## 7. Install

```
start_phase(toolkit=<toolkit_path>, phase="install", dry_run=false)
```

This is the real, long-running one — expect roughly 25–35 minutes for a
7-node cluster: package install, GPL module compile, `mmcrcluster`, NSD
creation, filesystem creation, AFM/COS, performance monitoring, GUI, file
audit logging packages, all across every node. Poll with `check_operation`
periodically rather than continuously — the operation log grows large
enough that `check_operation` itself will eventually exceed the tool
result size limit; when it does, the error message includes a path to a
saved file you can `tail`/`grep` instead of re-reading the whole thing.

Success looks like:
```
[ INFO ] SUCCESS
[ INFO ] All services running
[ INFO ] Installation successful. N GPFS nodes active in cluster <name>. Completed in ...
```
(Confirmed live: 31 minutes 6 seconds for a 7-node cluster — squarely
inside the estimate above.)

If a poll during this stretch suddenly errors on *every* tool, including
`ping`, first check the tunnel itself (a keepalive gap or NAT/firewall
timeout can drop it despite the `ServerAliveInterval` settings from §1) —
but if the tunnel looks fine and `ping` still fails repeatedly, suspect
`scale-server.py` itself: if it's running in the foreground of an SSH
session (see §1's warning about `tmux`), that session dying takes the
backend with it. Either way, the install/deploy operation itself is
driven by the toolkit on the installer node and keeps running
independently — restoring the tunnel and/or restarting the backend under
`tmux` (or checking the systemd service, if packaged) lets
`check_operation` pick the same operation back up where it left off.

## 8. Protocols (NFS/SMB/S3) — do this before `deploy`, not after

**This is the step most likely to be skipped**, because `deploy` will
"succeed" without it — it just won't actually turn any protocol on.
`spectrumscale deploy` only installs and activates CES *infrastructure*
(packages, the CES daemon, GUI, perfmon); it never runs `config protocols`
or `enable <protocol>` itself. If you skip this and run `deploy`, you'll
get a fully "successful" deploy with NFS/SMB/S3 all still `Disabled` in
`node list`.

```
start_protocols_config(
  toolkit=<toolkit_path>,
  filesystem="cesSharedRoot",
  mountpoint="/ibm/cesSharedRoot",
  interface="eth1",
  export_ip_pool="<proto1-secondary-ip>,<proto2-secondary-ip>",
  dry_run=false
)
```

Use the protocol nodes' **secondary** (`eth1`-style) interface and IPs
here — that's the externally-facing one TechZone provisions for CES. You
may see a `[WARN] CIDR value has not been passed with Export ces ip's` —
non-blocking; pass IPs in CIDR form (e.g. `10.x.x.x/24`) instead of bare
IPs if you want the toolkit's newer routing-table-aware mode instead of
legacy mode.

**There's no MCP tool that reads these IPs for you.** `probe_cluster_nodes`
runs `mmlscluster` locally on the installer node, which hits the same
bastion-isn't-a-cluster-member gap described in §10 (`mmlscluster: command
not found`) — it can't see the cluster from there. Get the secondary IPs
straight from `/etc/hosts` on the bastion instead:
```bash
grep proto /etc/hosts
# 10.249.129.232 scale-proto1 scale-proto1-eth0 scale-proto1-primary
# 10.249.128.70  scale-proto1-eth1 scale-proto1-secondary
# 10.249.129.227 scale-proto2 scale-proto2-eth0 scale-proto2-primary
# 10.249.128.72  scale-proto2-eth1 scale-proto2-secondary
```
The `-secondary`/`-eth1` addresses (a different subnet than the primary
cluster network) are what go in `export_ip_pool`.

Then enable whichever protocols you actually want:

```
start_protocols_enable(toolkit=<toolkit_path>, protocols=["nfs","smb"], dry_run=false)
# and/or, separately:
start_protocols_enable(toolkit=<toolkit_path>, protocols=["s3"], dry_run=false)
```

(S3 needs the extracted media's `s3_rpms/` directory to exist — check
`browse_files(dir=<extracted-path>)` if `enable` fails with missing
packages.)

Re-run `precheck-deploy` — you should see `<protocol> precheck OK` for
each one you enabled.

## 9. Deploy

```
start_phase(toolkit=<toolkit_path>, phase="precheck-deploy", dry_run=false)  # confirm clean
start_phase(toolkit=<toolkit_path>, phase="deploy", dry_run=false)
```

Note that `precheck-deploy` only validates readiness to deploy — it does
**not** tell you whether CES/protocols are already active from a prior
run. It looks identical whether `deploy` never ran, failed, or already
succeeded. If you're ever unsure of current state (e.g. after losing
`check_operation` visibility — see §1's `tmux` note), the reliable move is
just to re-run `deploy` itself: the toolkit is Ansible-based and
idempotent, so re-running it against an already-deployed cluster is safe
and gives you a fresh, definitive post-deploy status.

Budget more than the toolkit's own "shorter than install" framing
suggests — confirmed live: 10–15 minutes if everything comes up healthy
on the first pass, but if CES/NFS fail their health checks (see below)
the toolkit burns an extra ~5 minutes per protocol running 5 retries at a
30-second interval, and a second deploy attempt re-installs/re-verifies
most of it from scratch rather than resuming. One live run took 22m44s
end to end because of this.

If S3 is enabled, expect a **second, separate Ansible play** after the
main one — `s3_prepare`/`s3_install`/`ces_common`-for-S3 tasks running
after the first `PLAY RECAP`, with its own `S3 precheck ok` /
`PLAY RECAP`. This is normal; don't mistake it for the deploy hanging or
restarting.

Success looks like:
```
[ INFO ] SUCCESS
[ INFO ] All services running
[ INFO ] Successfully installed protocol packages on N protocol nodes. ...
```

**Verify, don't just trust the exit message** — check the post-install
checks section specifically for each component:
```
Filesystem ACTIVE
Cluster Export Services ACTIVE
Performance Monitoring ACTIVE
GUI ACTIVE
```

### Known issue: CES/NFS `NOT ACTIVE` despite `failed=0` everywhere

**Seen live twice, on two independent TechZone environments** — this
looks like a reproducible pattern, not a one-off fluke. Both Ansible
plays complete with `failed=0` across every node (the toolkit did
everything it was told to), S3 and SMB come up `ACTIVE`, but CES and NFS
fail their post-deploy health check on the protocol nodes:

```
[ INFO ] CES not healthy on all nodes
[ INFO ] Attempt 1 of 5 ... Attempt 5 of 5
[ WARN ] CES is not healthy on: <proto1>, <proto2>.
[ FATAL ] Cluster Export Services NOT ACTIVE
...
[ FATAL ] NFS NOT ACTIVE
...
[ FATAL ] Not all services available on specified nodes
```

The overall deploy exit status is `error` even though Performance
Monitoring and GUI come up fine right after. Since the toolkit's own
5-attempt retry loop already exhausted itself, re-running `deploy` a
third time is unlikely to help on its own — this needs direct
investigation **on the protocol nodes themselves**, not through this MCP
toolset (the bastion `mmcmd()` gap in §10 means `mmces`/`mmhealth` won't
run from here anyway):

```bash
mmces state show -a
mmhealth node show -N <proto-node>
# and check the Ganesha/NFS daemon directly, e.g.:
journalctl -u gpfs-ces
# or wherever Ganesha logs on your distro
```

Root cause not yet identified as of this writing — candidates worth
checking first: CES export-IP (`eth1`) reachability/routing from the
toolkit's health-check perspective, and whether the Ganesha NFS daemon is
actually starting (crash-looping) on the protocol nodes.

## 10. Post-configuration (optional, as needed)

```
start_profiled(nodes=[<cluster-node-list>], dry_run=false)
  # adds /usr/lpp/mmfs/bin to PATH on each given cluster node over SSH —
  # NOT the bastion (GPFS isn't installed there; see the gotcha below)

start_nfs_core_dump(toolkit=<toolkit_path>, mode="enable", dry_run=false)
  # useful pre-emptively if you're going to be exercising NFS/CES —
  # gives you a real dump to inspect if Ganesha crashes

start_healthinterval(interval="HIGH", nodes="all", dry_run=false)
start_mmchconfig_tunables(pagepool="4G", dry_run=false)
start_afmgateway(...)
start_guiuser(username=..., password=..., role="SecurityAdmin", dry_run=false)
```

### Known gotcha: `mmhealth`/`mmchconfig`/`mmlscluster` "command not found"

`start_healthinterval`, `start_mmchconfig_tunables`,
`start_release_latest`/`start_filesystem_version`, `start_afmgateway`,
`start_gpfs_shutdown`/`start_gpfs_startup`, and `ccr_status` all run their
`mm*` command as a **local subprocess on whatever host `scale-server.py`
itself runs on**. If that's the bastion — which, per §0, isn't a cluster
member — GPFS isn't installed there at all, and every one of these fails
with `sudo: /usr/lpp/mmfs/bin/mmXXX: command not found`.

This is a known, currently-unfixed architecture gap (as of this writing,
not yet built): these endpoints need to SSH to a designated cluster node
instead of assuming local GPFS binaries, the same way `start_profiled` was
reworked to do. Until that lands, anything routed through the
`spectrumscale` **toolkit** binary (`install`, `deploy`, `upgrade`,
`config protocols`/`enable`, `callhome`, node/NSD config,
`cluster-config-apply`'s `config gpfs` flags) works fine regardless of
where the backend runs, since the toolkit orchestrates execution against
real cluster nodes itself. `start_profiled` and `start_nfs_core_dump` also
work today, since both were built to SSH to specified nodes rather than
assume local binaries.

For credential-bearing tools like `start_guiuser`: don't paste a real
password into an AI agent's chat. Either have the agent generate a
temporary one you rotate immediately after first login, or run the
`mkuser` command yourself directly on the node.

## 11. Sanity checks after everything's up

```
mmgetstate -a          # from any cluster node directly — confirm GPFS active everywhere
                        # (test_connection's built-in mmgetstate check has a known bug:
                        #  it runs the bare command over non-interactive ssh, which
                        #  doesn't have /usr/lpp/mmfs/bin on PATH — fixed in 1.3.0, but
                        #  confirm your backend version has the fix)
```

Also worth eyeballing directly on a node if anything reported `NOT ACTIVE`
during deploy:
```bash
mmces state show -a
mmhealth node show -N <protocol-node>
```

---

## Appendix: fast reference — the whole sequence

```
ping
probe_mmfs
check_ansible
probe_interfaces
start_setup(dir, ip, dry_run=false)
start_node_config(toolkit, nodes=[...], dry_run=false)
list_devices(node) × each storage node
start_nsd_add(toolkit, nsds=[...], dry_run=false)
start_phase(toolkit, phase="precheck-install", dry_run=false)   # expect callhome FATAL
start_callhome(toolkit, enable=false, dry_run=false)
start_cluster_config_apply(toolkit, gpfs_flags=[...ephemeral_port_range...], perfmon=true, dry_run=false)
start_phase(toolkit, phase="precheck-install", dry_run=false)   # now clean
start_phase(toolkit, phase="install", dry_run=false)             # ~25-35 min
start_protocols_config(toolkit, filesystem, mountpoint, interface, export_ip_pool, dry_run=false)
start_protocols_enable(toolkit, protocols=[...], dry_run=false)
start_phase(toolkit, phase="precheck-deploy", dry_run=false)
start_phase(toolkit, phase="deploy", dry_run=false)               # ~10-15 min
# then whatever post-configuration you need
```
