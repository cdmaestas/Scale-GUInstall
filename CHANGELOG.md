# Changelog

All notable changes to Scale GUInstall are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Fixed
- Repository hardening pass (security review, silent-failure audit, git hook coverage, doc drift): `_build_nsd_add_cmd`'s disk path now uses `_VALID_DEVICE_PATH_RE` and `stream_nsd_add`'s toolkit path now uses `resolve_path()`/`_sudo_isfile()`, matching the stricter validation every other endpoint in the file already uses for the same kind of value — the old `_SAFE_PATH_RE` check let `..` traversal and non-`/dev/` paths through. A saved config file that exists but fails to parse (corruption, not just "nothing saved yet") is now logged and surfaced via a `warning` field on `GET /api/config`, instead of silently being treated as an empty config and overwritten on the next save. `stream_node_identity`'s certificate-validity `days` field now reports invalid input as an explicit error like its sibling fields, instead of silently substituting a default. Two empty JS `catch {}` blocks (device-list parsing, ansible-check SSE parsing) now log a console warning instead of discarding parse failures with no trace. `start.sh` no longer falls back to piping `curl`/`wget` output for `get-pip.py` into the interpreter with no integrity check if `pip install` fails — it now fails with instructions to install `pip` via the OS package manager instead. `packaging/debian/{postinst,prerm,postrm}` are now covered by `shellcheck` in both the pre-commit hook and CI (previously the only shell scripts in the repo not linted). Documented the deliberate choice to run the systemd service as root with no sandboxing directives as [ADR 0001](docs/adr/0001-service-runs-as-root-no-systemd-sandboxing.md), rather than leaving it looking like an oversight. Updated the man page (waitress mention, `venv/` now installs waitress too) and `help.html` (the same "open the served URL, not the file" clarification already made in the README/man page earlier, plus troubleshooting entries for stale-token 401s and the config-conflict banner) to match current behavior.

---

## [1.1.0] — 2026-08-17

### Added
- Cluster Upgrade page is now real: **Pre-upgrade Check**, **Run Upgrade**, **Post-upgrade Check**, and a new **Show Versions** button (replacing the dead "Upgrade Protocols" button) call the actual `spectrumscale upgrade {precheck,run,postcheck,showversions}` subcommands via `/api/stream/phase`, instead of a `setTimeout`-simulated terminal with fabricated output and wrong command flags (`--precheck`/`--upgrade-protocols` — `spectrumscale upgrade` takes a positional subcommand, not flags; `run` already upgrades GPFS, S3, NFS, SMB, HDFS, and Performance Monitoring together, confirmed against the real `spectrumscale upgrade -h`). **Run Upgrade** is gated behind a confirmation dialog. The Target Version and Upgrade Method panels are marked reference-only, since `upgrade run` takes no arguments for them.
- `testConnection()` on the Populate from Cluster page is likewise now real: a new `/api/stream/test-connection` endpoint runs `sudo -n ssh -p <port> <user>@<node> mmgetstate -a` and reports actual SSH/GPFS state, replacing a fake `[OK] SSH connection successful` timer. Also wires up the previously-decorative `pop-user`/`pop-port` fields into the real call.
- Per-process auth token, generated fresh at startup and injected into the page only when the backend serves it itself: every `/api/*` call now requires it, closing a CSRF-shaped hole where any page open in the same browser could hit the backend's unauthenticated GET endpoints (no CORS preflight required for a "simple" GET request) to execute privileged commands. A page opened as a local `file://` copy has no token and gets a clean 401 on any real backend call, though Dry Run still works fully since it never touches the backend. The frontend attaches the token by wrapping `fetch()` once at load rather than threading a header through the ~25 individual call sites by hand.
- Config autosave: the GUI's working state (nodes, NSDs, filesystem, protocols, cluster name, toolkit path) is now autosaved to the backend (`/var/lib/scale-guinstall/config.json`, mode 0600 in a mode 0700 directory) roughly once a second and restored automatically on the next page load — closing a tab or restarting the browser no longer loses in-progress work. Writes are optimistically locked via a revision counter; a genuine conflict (two tabs/sessions open at once) pauses autosave and shows a banner instead of silently overwriting the other session's work, keeping the current tab's unsaved edits intact. Dry Run is always re-forced on after a restore regardless of what was saved, so autosave can never silently resume into live mode. Separate from the existing manual Export/Import Config buttons, which remain the way to back up or move a configuration to a different installer node.
- First test suite for the project: a pytest suite (`tests/`, wired into CI and the pre-push hook) covering NSD-add flag construction, GPFS pool/usage validation, `PHASE_CMDS` shape (including a regression guard for the `upgrade` positional-subcommand fix above), and the `_VALID_*_RE` validation regex boundary cases. Required extracting the NSD-add validation/flag-building logic out of `stream_nsd_add()`'s SSE generator into standalone functions (`_build_nsd_add_cmd()`, `_nsd_pool_usage_error()`) so it could be tested without mocking Flask/subprocess/sudo — verified behavior-preserving via the new tests and a live before/after smoke test.

