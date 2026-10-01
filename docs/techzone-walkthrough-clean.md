# TechZone Runbook: Clean End-to-End Walkthrough

A straight-through demo path for [`techzone-runbook.md`](techzone-runbook.md):
toolkit setup through a fully active NFS/SMB/S3 deployment, with no detours.

This is **not** a record of a literal live run — it's the golden path,
with every lesson learned from the real troubleshooting sessions
([first walkthrough](techzone-walkthrough.md),
[second walkthrough](techzone-walkthrough-2.md)) folded in as standard
up-front preparation instead of a narrated mistake. If you're looking
for the real debugging story — the SSH tunnel gotcha, the DHCP-colliding
floating IP, the masked `rpcbind` investigation — those are in the two
walkthroughs linked above. This one skips straight to "do it right the
first time."

A terminal reenactment is at
[`recordings/techzone-runbook-walkthrough-clean.cast`](recordings/techzone-runbook-walkthrough-clean.cast) —
narration-paced, ~3.5 minutes, meant to be played and talked over live.

All three protocols (NFS, SMB, S3) are covered — S3 was confirmed live
on a real environment (added to an already-running NFS/SMB cluster,
`deploy` finished `failed=0` with `S3 ACTIVE` and NFS/SMB undisturbed)
before being folded into this clean version.

## The golden path

| Step | What happens |
|---|---|
| Toolkit setup | `spectrumscale setup -s <installer-ip>` |
| Node configuration | All 7 nodes added with roles: 2 NSD/quorum/manager servers, 1 GUI/quorum/admin, 2 protocol/manager, 2 plain clients |
| Storage discovery + NSDs | 3 free disks per server, split into `cesSharedRoot` (shared root) + `fs1` (general use), mirrored across both servers |
| **Pre-flight: `rpcbind`** | Confirm `rpcbind.socket`/`rpcbind.service` are active on both protocol nodes *before* install — a masked `rpcbind` silently blocks NFS regardless of anything else being configured correctly. S3 doesn't depend on it, but NFS does |
| **Pre-flight: floating IPs** | Ping-check candidate export IPs before using them — an IP that collides with what DHCP hands the interface can never be claimed by GPFS |
| **Pre-flight: S3 media** | Confirm the extracted media's `s3_rpms/<os>/` directory actually has packages in it — `enable s3` fails on missing packages otherwise |
| Precheck + install | Callhome disabled and the ephemeral port range set *before* the first precheck, so it passes clean on the first try; install then runs ~25–30 min |
| Confirm cluster | Direct `mmlscluster`/`mmgetstate`/`mmlsfs` check — all 7 nodes active, both filesystems created |
| Protocol configuration | `config protocols` with the pre-verified floating IPs, then `enable nfs smb s3` |
| Precheck-deploy | Clean, S3 included |
| Deploy | `Filesystem`, `Cluster Export Services`, `S3`, `SMB`, `NFS`, `Performance Monitoring`, and `GUI` all come up `ACTIVE` on the first attempt — no retries, no manual IP assignment, nothing left broken |

## Watching the recording

[`recordings/techzone-runbook-walkthrough-clean.cast`](recordings/techzone-runbook-walkthrough-clean.cast)
is an [asciinema](https://asciinema.org) v2 cast file — narration-paced
the same way as the second walkthrough's recording, so it can be played
and talked over live without constantly pausing:

```bash
brew install asciinema   # if you don't already have it
asciinema play docs/recordings/techzone-runbook-walkthrough-clean.cast
```
