# MCP walkthrough

Driving an IBM Storage Scale install in plain language through the [`scale-guinstall` MCP server](../../../mcp-server/README.md). The agent turns each request into a call to the backend, and the backend runs the `spectrumscale` toolkit on the installer node. Follow the [TechZone runbook](../../techzone-runbook.md) for the actual procedure; this shows what it looks like through MCP.

| Recording | Length | Chapters | Watch | Narration |
|---|---:|---:|---|---|
| **A real installation through MCP** (2026-10-06 run, from the transcripts) | 5:10 | 15 | [Player](real-run.html) · [GIF](real-run.gif) · [cast](real-run.cast) | [Script](real-run.narration.md) |
| **MCP installation and diagnostic repair** | 6:46 | 20 | [Player](install-and-debug.html) · [GIF](install-and-debug.gif) · [cast](install-and-debug.cast) | [Script](install-and-debug.narration.md) |
| CES and NFS: from failed health checks to confirmation | 2:52 | 8 | [Player](ces-nfs-case-study.html) · [GIF](ces-nfs-case-study.gif) · [cast](ces-nfs-case-study.cast) | [Script](ces-nfs-case-study.narration.md) |
| Extra examples: context recovery and adding S3 | 0:47 | 4 | [Player](extra-examples.html) · [GIF](extra-examples.gif) · [cast](extra-examples.cast) | [Script](extra-examples.narration.md) |

## What each one shows

- **A real installation through MCP.** The actual calls of the 2026-10-06 run, in order: readiness checks, disks, setup, nodes, NSDs, call home and cluster settings, then precheck, install, deploy and postchecks. Two real hiccups are left in: a dry run that caught a wrong toolkit argument, and `check_operation` results too large for one tool reply (read from a saved file instead). It is copied from the session transcripts, not reenacted; the operator's words are verbatim, the agent's replies are not shown, and the protocols step was done in the GUI.

- **Installation and diagnostic repair.** Check the installer, inspect nodes and disks, assign the seven node roles, define storage, recover from configuration errors, configure the protocols, install, deploy and verify. The last part is a separate episode: a misleading "SSH connection failed" from one tool while another reached the same nodes, how it was told apart from a real failure, fixed, and confirmed after restarting.
- **CES and NFS case.** Why a deploy reported `failed=0` while CES and NFS stayed inactive, across two environments. It ends with **NFS and SMB working, not S3**. The two causes it found, export addresses that were not actually free and a masked `rpcbind`, are written up in [runbook §9](../../techzone-runbook.md).
- **Extra examples.** Two separate short examples: recovering the context of a running operation, and adding S3 to an existing cluster. They are not a continuous run.

## Read this before trusting a detail

Except for the real run, these are **edited reenactments** of real sessions, not footage. Some operator requests are reconstructed rather than quoted, long operations are summarized, and a few bugs shown were later fixed (the SSH test bug, and the removed `perfmon_node` parameter). Chapters label this on screen. The corrections that apply to each original are listed in the [archive](../../archive/README.md), and the source of each chapter is its cited range in the original cast.

Do not copy a chapter's wording as a recipe. Use the runbook.