### Changed
- Backend now runs under `waitress` by default instead of Flask's development server, falling back to the dev server with a warning if `waitress` isn't installed. Uncovered and fixed a real incompatibility in the process: waitress enforces PEP 3333 and rejects an application setting the `Connection` response header, which crashed every SSE endpoint with a 500 the instant it was in front — that header (a workaround for a Werkzeug dev-server-specific keep-alive hang, see 1.0.26) is now only sent on the Werkzeug fallback path.
- CORS no longer allows the `file://` (null-origin) origin — the frontend must be served by the backend to make real API calls (see auth token above), which removes the need to support that origin at all.

---

## [1.0.27] — 2026-08-08

### Added
- "Find .zip here" button next to the Zip Archive Path field on Prepare Software Step 1: lists `.zip` files already on the installer node in the directory portion of the current path, via a new `GET /api/browse/files?dir=&ext=` endpoint (reuses the existing `_sudo_listdir` helper). Selecting one fills the field with the full path. A native `<input type="file">` picker can't work here — this app is normally used from a workstation over an SSH tunnel, so the browser and the installer node running `unzip` are different filesystems; this lists the *remote* directory server-side instead.

---

## [1.0.26] — 2026-08-07

### Fixed
- Bulk NSD wipe (`wipefs` over SSH) hung after the first disk finished successfully, never moving on to the next one. The actual cause: every SSE streaming response explicitly set `Connection: keep-alive`, and Werkzeug's development server (which this backend always runs on) can get stuck servicing the *next* request on a reused persistent connection after a chunked streaming response — the previous request completes cleanly server-side, but the following one on the same connection never gets serviced, which looks exactly like a hang from the browser's side. Reproduced directly: with `keep-alive`, a second back-to-back request to the same SSE endpoint reliably hung; switching to `Connection: close` (a fresh TCP connection per request — free on loopback, negligible over an SSH tunnel) fixed it in six consecutive test requests. `stream_process()` also gained an optional `timeout` parameter (bounded read via `select()`, killing the process if the deadline is hit) as defense-in-depth against the separate, real risk that `ssh` doesn't close stdout until everything a remote command left running exits too — applied to the wipefs, TLS-identity `scalectl` import, and fake-NSD `truncate`/`fallocate` calls. Existing `stream_process()` callers without a timeout keep the original unbounded behavior.

---

## [1.0.25] — 2026-08-07

### Added
- Local setup-run history on Prepare Software Step 4: `spectrumscale setup` is a one-shot config command with no persistent process to check status of (it writes config and exits, on the Ansible-based toolkit), so rather than detect node state, the app now remembers whether *it* has completed a setup run for a given installer IP — success/failure and when — shown just below the IP field. Tracked per-IP in `localStorage`, clearly labeled "remembered in this browser only" since it reflects runs made through this app in this browser, not configuration state on the node itself.
- Header badge (next to the cluster status, visible from every page) built on the same local history: **Install Service: Run** (green) if setup has succeeded at least once for any installer IP in this browser, **Not Run** (red) otherwise.
- "In cluster" flag on Node Configuration: clicking **Load from cluster** now also cross-checks the loaded nodes against the live GPFS cluster (`mmlscluster`, via the existing `/api/probe/cluster-nodes` endpoint) and marks any that are already live cluster members with a green badge next to the hostname. Informational only — no delete/remove action is offered, since `mmdelnode` has real destructive prerequisites (quorum, NSD ownership) that this app doesn't attempt to validate. Fails silently if the live-cluster check itself fails (e.g. no cluster yet), so it never blocks the primary load.

---

## [1.0.24] — 2026-08-05

