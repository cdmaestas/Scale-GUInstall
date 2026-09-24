# TechZone Runbook: Walkthrough of a Live Run

A narrative record of actually executing [`techzone-runbook.md`](techzone-runbook.md)
end to end, driven entirely through the `scale-guinstall` MCP tools against
two real IBM TechZone VSI environments. Where the runbook tells you *what
to do*, this document tells you *what actually happened* the times it was
run — including the parts that didn't go according to plan.

A terminal reenactment of this walkthrough is at
[`recordings/techzone-runbook-walkthrough.cast`](recordings/techzone-runbook-walkthrough.cast) —
see [Watching the recording](#watching-the-recording) below.

## Environment

- 7-node TechZone VSI cluster: `scale-server1/2`, `scale-gui1`,
  `scale-proto1/2`, `scale-client1/2`, plus a `scale-bastion` installer node.
- Storage Scale 6.0.1.1, RHEL 9, x86_64.
- Driven from a local MCP client over an SSH tunnel to `scale-server.py`
  running on the bastion.

## Timeline

| Step | Result | Notes |
|---|---|---|
| SSH tunnel | Hit `administratively prohibited` on first attempt | TechZone's hardened `sshd_config.d` drop-in; fixed per runbook §1 |
| Prerequisites (`probe_mmfs`, `check_ansible`, `probe_interfaces`) | Clean | — |
| Toolkit setup | Clean, fast | Contrary to the tool's own doc string calling it the longest-running v1 op |
| Node configuration (7 nodes) | Clean | Harmless `[FATAL] does not exist` + `/etc/hosts` mis-order WARN, both expected |
| Storage discovery + NSD design | Clean | `vdd`/`vde`/`vdf` node-local disks; `cesSharedRoot` + `fs1` design |
| First `precheck-install` | **Failed as expected** | Callhome FATAL — disabled callhome, set ephemeral port range |
| Second `precheck-install` | Clean | `Pre-check successful for install.` |
| `install` | **Succeeded** — 31 min 6 sec | Matched the runbook's 25–35 min estimate |
| Protocols config + enable (NFS/SMB/S3) | Clean | Needed proto nodes' secondary (`eth1`) IPs, pulled from `/etc/hosts` by hand — no MCP tool surfaces these |
| `precheck-deploy` | Clean | `Pre-check successful for deploy.` |
| `deploy` (1st attempt) | **Lost visibility mid-run** | `scale-server.py` had been started in the foreground of the SSH session; that session's backend process died, taking `check_operation` visibility with it (the toolkit kept running independently) |
| Recovery | Restarted backend under `tmux`; re-ran `precheck-deploy` to sanity-check state (inconclusive — precheck doesn't report already-active services), then **re-ran `deploy`** | Safe because the toolkit is idempotent |
| `deploy` (2nd attempt) | **Completed, but overall status `error`** — 22 min 44 sec | Filesystem/S3/SMB/PerfMon/GUI all `ACTIVE`; **CES and NFS both came back `NOT ACTIVE`** after 5 health-check retries each, despite every Ansible task reporting `failed=0` |
| Post-configuration (`start_profiled`, `start_nfs_core_dump`) | Clean | SSH-based tools, unaffected by the bastion limitation |
| Post-configuration (`start_healthinterval`, `start_mmchconfig_tunables`) | **Failed as expected** | `mmhealth`/`mmchconfig: command not found` — confirms the documented bastion `mmcmd()` architecture gap |

## What went right

The runbook's procedural content — every command, parameter, and expected
warning from §0 through §8, and the `start_profiled`/`start_nfs_core_dump`
post-config tools in §10 — matched live behavior exactly on both
environments this was run against. Nothing in that part of the runbook
needed correction after execution; it was accurate on first write.

## What went wrong, and what it taught the runbook

Three real gaps surfaced only by actually running this, none of which
would have been obvious from reading the toolkit's own documentation:

1. **The SSH-tunnel-forwarding block.** TechZone's hardened base image
   disables port forwarding via a drop-in that overrides the main
   `sshd_config`. Not a firewall issue, not a client issue — specific to
   how the config `Include` order works. (Runbook §1.)

2. **`scale-server.py` in the foreground of an SSH session is fragile.**
   When that session dies, the backend dies with it, and *operation
   tracking is entirely in-memory* — a restarted backend has zero
   knowledge that `install`/`deploy` was ever running, even though the
   toolkit process itself survives untouched on the installer node. The
   fix (`tmux`, or the packaged systemd service) is now documented, but
   there's still no way to recover a lost operation's final status short
   of re-running the phase — the toolkit's own log files exist on disk,
   but no tool in this MCP server reads file contents, only lists
   filenames and checks existence. (Runbook §1.)

3. **CES/NFS `NOT ACTIVE` after a fully successful Ansible run — twice,
   on two independent environments.** This is the most interesting open
   finding: `deploy`'s automation completes with `failed=0` across every
   node, S3 and SMB come up healthy, but CES's own health check (and NFS,
   which depends on it) fails 5 retries straight on the protocol nodes.
   Root cause hasn't been identified yet — the bastion `mmcmd()` gap
   means the diagnostic commands (`mmces state show -a`, `mmhealth node
   show -N ...`) can't be run through this MCP tooling and need direct
   node access instead. Documented as a known issue in runbook §9 with
   the manual diagnostic commands to run next.

## Watching the recording

[`recordings/techzone-runbook-walkthrough.cast`](recordings/techzone-runbook-walkthrough.cast)
is an [asciinema](https://asciinema.org) v2 cast file. It's a **scripted
reenactment**, not a raw terminal capture — the real run was driven
through MCP tool calls against a remote backend, not typed into a local
shell, so this recording reconstructs the equivalent CLI commands (the
same `spectrumscale`/`ssh`/`mm*` invocations the MCP tools actually issued
under the hood) paired with real, captured output from the session.
Timings are compressed; the two genuinely long waits (install, ~31 min;
deploy, ~23 min) are summarized rather than played out in full.

Play it locally:

```bash
brew install asciinema   # if you don't already have it
asciinema play docs/recordings/techzone-runbook-walkthrough.cast
```

Or convert it to a shareable GIF/video with
[`agg`](https://github.com/asciinema/agg) or upload it to
[asciinema.org](https://asciinema.org) with `asciinema upload`.
