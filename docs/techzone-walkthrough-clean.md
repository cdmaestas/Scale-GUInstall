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
narration-paced, ~3.6 minutes, meant to be played and talked over live.

All three protocols (NFS, SMB, S3) are covered — S3 was confirmed live
on a real environment (added to an already-running NFS/SMB cluster,
`deploy` finished `failed=0` with `S3 ACTIVE` and NFS/SMB undisturbed)
before being folded into this clean version. `postcheck-install` and
`postcheck-deploy` were also run live on that same environment for
this version — both came back clean (`SUCCESS`, `All services
running`), confirming the toolkit's own post-phase health checks
agree with what `deploy` already reported.

This version trims out the pre-flight checks (confirming `rpcbind` is
active, confirming floating IPs are free, confirming S3 media is
present) for a tighter demo — they still matter in a real run, and are
exactly where the real walkthroughs' debugging stories start. Skip them
at your own risk; they're cheap to run and expensive to skip.

## The golden path

| Step | What happens |
|---|---|
| Toolkit setup | `spectrumscale setup -s <installer-ip>` |
| Node configuration | All 7 nodes added with roles: 2 NSD/quorum/manager servers, 1 GUI/quorum/admin, 2 protocol/manager, 2 plain clients |
| Storage discovery + NSDs | 3 free disks per server, split into `cesSharedRoot` (shared root) + `fs1` (general use), mirrored across both servers |
| Precheck + install | Callhome disabled and the ephemeral port range set *before* the first precheck, so it passes clean on the first try; install then runs ~25–30 min |
| **Postcheck-install** | `spectrumscale install --postcheck` — the toolkit's own verification, independent of the install run's own exit status: `GPFS ACTIVE`, `NSDs ACTIVE`, `Performance Monitoring ACTIVE`, `GUI ACTIVE` |
| Protocol configuration | `config protocols` with the floating IPs, then `enable nfs smb s3` |
| Precheck-deploy | Clean, S3 included |
| Deploy | `Filesystem`, `Cluster Export Services`, `S3`, `SMB`, `NFS`, `Performance Monitoring`, and `GUI` all come up `ACTIVE` on the first attempt — no retries, no manual IP assignment, nothing left broken |
| **Postcheck-deploy** | `spectrumscale deploy --postcheck` — same idea, for the protocol deploy: every component independently reconfirmed `ACTIVE` |

## Watching the recording

[`recordings/techzone-runbook-walkthrough-clean.cast`](recordings/techzone-runbook-walkthrough-clean.cast)
is an [asciinema](https://asciinema.org) v2 cast file — narration-paced
the same way as the second walkthrough's recording, so it can be played
and talked over live without constantly pausing:

```bash
brew install asciinema   # if you don't already have it
asciinema play docs/recordings/techzone-runbook-walkthrough-clean.cast
```

A silent animated rendering of the same cast is at
[`recordings/techzone-runbook-walkthrough-clean.gif`](recordings/techzone-runbook-walkthrough-clean.gif) (~2.4 MB, the same narration pacing, made with
`agg --idle-time-limit 21 --last-frame-duration 17 --font-size 16`), for viewing without asciinema installed or
for screen-recording under the narration.
