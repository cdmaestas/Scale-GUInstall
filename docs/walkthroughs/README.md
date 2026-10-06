# Walkthroughs

Three ways to drive the same install, plus the procedure they all follow.

| Walkthrough | What it covers | Watch | Read |
|---|---|---|---|
| **[GUI](gui/README.md)** | The web interface, step by step: Prepare Software through Install & Deploy. A static tour of the controls. | [Player](gui/player.html) · 3:38 | [Page](gui/README.md) · [Narration](gui/narration.md) |
| **[MCP](mcp/README.md)** | Driving the install in plain language through the `scale-guinstall` MCP tools, then fixing a problem the same way. | [Player](mcp/install-and-debug.html) · [GIF](mcp/install-and-debug.gif) · 6:47 | [Page](mcp/README.md) · [Narration](mcp/install-and-debug.narration.md) |
| **[CLI](cli/README.md)** | The `spectrumscale` commands of one real run, in order, with the toolkit's own output. | [Player](cli/install-run.html) · [GIF](cli/install-run.gif) · 6:27 | [Page](cli/README.md) · [Narration](cli/install-run.narration.md) |

The step-by-step procedure, with every gotcha found on real environments, is the **[TechZone runbook](../techzone-runbook.md)**. The walkthroughs show the shape of the work; the runbook is what to follow.

## How to use the players

Open a `.html` player in a browser. It starts paused and has chapter selection, previous/next, pause, restart, pace selection and a synchronized narration panel. Space toggles playback and the arrow keys change chapter when focus is outside a control. Collapse the narration panel for a cleaner screen recording. The `.gif` files are silent, play once, stop on the last frame and have no controls; the `.cast` files are the same content in asciinema format.

New chapter players are paced at 135 words per minute plus two seconds per chapter. The GUI player keeps its original 150 words per minute.

## What these are, and are not

- **They are edited summaries, not footage.** Each chapter is a clean screen of text regenerated from a source file, not a cut of scrolling terminal output. Where an operator request was reconstructed rather than quoted, or a bug has since been fixed, the chapter says so.
- **The GUI tour is static.** Its screenshots come from a demo with no backend attached, so it shows the controls, not a live installation.
- **The CLI walkthrough is built from a real run.** Its commands and output lines are quoted from the operation logs of the 2026-10-05 installation, and the build fails if a quoted line is missing from the capture. Per-line timing was not recorded, so the pacing is generated.
- **Provenance** for the MCP material is in the [capture log](../archive/nlp-capture-log.md).

## Not captured yet

These need a fresh TechZone environment, because the previous one is gone:

- A GUI tour against a real cluster (7 nodes, 6 NSDs, protocols, install and deploy previews) instead of the empty-state demo.
- A real-time recording (`asciinema`) of the same commands, if timing as well as content should be real.
- An MCP walkthrough built from a single clean run, with no reconstructed requests.

## More

- **[Archive](../archive/README.md)**: the original recordings, older walkthrough pages and capture notes, kept unchanged for provenance and with their known corrections listed.
- **[Build and validation recipe](_build/BUILD.md)** · [scene sources](_build/sources/) · [timings](_build/timings.json): how the MCP and CLI players, casts, GIFs and narration scripts are regenerated from one source.
