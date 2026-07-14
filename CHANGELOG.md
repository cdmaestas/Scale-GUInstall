# Changelog

All notable changes to Scale GUInstall are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

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

[Unreleased]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.15...HEAD
[1.0.15]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.14...v1.0.15
[1.0.2]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/cdmaestas/Scale-GUInstall/releases/tag/v1.0.0
