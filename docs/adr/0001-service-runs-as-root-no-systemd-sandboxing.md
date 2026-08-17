# 1. Service runs as root, with no systemd sandboxing directives

## Context

`packaging/scale-guinstall.service` has no `User=` line, so the backend runs as root under systemd, and carries none of the usual hardening directives (`ProtectSystem=`, `NoNewPrivileges=`, `PrivateTmp=`, etc.). At a glance this looks like an oversight — a reviewer auditing the unit file would reasonably expect to see at least some of them.

The backend genuinely needs broad access: it runs the `spectrumscale` installer/deploy/upgrade toolkit, formats block devices, writes `/etc/profile.d` and `/etc/ssh/sshd_config.d` drop-ins, and manages GPFS cluster state — all of which require real root privileges across most of the filesystem, not a narrow, sandboxable slice of it. Directives like `ProtectSystem=strict` or `ReadOnlyPaths=` would break that functionality outright, not just narrow its blast radius.

## Decision

Run as root with no systemd-level sandboxing. The actual access-control boundary for this tool is the network binding (`127.0.0.1` only, reachable remotely only via an SSH tunnel) plus the per-process auth token required on every API call — not process isolation. This is a deliberate trade-off, not an oversight.

## Why

Systemd sandboxing and "this process can do arbitrary privileged cluster administration" are close to mutually exclusive here. Given the tool's actual job, the meaningful security boundary is *who can reach the backend at all* (loopback + tunnel + token), not *what the process can touch once a request arrives* — that has to be "almost everything," by design.