### Changed
- Clearer NSD button/heading wording to distinguish the two "add" steps: the form's **Add NSD** button is now **Add to Configured NSDs** (stages an NSD into the local list) under a **Define NSD Disk** heading, and the apply action is **Apply to Cluster Definition** (runs `spectrumscale nsd add`). The flow now reads Disk Discovery → Define NSD Disk → Configured NSDs → Apply to Cluster Definition.

### Added
- Header activity indicator: a badge in the top bar shows **Running…** (amber, pulsing) while any command is streaming and **Done** (green) or **Error** (red) briefly when it finishes, then auto-hides. A counter keeps it accurate across overlapping/parallel commands (e.g. the multi-node device scan). Wired into the shared streaming paths, so it covers prepare steps, node add, NSD add, format, populate, cluster config, and device discovery.

---

## [1.0.23] — 2026-08-04

### Changed
- In "Configure the filesystem in the IBM Storage Scale GUI" mode, the NSD `usage` is now also deferred to the Scale GUI (which sets usage/pool when it builds the filesystem): the Usage field is hidden and `spectrumscale nsd add` omits `-u`, so the command is the bare `nsd add -p <server> <device>`. The Usage column shows `—` in the Configured NSDs table, and the backend/stanza treat usage as optional. Turning the mode off restores full usage/pool/failure-group control.

---

## [1.0.22] — 2026-08-03

