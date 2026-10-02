# TechZone Runbook: Chasing Down CES/NFS `NOT ACTIVE` — and Fixing It

> **Historical source material.** For the edited presentation, use the [curated recordings](recordings/README.md). Original recordings and narration are retained for provenance; see the [archive corrections](recordings/ARCHIVE.md) before reusing their examples.

A second narrative record of executing [`techzone-runbook.md`](techzone-runbook.md)
live against TechZone VSI environments, picking up exactly where
[the first walkthrough](techzone-walkthrough.md) left off: the "CES/NFS
`NOT ACTIVE` despite `failed=0` everywhere" issue, still open at the time
that doc was written.

This run closes it out. Across two environments in one session:
the first diagnoses a second, independent root cause underneath the
already-documented export-IP conflict; the second confirms the fix by
running the full flow clean, with CES/NFS/SMB all `ACTIVE` on the very
first `deploy` attempt — no manual repair steps needed at all.

A terminal reenactment of this run is at
[`recordings/techzone-runbook-walkthrough-2.cast`](recordings/techzone-runbook-walkthrough-2.cast) —
see [Watching the recording](#watching-the-recording) below.

## Environment

Two separate 7-node TechZone VSI clusters (`scale-server1/2`,
`scale-gui1`, `scale-proto1/2`, `scale-client1/2`, plus a
`scale-bastion` installer node), Storage Scale 6.0.1.1, RHEL 9,
x86_64 — driven the same way as before, over an SSH tunnel to
`scale-server.py` on the bastion.

## Timeline — Environment A (diagnosis)

| Step | Result | Notes |
|---|---|---|
| Full install → protocols config → deploy | **Deploy "succeeded" with `failed=0`, but CES/NFS came back `NOT ACTIVE`** | Export IPs this time were genuinely free (verified via ping before use) — real progress over the first walkthrough, since SMB came up `ACTIVE` as proof the IP fix works, but CES/NFS still failed |
| `mmces address list` | Both export IPs stuck **`unassigned`** | `export_ip_pool` only stages the pool; `deploy` never actually assigns an IP to a node |
| Manual `mmces address add --ces-node` | **Failed**: `Node ... is not currently accepting CES network assignments` | The documented stuck-`Failed`-flag problem, hit independently on a new environment |
| `mmces node suspend`/`resume` | Cleared the flag only **transiently** | Resuming re-triggers GPFS's health check; since the real cause was still broken, the flag came back on both nodes on the next evaluation |
| Direct service checks (`systemctl status firewalld nfs-ganesha rpcbind`) | **Root cause found**: `rpcbind.socket` and `rpcbind.service` both **masked** | `firewalld` was inactive (ruled out). A masked unit is a hard systemd block — GPFS's own `systemctl start rpcbind` call (confirmed via `strace` during this same investigation) cannot start it. No rpcbind → no portmapper → NFS-Ganesha can never come up. SMB doesn't depend on rpcbind, explaining why only SMB was healthy |
| Fix identified (`systemctl unmask` + `enable --now` both units) | Not yet applied/confirmed in this environment | Reservation ended before a follow-up deploy could validate it |

## Timeline — Environment B (confirmation)

| Step | Result | Notes |
|---|---|---|
| Pre-flight: `rpcbind.socket`/`.service` status check | **Confirmed masked again** — same symptom, independent environment | Not a one-off image defect |
| Fix applied **before** `install` (not as a repair) | `systemctl unmask`/`enable --now` both units on both protocol nodes | User applied this at the TechZone template level too, for future provisions |
| Toolkit setup, node config (7 nodes), storage discovery, NSD add | Clean | Same two harmless per-node warnings as always (`[FATAL] does not exist`, `/etc/hosts` mis-order) |
| First `precheck-install` | **Failed as expected** — callhome FATAL | Disabled callhome, set ephemeral port range, exactly per runbook §6 |
| Second `precheck-install` | Clean — plus a new, confirmatory `WARN` | `"the Portmapper service (rpcbind) is found running"` — direct evidence the fix was live before install even started |
| `install` | **Succeeded** — ~26 min | Lost the log stream's tail mid-run (the documented §1 visibility gap) but confirmed via direct `mmlscluster`/`mmlsfs` on a cluster node that all 7 nodes were `active` and both filesystems (`cesSharedRoot`, `fs1`) were created with all NSDs `up`/`ready` |
| Protocols config | Clean | `export_ip_pool` sourced from this environment's own pre-allocated `ces.scale.lab` addresses, verified unused (no ping response) before use |
| `precheck-deploy` | Clean | `Pre-check successful for deploy.` |
| `deploy` | **Succeeded on the first attempt — 12 minutes 33 seconds** | `failed=0` across all 7 nodes. `Filesystem ACTIVE`, `Cluster Export Services ACTIVE`, `SMB ACTIVE`, `NFS ACTIVE`, `Performance Monitoring ACTIVE`, `GUI ACTIVE`. No `mmces address add`, no suspend/resume, no retries — none of the Environment A workaround dance was needed |

## What this confirms

The masked-`rpcbind` finding from the first walkthrough's open
question is real, reproducible across independent environments, and
**fixing it before `deploy` — not after — eliminates the whole
CES/NFS failure chain**: no stuck `Failed` flags, no manual address
assignment, no suspend/resume flapping. Combined with the
already-documented genuinely-free `export_ip_pool` fix, protocol
deploy now goes clean on the first try.

`techzone-runbook.md` §8 has been updated to put the `rpcbind`
mask check at the top as a recommended pre-flight step, with the
confirmed fix path and real timing numbers, rather than leaving it
buried as a troubleshooting footnote.

## What's still open

Both fixes (rpcbind unmask + genuinely-free export IPs) were applied
together on the confirmation run, since isolating which one alone
would have sufficed isn't worth the cost of another ~40-minute
install+deploy cycle. If a future environment reproduces only one of
the two symptoms, that would narrow it further, but there's no
pressing need to chase that.

## Watching the recording

[`recordings/techzone-runbook-walkthrough-2.cast`](recordings/techzone-runbook-walkthrough-2.cast)
is an [asciinema](https://asciinema.org) v2 cast file — a **scripted
reenactment** built from the real commands and real captured output of
this session, the same way as the first recording: narration banners
between sections, simulated typing for commands, and the two long waits
(install ~26 min, deploy ~13 min) compressed rather than played out in
full.

Unlike the first recording, this one is **narration-paced**: each
section holds for roughly as long as it takes to read the matching
section of the companion narration script aloud, so it can be played
and talked over live (via `asciinema play` + screen recording) without
constantly pausing. Total runtime is ~5.5 minutes. Play it locally:

```bash
brew install asciinema   # if you don't already have it
asciinema play docs/recordings/techzone-runbook-walkthrough-2.cast
```

A silent animated rendering of the same cast is at
[`recordings/techzone-runbook-walkthrough-2.gif`](recordings/techzone-runbook-walkthrough-2.gif) (~6.9 MB, the same narration pacing, made with
`agg --idle-time-limit 40 --last-frame-duration 18 --font-size 16`), for viewing without asciinema installed or
for screen-recording under the narration.

Or convert it to a shareable GIF/video with
[`agg`](https://github.com/asciinema/agg) or upload it to
[asciinema.org](https://asciinema.org) with `asciinema upload`.
