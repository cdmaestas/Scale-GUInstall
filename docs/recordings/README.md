# Walkthroughs and narrated recordings

Start with the format that matches your audience. The GUI tour explains visible controls; the terminal overview illustrates the installation order; the MCP story follows a historical install and diagnostic repair. They are separate perspectives, not footage of the same continuous run.

| Recording | Duration | Watch / record | Silent preview | Narration |
|---|---:|---|---|---|
| **MCP installation and diagnostic repair** | **6:46.67** | [Chapter player](mcp-install-and-debug.html) · [cast](mcp-install-and-debug.cast) | [GIF](mcp-install-and-debug.gif) | [Script](../narration-mcp-install-and-debug.md) |
| **Clean terminal overview** | **3:01.11** | [Chapter player](terminal-overview.html) · [cast](terminal-overview.cast) | [GIF](terminal-overview.gif) | [Script](../narration-terminal-overview.md) |
| **GUI tour** | **3:38.80** | [Screenshot walkthrough](gui-walkthrough.html) | Separate GUI content | [Script](../narration-gui-walkthrough.md) |
| Extra MCP examples: context recovery and S3 | 0:47.55 | [Chapter player](mcp-extra-examples.html) · [cast](mcp-extra-examples.cast) | [GIF](mcp-extra-examples.gif) | [Script](../narration-mcp-extra-examples.md) |
| CES/NFS troubleshooting case | 2:52.90 | [Chapter player](ces-nfs-case-study.html) · [cast](ces-nfs-case-study.cast) | [GIF](ces-nfs-case-study.gif) | [Script](../narration-ces-nfs-case-study.md) |

## Recording your narration

Open a chapter player locally in a browser. The four new players start paused and include chapter selection, previous/next, pause, restart, pace selection and synchronized narration. Space toggles playback; arrow keys change chapters when focus is outside a control. Collapse the narration panel if you want only the presentation on screen. Playback stops after the final chapter.

The new material is paced at **135 words per minute plus two seconds per chapter**, rounded to hundredths of a second. GIFs are silent, play once, and have no built-in controls; reopen/reload to replay. They use 20-pixel Menlo text at 1084 × 700. Prefer HTML for live narration, especially when you need to pause. The existing GUI player retains its original controls and 150-word-per-minute timing.

## What these recordings establish

- The combined MCP story follows installation **before** the debugging epilogue. Its scene summaries derive from recorded calls/results; some original operator requests were reconstructed. They are labeled as request summaries rather than quotations. [Capture provenance](../nlp-capture-log.md).
- The clean terminal overview is an instructional reenactment. Prerequisites are assumed, and replica settings must be checked separately from disk placement.
- The CES/NFS case spans two environments and ends with **NFS and SMB**, not S3. Ping silence is not evidence of address availability.
- Historical fixed bugs and removed parameters are explicitly identified. These edited summaries are not a replacement for the [current runbook](../techzone-runbook.md).
- The GUI tour is a static demonstration of controls with no live installation attached.

## Sources, exports and history

[Build and validation recipe](BUILD.md) · [Scene sources](sources/) · [Timings](timings.json) · [Historical originals and caveats](ARCHIVE.md) · [Cleanup outcome](../recordings-cleanup-report.md)

All six original GIF/cast pairs remain at their original paths. No Git history rewrite or deletion was needed. Use the primary links above for the cleaned presentation rather than concatenating historical exports.
