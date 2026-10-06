# CLI walkthrough

The `spectrumscale` commands of one real installation, in order, with the toolkit's own output at each step. It is what the GUI and the MCP tools run underneath. Follow the [TechZone runbook](../../techzone-runbook.md) for the procedure and its gotchas.

| Recording | Length | Chapters | Watch | Narration |
|---|---:|---:|---|---|
| **A real installation, command by command** | 6:27 | 16 | [Player](install-run.html) · [GIF](install-run.gif) · [cast](install-run.cast) | [Script](install-run.narration.md) |

## What it covers

Setup, defining seven nodes and six NSDs, call home and cluster settings, configuring and enabling NFS, SMB and S3, then each phase of the install and the deploy (`--precheck`, the run, `--postcheck`). It ends with the `mmces` and `mmhealth` checks on a protocol node, a look at the SMB `TIPS` status, and the time each operation took.

## Where it comes from

It was built from the logged output of the installation of **2026-10-05** on a TechZone environment (installer plus seven cluster nodes, IBM Storage Scale 6.0.1.1, RHEL 9; the environment no longer exists).

- **Commands** are the lines the backend echoed when it ran each operation (`sudo -n .../spectrumscale ...`). The path is shortened to `.../` on screen.
- **Output lines** are quoted verbatim from the operation logs, with the `INFO` marker dropped. For the install and the deploy, which log over a thousand lines each, only the headline lines are used.
- **The build checks the quotes.** Each quoted line is looked up in the [capture file](../_build/captures/2026-10-05-run.json), and the build fails if it is not there.
- **Nobody typed these commands.** The run was driven through the MCP tools, with the protocols applied from the GUI, and the backend executed the commands.
- **Pacing is generated** at 135 words per minute plus two seconds per chapter. Per-line timestamps were not recorded; only each operation's start and finish times were.
- **Things left in on purpose:** the expected `FATAL` and `WARN` lines from defining nodes, the install's retry lines, the one `ASYNC FAILED` line in the deploy log (its cause was not investigated; the recap shows `failed=0` and the postcheck passes), and the SMB `TIPS` status.
- **Gaps:** only some of the per-node and per-NSD commands were seen echoed, and the screens say which. The finish time of the node definition was not captured.

The earlier terminal overview, an edited reenactment, is kept in the [archive](../../archive/README.md).
