# Changelog

All notable changes to Scale GUInstall are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

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

[Unreleased]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/cdmaestas/Scale-GUInstall/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/cdmaestas/Scale-GUInstall/releases/tag/v1.0.0
