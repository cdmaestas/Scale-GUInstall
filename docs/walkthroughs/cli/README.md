# CLI walkthrough

The `spectrumscale` commands of one real installation, in order, with the toolkit's own output at each step. It is what the GUI and the MCP tools run underneath. Follow the [TechZone runbook](../../techzone-runbook.md) for the procedure and its gotchas.

| Recording | Length | Chapters | Watch | Narration |
|---|---:|---:|---|---|
| **A real installation, command by command** | 8:13 | 18 | [Player](install-run.html) · [GIF](install-run.gif) · [cast](install-run.cast) | [Script](install-run.narration.md) |
| Verification on a protocol node (live recording) | 1:05 | 6 | [GIF](verification-run.gif) · [cast](verification-run.cast) | [Script](verification-run.narration.md) |

## What it covers

Setup, defining seven nodes and six NSDs, call home and cluster settings, configuring and enabling NFS, SMB and S3, then each phase of the install and the deploy (`--precheck`, the run, `--postcheck`). Two chapters show where the install and deploy time went, read from the toolkit's timestamps. It ends with the `mmces` and `mmhealth` checks on a protocol node, a look at the SMB `TIPS` status, and the time each operation took.

## Where it comes from

It was built from the logs of the installation of **2026-10-06** on a TechZone environment (installer plus seven cluster nodes, IBM Storage Scale 6.0.1.1, RHEL 9; the environment no longer exists). The 2026-10-05 run's [capture](../_build/captures/2026-10-05-run.json) is kept for reference.

- **Commands** are the lines the backend echoed when it ran each operation (`sudo -n .../spectrumscale ...`). The path is shortened to `.../` on screen.
- **Output lines** are quoted verbatim, with the `INFO` marker dropped. For the install and the deploy, which log over a thousand lines each, only the headline lines are used. Their text comes from the toolkit's own log files, copied off the installer before the environment was released.
- **Times are real.** The `+m:ss` marks are seconds since the toolkit's log opened, from its millisecond timestamps. The "where the time went" chapters show the longest gaps between `TASK` lines; tasks run in parallel across nodes, so that is log spacing, not the cost on one node.
- **The build checks the quotes.** Each quoted line is looked up in the [capture file](../_build/captures/2026-10-06-run.json), and the build fails if it is not there.
- **Nobody typed these commands.** The run was driven through the MCP tools, with the protocols applied from the GUI, and the backend executed the commands.
- **Playback pacing is generated** at 135 words per minute plus two seconds per chapter; it is not the real elapsed time.
- **Things left in on purpose:** the expected `FATAL` and `WARN` lines from defining nodes, the install's retry lines (4 for the GPFS daemon wait, 2 for the GUI; the toolkit logs each batch at a single instant, so they show that retries happened, not when), the one `ASYNC FAILED` line in the deploy log at +4:42 (the log has no error text for it, so its cause is still unknown; the recaps show `failed=0` and the postcheck passes), and the SMB `TIPS` status.
- **Gaps:** five of the six NSD add commands and some node commands were seen echoed, and the screens say which. The backend did not keep the `setup` output this run. The node table is trimmed on screen by its trailing OS and architecture columns to fit the terminal.

**The verification recording is live output, not generated.** Six read-only commands were run over SSH from the Mac through the installer to `scale-proto1`, recorded with asciinema, about an hour after the deploy. The prompt and typing are drawn by the recording script and the screen is cleared between commands; the output is real. It shows the SMB `TIPS` from the install chapters already cleared (`smb_sensors_active` at 18:58:27, fifty minutes after the TIPS began at 18:08:27).

The earlier terminal overview, an edited reenactment, is kept in the [archive](../../archive/README.md).