### Added
- "Configure the filesystem in the IBM Storage Scale GUI" toggle at the top of the NSD Storage page (default **on**). When on, this installer adds bare NSDs — no storage pool, failure group, or filesystem — and skips its own Filesystem step (the Filesystem nav item is hidden and the NSD page's Next button goes straight to Protocol Services). The filesystem is created later in the Scale management GUI. Turn it off to configure pool/failure group and use the installer's Filesystem step. `spectrumscale nsd add` omits `-fg`/`-po`/`-fs` in this mode, the backend treats the failure group as optional, and the Configured NSDs table shows `—` for pool and failure group (rather than implying a `system` pool) when neither is set.
- The Add NSD Disk form now auto-suggests the next failure group as the next multiple of 10 above the highest one already configured (1 for the first NSD) — so new disks land in a fresh failure group (e.g. after 1 and 2 it suggests 10, then 20) instead of reusing or sitting adjacent to an existing one. The value is still editable.
- Block-device discovery on NSD Storage now runs `lsblk` (via `/api/stream/list-devices`, `sudo -n ssh <node> lsblk -b -P -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL`) across every NSD-role node in parallel, returning structured records (new `devices` SSE event) with size, type, filesystem, mount point, and model. Sudo elevates the local ssh client to root before it connects, since GPFS clusters rely on passwordless root-to-root SSH trust.
- Discovered devices are shown in a selectable table (checkbox per row, select-all, sortable Node/Device/Size/Type columns). Only disks ≥ 32 GB are listed by default, with a "Show devices under 32 GB" toggle. Devices that carry a filesystem or are mounted are flagged **In use** and cannot be selected, so a running OS/data disk can't be wiped by accident.
- Multi-select devices and configure them all at once into NSDs: usage type, failure group (**Auto** assigns one per node, or a manual value), storage pool, filesystem, and an optional `wipefs -a` format step (reuses `/api/stream/format-disk`, gated by Dry Run and a confirmation dialog). Configured NSDs are pushed into the Configured NSDs table; the manual Add NSD Disk form remains for backup-server assignment and edits.
- Model column in the NSD Storage device discovery table (from `lsblk` MODEL)
- EMS, Call Home, and Archive EE are now editable inline as columns in the Configured Nodes table (previously only settable when first adding a node)

### Changed
- NSD Storage page: the run action is split into its own **Apply NSDs to Cluster** panel (command preview + button + terminal, always visible), and the **Stanza File Preview** is now a collapsible panel — collapsed by default and moved to the bottom as an informational reference.
- `/api/stream/list-partitions` (which parsed `/proc/partitions`) is replaced by `/api/stream/list-devices`; the per-row "Use & Format" action is replaced by the multi-select bulk-configure flow.
- Help opens in a named tab and its "Back to app" link now returns to the existing app tab (closing the Help tab) instead of loading a second copy of the app inside the Help tab; falls back to normal navigation when Help was opened directly.
- Node Configuration redesigned: the Configured Nodes table (with a prominent **Load from cluster** button) is now at the top so current state is visible first, followed by Bulk Import, with Add Single Node collapsed at the bottom. The redundant read-only "Role Assignment" card grid is removed — roles are edited only inline in the table.

### Fixed
- NSD pool/usage validation: metadata can only live in the `system` pool, so a non-system storage pool may only hold `dataOnly` NSDs. Selecting `dataAndMetadata`, `metadataOnly`, or `descOnly` now locks the Storage Pool field to `system` (in both the manual Add NSD form and the bulk-configure flow) so an invalid pool can't be entered; only `dataOnly` allows naming a custom pool. The invalid combination is still rejected by the backend and a validation guard as a backstop, instead of letting the toolkit fail with `FATAL: An NSD cannot be used for dataAndMetadata and be in the <pool> pool`. The default `system` pool is stored as empty, so `-po` is omitted from the command entirely.
- `spectrumscale nsd add` used the wrong option flags and failed with `error: ambiguous option: -f could match -fs, -fg`. Corrected to the toolkit's actual flags: `-fg` (failure group, was `-f`), `-po` (pool, was `-t`), `-fs` (filesystem, previously stanza-only), and `-s` (secondary/backup servers, was `-b`). The bogus size flag is dropped entirely — the toolkit reads the device size itself, and `-s` had meant secondary server, not size. Both the backend command and the frontend preview are fixed.

---

## [1.0.21] — 2026-08-02

### Fixed
- "List Partitions" on the NSD Storage page could hang indefinitely — the SSH call only bounded the initial TCP connect phase (`ConnectTimeout=10`), not authentication or a connection that goes silent after being established (e.g. a slow reverse-DNS lookup on the remote `sshd`, or a dropped connection with no FIN/RST). Added `BatchMode=yes` (fail fast instead of waiting on a prompt) and `ServerAliveInterval=5`/`ServerAliveCountMax=2` (detect and kill a stalled connection within ~10s) to this and the two other SSH call sites in `scale-server.py` (NSD file-backed disk creation, node identity certificate push), which had the same gap.

---

## [1.0.20] — 2026-08-02

### Fixed
- "Back to app" link in `help.html` 404'd when the app was loaded through the backend server (`http://127.0.0.1:5001/`) — the relative link resolves to `/Scale-GUInstall.html`, but only `/` had a route. Added `/Scale-GUInstall.html` as an alias route serving the same content.

---

## [1.0.19] — 2026-08-02

### Added
- CI `security-guard` job and a matching local pre-commit check: fails the build on `shell=True`, unsafe `pickle`/`yaml.load`/`eval`, bare `except:` (silent-failure regression), or an `innerHTML` template literal that interpolates a value without routing it through the `h()` escape helper
- Always-visible Dry Run toggle in the top header, synchronized with the existing Settings-page toggle; turns red with a **LIVE** label when disabled
- `help.html` — a standalone in-app help/reference page (getting started, Dry Run explanation, page-by-page guide, remote access, troubleshooting) linked from a new **Help** button in the header; served by `scale-server.py` at `/help.html` and packaged in both RPM and DEB
- README screenshots (Dashboard, Node Configuration, NSD Storage, Install & Deploy, Settings) under `docs/screenshots/`
- Styled hover tooltip for the collapsed icon-rail sidebar, replacing the native browser `title` tooltip — appears instantly, matches the app's dark theme, and is positioned via JS so it isn't clipped by the sidebar's `overflow-x: hidden`

### Fixed
- CI `python-check` job used the deprecated `ast.Constant.s` accessor, removed in Python 3.12+; switched to `ast.Constant.value`

### Removed
- "AFM Gateway" checkbox/column from Node Configuration. The `spectrumscale` install toolkit has no node-add flag for it — the role was silently dropped from `node add` on the backend and never wired to the AFM Gateway post-configuration panel, so checking it did nothing. AFM gateway designation still works as intended via the Post Configuration → AFM Gateway panel (`mmafmconfig -N <node>`), which is unaffected. Can be reintroduced as a real node role if the toolkit ever adds support.

---

## [1.0.18] — 2026-08-02

### Changed
- Collapsing the sidebar on desktop (>960px) now shrinks it to a 56px icon rail instead of sliding it fully off-screen. Section labels, item text, and count badges hide; icons stay visible and centered, each with a hover tooltip naming the page. Mobile drawer behavior (≤960px) is unchanged.

---

## [1.0.17] — 2026-07-16

### Fixed
- Concurrency guard no longer fails open: if the pgrep process check itself fails or times out, spectrumscale commands are refused with an explicit error instead of silently proceeding as if nothing were running
- `/api/spectrumscale/running`, `/api/spectrumscale/kill`, and `/api/setup-service/status` return HTTP 500 with an error field when the process check fails, instead of reporting "nothing running" / "not running"; the Step 4 badge shows grey **Unknown** and the Settings panel shows the error instead of a false "[OK]"
- Setup service restart refuses to proceed when the service state cannot be determined

### Changed
- Pre-commit hook and CI now shellcheck `enable-ssh-forwarding.sh` and the `.githooks/` scripts, and validate the embedded JavaScript with `node --check` (new `js-check` CI job)

---

## [1.0.16] — 2026-07-14

### Added
- `packaging/enable-ssh-forwarding.sh` — enables local SSH TCP forwarding via an `/etc/ssh/sshd_config.d/60-scale-guinstall.conf` drop-in when the directory exists (falls back to in-place edit of `sshd_config`), validates with `sshd -t` before reloading; shipped in RPM/DEB at `/usr/lib/scale-guinstall/`
- Concurrency guard: the backend refuses to start a `spectrumscale` command while another toolkit invocation is running, listing the conflicting PIDs — concurrent runs corrupt the cluster definition
- Settings → Running Toolkit Processes panel: Check Running lists toolkit CLI processes; Kill All terminates them (TERM, then KILL after 2s) — never touches the backend service or GPFS daemons
- Setup service status badge on Prepare Software Step 4 — green Running / red Not running, auto-checked on page load and after Start/Restart; detects the toolkit's `installer.snap.py` daemon
- Restart Service button on Step 4 — stops the setup daemon and re-runs `spectrumscale setup -s <ip>`
- Review Node Configuration after a successful populate now imports the populated nodes via `spectrumscale node list` before navigating, instead of landing on a blank table

### Fixed
- `config populate` hung forever when a cluster definition already existed: the toolkit's overwrite prompt was waiting on stdin nobody could see. All backend subprocesses now default stdin to `/dev/null` (prompts fail visibly), and the Overwrite checkbox — previously not sent to the backend at all — now answers the prompt with y/n
- Removed `--skip ssh` from the Populate page — `spectrumscale config populate` does not support it (`--skip nsd` remains)

### Documentation
- SSH forwarding docs corrected: appending `AllowTcpForwarding local` to the end of `sshd_config` does **not** override an earlier `no` (sshd is first-match-wins); README, man page, and `start.sh` hint now recommend the `sshd_config.d` drop-in or in-place edit

---

## [1.0.15] — 2026-07-13

### Added
- Committable local git hooks in `.githooks/` (pre-commit: py_compile + shellcheck + HTML markers; pre-push: pre-commit checks plus package builds when tools are present); enable with `git config core.hooksPath .githooks`

### Security
- Escape backend URL with `h()` in the "Backend not reachable" banner (last unescaped user-controlled `innerHTML` interpolation)

### Changed
- Narrow broad `except Exception: pass` probes in `find_compliant_python()` / `_parse_python_version()` to expected failure types (`OSError`, `TimeoutExpired`, `ValueError`) so genuine bugs surface instead of being swallowed
- Add `# shellcheck shell=sh` directive to `scale-guinstall-mmfs.sh` so the sourced profile.d snippet lints cleanly

---

## [1.0.14] — 2026-07-13

### Security
- `_diagnose_path` no longer includes a root-privileged directory listing in error messages for paths outside `/usr/lpp/mmfs` — prevents using the setup endpoint's `bin` parameter to list root-only directories such as `/root`
- All backend `sudo` invocations now use `sudo -n` (non-interactive) — a missing `NOPASSWD` rule fails immediately with a clear diagnostic instead of hanging the request thread on a hidden password prompt

### Fixed
- Toolkit detection failed on nodes where `/usr/lpp/mmfs/<version>` is root-only: filesystem checks (`isfile`/`isdir`/`listdir`) now run via `sudo`, and the probe searches `ansible-toolkit/`, `installer/`, and the version root for `spectrumscale`
- Setup step error messages now explain *why* the toolkit path check failed (sudo unavailable, path is not a regular file, or path missing — with a listing of the nearest existing directory under `/usr/lpp/mmfs`) instead of a misleading bare "not found"
- All `sudo` filesystem checks have a 10-second timeout so a stale NFS mount cannot wedge a request thread

### Documentation
- README and man page now document the passwordless sudo (`NOPASSWD`) requirement
- README and man page document `/etc/profile.d/scale-guinstall-mmfs.sh` installed by the packages
- Man page gains SSH tunnel troubleshooting for `administratively prohibited` (AllowTcpForwarding)
- `start.sh` banner shows the AllowTcpForwarding fix hint
- Added `.gitignore` (`__pycache__/`, `dist/`, packaging build dirs)

---

## [1.0.13] — 2026-07-13

### Added
- `packaging/scale-guinstall-mmfs.sh` — profile.d script that appends `/usr/lpp/mmfs/bin` to `$PATH`; installed to `/etc/profile.d/` by both RPM and DEB packages so `mm*` commands are available in interactive shells after install
- `start.sh` now prints an SSH tunnel hint (`ssh -L 5001:127.0.0.1:5001 <user>@<node>`) in the startup banner
- `/api/probe/cluster-nodes` endpoint — parses `sudo mmlscluster` node table and returns hostnames as JSON
- "Load from cluster" button on Populate page fetches cluster nodes and populates a dropdown for the Existing Cluster Node field

### Changed
- All `mm*` subprocess calls in the backend now use the full absolute path `/usr/lpp/mmfs/bin/<cmd>` via a `mmcmd()` helper — `sudo` no longer requires `/usr/lpp/mmfs/bin` to be in root's PATH
- Commands updated: `mmlscluster`, `mmchconfig`, `mmhealth`, `mmcrfileset`, `mmafmconfig`, `mmlinkfileset`
- CCR status check streams full `mmlscluster` output to the terminal (previously only the grepped Repository line); Repository type badge now shows **CCR Enabled**, **Repository: \<type\>**, or **CCR Not Found**

---

## [1.0.12] — 2026-07-08

### Fixed
- NSD usage field now validated against the IBM allowlist (`dataAndMetadata`, `dataOnly`, `metadataOnly`, `descOnly`, `logOnly`) before reaching the CLI — previously any string was forwarded to `spectrumscale nsd add -u`, producing a confusing toolkit error instead of a clean backend message
- "Add backup server" button now reappears after removing a backup row when at the 7-row limit; previously the button stayed hidden even after rows were deleted

---

## [1.0.11] — 2026-07-08

### Added
- Storage Pool field in Add NSD Disk form — maps to `-t <pool>` CLI flag and `pool=` stanza field; blank defaults to the system pool
- Filesystem field in Add NSD Disk form — written to the stanza as `filesystem=<name>`
- Up to 7 backup servers per NSD — dynamic list replaces the single backup dropdown; rows added with "+ Add backup server" and removed individually; all backups passed as `-b nsd2,nsd3,...` and included in `servers=` in the stanza
- Backups and Pool columns in the Configured NSDs table
- Backend validates each backup hostname, enforces the 7-backup limit, and validates pool name against GPFS name regex

### Changed
- `spectrumscale nsd add` command now runs once per disk using CLI flags (`-p`, `-b`, `-u`, `-f`, `-t`, `-s`) instead of a stanza file; stanza preview remains as an informational reference

---

## [1.0.10] — 2026-07-08

### Added
- Disk Discovery panel on NSD Storage page combines List Partitions and Create Simulated NSD File into a single segmented-button panel, positioned immediately after the destructive-operation warning
- Create Simulated NSD now runs the command on the selected NSD server node via SSH, eliminating the need to run it locally on the installer node
- Node selector in Create Simulated NSD is populated from configured nodes; NSD-role nodes are labelled `(NSD)` for clarity
- SSH User field (default: `root`) controls the remote login user; command preview updates live to show the full `ssh user@node "..."` form
- Backend validates `node` and `ssh_user` parameters and shell-quotes all path and size arguments in the remote command

### Changed
- Segmented control buttons use explicit `#0f62fe` blue fill/outline states, visible in both dark and light mode

---

## [1.0.9] — 2026-07-07

### Added
- Client Only checkbox in Add Single Node form — when selected, disables and unchecks incompatible roles (NSD, Protocol, GUI, Gateway, EMS, Call Home, Archive EE); only Admin, Manager, and Quorum remain selectable
- Inline node table enforces the same restriction: incompatible role checkboxes are dimmed and non-interactive for client-only nodes
- Toggling Client Only on an existing node strips any incompatible roles already assigned

### Fixed
- NSD server and backup server dropdowns in Add NSD Disk now populate when navigating to the NSD Storage page, even if nodes were configured before visiting it

---

## [1.0.8] — 2026-07-07

### Documentation
- Add firewall and SSH server requirements section to README
- Document `AllowTcpForwarding local` in `sshd_config` as the correct setting for enabling `ssh -L` tunnels on hardened RHEL/CentOS servers
- Clarify that port 5001 requires no firewall rule for the SSH tunnel — only port 22 (SSH) needs to be reachable
- Correct direct-access note: opening port 5001 in the firewall has no effect without also rebinding Flask to `0.0.0.0`; if done, restrict to specific workstation IP via `--add-rich-rule`

---

## [1.0.7] — 2026-07-06

### Security
- Validate `server_ip` against hostname/IP regex before passing to `spectrumscale setup`
- Validate `node` in `/api/stream/populate` before passing to `spectrumscale config populate -N`
- Validate `nodes` in `/api/stream/postconfig/healthinterval` — must be `all` or a valid hostname
- Validate `org_name`, `ca_cn`, `cluster_name` against a safe character set before interpolation into openssl `-subj` string (prevents X.509 field injection via `/`)
- Shell-quote `tls_dir` and certificate paths in remote SSH command using `shlex.quote` (prevents remote shell injection)
- Validate `ssh_user` against `[A-Za-z0-9._-]` before constructing `user@host` SSH targets
- Validate `perfmon_node` and `fileaudit_fs` in both individual endpoints and `apply-cluster-config`
- Validate `username` against `[A-Za-z0-9._-]` and `role` against an explicit allowlist in `/api/stream/postconfig/guiuser`
- Validate AFM gateway `fs`, `fileset`, `node`, and `mode` before GPFS commands; `mode` restricted to `{ro, rw, sw, iw, lg}`

### Changed
- Extract shared `_gen_callhome`, `_gen_perfmon`, `_gen_fileaudit` generator helpers — individual endpoints and `apply-cluster-config` both delegate to them, eliminating duplicated command construction
- Move `import glob`, `import tempfile` to module top level; remove unused `import shutil`
- Replace `__import__("os").unlink(...)` with plain `os.unlink(...)`
- Remove redundant `import re as _re` inside `probe_mmfs` — module-level `re` already available
- Derive `_SKIP_SSH_PHASES` from `PHASE_CMDS` keys instead of duplicating them

---

## [1.0.6] — 2026-07-06

### Added
- Probe installer node network interfaces on Prepare page load via `/api/probe/interfaces`
- Detected IPs shown as clickable chips below the IP input in Step 4; single-IP nodes auto-fill the field
- Release install instructions clarified: download `RPM-GPG-KEY-scale-guinstall` alongside the RPM before importing (works air-gapped)

---

## [1.0.5] — 2026-07-06

### Added
- Probe /usr/lpp/mmfs on Prepare page load to detect installed IBM Storage Scale versions
- Detection banner shows a version selector (all detected x.y.z.w directories) and an editable toolkit path override for versions not yet extracted
- "Apply & skip to Step 4" sets the global toolkit path, updates the Step 4 setup command preview, and scrolls Step 4 into view
- Steps 1–3 can be skipped when Scale is already installed

---

## [1.0.4] — 2026-07-06

### Added
- RPM packages are now GPG-signed (RSA-4096); public key distributed as `RPM-GPG-KEY-scale-guinstall` in each release
- Install instructions updated to `rpm --import` the signing key — no more `--nogpgcheck` needed

---

## [1.0.3] — 2026-07-06

### Fixed
- Opening `http://127.0.0.1:5001` over an SSH tunnel now serves the app directly — Flask was returning 404 because no `/` route existed; the HTML had to be opened locally as a `file://` URL
- Backend URL auto-detects from `window.location.origin` when the page is served over HTTP, so no manual configuration is needed

### Added
- TLS-based node identity setup panel in Install & Deploy Step 2: generates a self-signed CA and per-node X.509 certificates using EC keys (`openssl ecparam prime256v1`), signs with Subject Alternative Names, and imports via `scalectl node config set --cert --key --chain`; optional SSH distribution and system trust store registration

---

## [1.0.2] — 2026-07-03

### Added
- Man page (`scale-guinstall(1)`) covering synopsis, options, environment, files, examples, and security notes
- README.md and CHANGELOG.md installed to `/usr/share/doc/scale-guinstall/` in both RPM and DEB packages
- Release workflow now extracts the matching changelog section automatically as the GitHub Release body

---

## [1.0.1] — 2026-07-03

### Security
- Validate `config gpfs` flags against an explicit allowlist — unrecognised flags are now rejected before reaching the subprocess
- Validate node hostnames against a strict regex (`[a-zA-Z0-9._-]`) before use in subprocess arguments or file paths
- Validate `mmchconfig` values against `[A-Za-z0-9.]+` regex to prevent malformed arguments
- Fix CORS handler: empty `Origin` header no longer produces `Access-Control-Allow-Origin: *`
- Clamp and safe-parse TLS certificate `days` field — bad input now falls back to default instead of raising a 500

### Fixed
- RPM `%post` script used bash `[[` syntax but was executed under `/bin/sh`; added `#!/bin/bash` shebang and switched to POSIX `[ ]`
- Debian `postinst` missing `-u` and `pipefail` flags — pip failures in pipelines were silently swallowed
- `bulkImport` arrow-function parameter `h` shadowed the global XSS-escape helper `h()`

### Changed
- `import re` moved to module top-level in `scale-server.py`; removed three inline imports and `__import__("re")` usage
- Installing via Package section moved before Getting Started in README — packaged install is the recommended production path
- README install commands use `<version>` placeholder instead of hardcoded `1.0.0`; added RHEL 8/9 AppStream note for `python3.11`

---

## [1.0.0] — 2026-06-28

### Added
- IBM Storage Scale 6.0.1 support: `scaleadmd enable` and `nodeid define` steps in Install & Deploy
- NFS core dump enable/disable panel in Post Configuration
- `--gplbin_dir` flag support in Cluster Settings
- Inline NSD edit (repopulates form and scrolls to input)
- Ansible version prerequisite check with ansible-core 2.24+ incompatibility warning
- Ubuntu locale prerequisite check
- CCR status check panel on Populate from Cluster page
- TLS-based node identity setup panel (generates CA + per-node certificates via openssl)
- `scale-server.py` Flask backend with SSE streaming for live command execution
- RPM and DEB packaging with isolated venv at `/usr/lib/scale-guinstall/venv`
- systemd unit (`scale-guinstall.service`) — installed but not enabled by default
- `start.sh` convenience launcher with automatic Python 3.10+ detection and Flask bootstrap
- SSH tunnel helper panel in Settings — generates `ssh -L` command and tests connection
- GitHub Actions CI workflow (python-check, shellcheck, html-check, build-deb, build-rpm)
- GitHub Actions release workflow — triggered on `v*.*.*` tags, creates GitHub Release with RPM + DEB + HTML assets
- Archive EE node role support in Node Configuration
- Admin checkbox column in Configured Nodes table
- Inline role checkboxes in Configured Nodes table
- `--skip-ssh` and `--skip-nsd` options in Install & Deploy and Populate from Cluster

### Security
- All user input rendered via `innerHTML` escaped with `h()` helper — XSS prevention throughout
- Terminal output uses `textContent` instead of `innerHTML`
- Credentials (GUI user passwords, S3 secret keys) sent via POST JSON body — never in URL query parameters
- Server binds to `127.0.0.1` only; CORS restricted to `localhost`, `127.0.0.1`, and `file://` origins
- No generic shell execution endpoint — all commands are explicit and allowlisted
- Filesystem paths validated against an allowlist of safe roots to prevent path traversal
- `binpath` inputs restricted to safe characters via regex
- SSH host key checking uses `accept-new` rather than disabling verification entirely

### Fixed
- Ephemeral port range `-e`, remote shell `-r`, and remote copy `-rc` flags not sent when value matched the pre-filled default
- Node list parser rewritten for actual `spectrumscale` output format
- Cluster config load: parse `is <value>` format and filter `None` values
- Duplicate `skipSsh` declaration causing script parse failure
- `start.sh` Python detection when system `python3` is below 3.10
- RPM version field: hyphens replaced with `.` to satisfy RPM version format rules

[Unreleased]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.21...HEAD
[1.0.21]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.20...v1.0.21
[1.0.20]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.19...v1.0.20
[1.0.19]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.18...v1.0.19
[1.0.18]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.17...v1.0.18
[1.0.15]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.14...v1.0.15
[1.0.2]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/cdmaestas/Scale-GUInstall/releases/tag/v1.0.0
