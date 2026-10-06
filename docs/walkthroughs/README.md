# Walkthroughs

Three ways to drive the same install, plus the procedure they all follow.

| Walkthrough | What it covers | Watch | Read |
|---|---|---|---|
| **[GUI](gui/README.md)** | The web interface, step by step, from screenshots of a real run: Prepare Software through Install & Deploy, with the one live action (Apply Protocols) and what the GUI does not show. | [Player](gui/player.html) · [GIF](gui/tour.gif) · 9:45 | [Page](gui/README.md) · [Narration](gui/narration.md) |
| **[MCP](mcp/README.md)** | Driving the install in plain language through the `scale-guinstall` MCP tools, then fixing a problem the same way. Includes a recording of the real 2026-10-06 run's calls. | [Player](mcp/real-run.html) · [GIF](mcp/real-run.gif) · 5:10 (real run); [repair episode](mcp/install-and-debug.html) 6:47 | [Page](mcp/README.md) · [Narration](mcp/install-and-debug.narration.md) |
| **[CLI](cli/README.md)** | The `spectrumscale` commands of one real run, in order, with the toolkit's own output. | [Player](cli/install-run.html) · [GIF](cli/install-run.gif) · 8:13 | [Page](cli/README.md) · [Narration](cli/install-run.narration.md) |

The step-by-step procedure, with every gotcha found on real environments, is the **[TechZone runbook](../techzone-runbook.md)**. The walkthroughs show the shape of the work; the runbook is what to follow.

## How to use the players

Open a `.html` player in a browser. It starts paused and has chapter selection, previous/next, pause, restart, pace selection and a synchronized narration panel. Space toggles playback and the arrow keys change chapter when focus is outside a control. Collapse the narration panel for a cleaner screen recording. The `.gif` files are silent, play once, stop on the last frame and have no controls; the `.cast` files are the same content in asciinema format.

New chapter players are paced at 135 words per minute plus two seconds per chapter. The GUI player keeps its original 150 words per minute.

## What these are, and are not

- **They are edited summaries, not footage.** Each chapter is a clean screen of text regenerated from a source file, not a cut of scrolling terminal output. Where an operator request was reconstructed rather than quoted, or a bug has since been fixed, the chapter says so.
- **The GUI tour is real screenshots, mostly in Dry Run.** They were taken against the installer's backend during the 2026-10-06 run; only Apply Protocols was run live, and the install and deploy went through the MCP tools, so the GUI never shows a finished cluster.
- **The CLI walkthrough is built from a real run.** Its commands and output lines are quoted from the operation records and the toolkit's own logs of the 2026-10-06 installation, and the build fails if a quoted line is missing from the capture. The `+m:ss` times on screen are the toolkit's real log timestamps; the playback pacing is still generated from the narration.
- **The MCP real run is copied from the session transcripts.** Every call, argument and (shortened) result is derived from the recorded tool calls, and the operator's quoted words are verbatim; the build script asserts each quote. The other MCP recordings are edited reenactments; their provenance is in the [capture log](../archive/nlp-capture-log.md).

## Still not covered

- **The GUI against a finished cluster.** The GUI only knows what was configured through it, and the install and deploy ran through MCP, so it never shows a completed cluster. Running the install from the GUI would be a separate capture.
- **Real-time recording of the install itself.** The install and deploy are 25 and 17 minutes; their timing is real (from the toolkit logs) but they were not recorded as live terminal casts. Only the short verification commands were.
- **The MCP real run spans two sessions** (a context clear in the middle), the protocols step was done in the GUI, and the agent's replies are not shown; its chapters say so.

## More

- **[Archive](../archive/README.md)**: the original recordings, older walkthrough pages and capture notes, kept unchanged for provenance and with their known corrections listed.
- **[Build and validation recipe](_build/BUILD.md)** · [scene sources](_build/sources/) · [timings](_build/timings.json): how the MCP and CLI players, casts, GIFs and narration scripts are regenerated from one source. The GUI tour has its own builder, [`build_gui.py`](_build/build_gui.py).
