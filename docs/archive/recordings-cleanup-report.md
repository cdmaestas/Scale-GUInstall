# Recording cleanup completed

> **Historical record.** This report describes the layout before the `docs/walkthroughs/` restructure; the links below were repointed to the files' new locations, but file names in the prose (for example `build_recordings.py`) are the old ones. See the [walkthroughs index](../walkthroughs/README.md).

The primary presentation is now an edited MCP installation followed chronologically by its diagnostic repair. Three shorter companions cover the terminal sequence, unique MCP examples, and the CES/NFS case. The GUI screenshot tour remains separate and unchanged.

## Watch and narrate

| Recording | Measured GIF duration | Chapters | Player | GIF | Script |
|---|---:|---:|---|---|---|
| MCP install and diagnostic repair | **6:46.67** | 20 | [Open](../walkthroughs/mcp/install-and-debug.html) | [Preview](../walkthroughs/mcp/install-and-debug.gif) | [Narration](../walkthroughs/mcp/install-and-debug.narration.md) |
| Clean terminal overview | **3:01.11** | 9 | [Open](recordings/terminal-overview.html) | [Preview](recordings/terminal-overview.gif) | [Narration](narration-terminal-overview.md) |
| Extra MCP examples | **0:47.55** | 4 | [Open](../walkthroughs/mcp/extra-examples.html) | [Preview](../walkthroughs/mcp/extra-examples.gif) | [Narration](../walkthroughs/mcp/extra-examples.narration.md) |
| CES/NFS case study | **2:52.90** | 8 | [Open](../walkthroughs/mcp/ces-nfs-case-study.html) | [Preview](../walkthroughs/mcp/ces-nfs-case-study.gif) | [Narration](../walkthroughs/mcp/ces-nfs-case-study.narration.md) |

The new players start paused. Use chapter selection, previous/next, pause, restart or pace controls while narrating; collapse the narration panel for a cleaner screen recording. GIFs are silent, play once, and stop on the closing frame. These are concise chapter summaries regenerated from source material, not cuts of scrolling terminal footage. Narration is supplied as text, not recorded audio.

The combined story is about seven seconds longer than the approximate 6:40 target to preserve a natural 135-word-per-minute pace and two-second chapter buffers. Screen text is 20-pixel Menlo at 1084 × 700, with bright cyan headings and near-white explanatory text. Every chapter starts on a clean screen.

## Editorial changes

- Kept installation, final verification and the later debugging epilogue in chronological order. The stale-client/restart lesson remains intact.
- Labeled edited reenactments, reconstructed request summaries, historical fixed bugs and the removed monitoring parameter.
- Retained the successful recap and final health verification alongside the historical ASYNC FAILED line.
- Removed unsupported claims that disk placement proves mirroring or that ping silence proves an IP is free.
- Shortened the old MCP montage to its distinct context-recovery and S3-extension examples. The mislabeled deployment/roles scene is omitted; its historical correction is documented.
- Condensed the CES/NFS case while preserving the two-environment transition, root-cause checks and successful NFS/SMB result. It is not presented as an S3 deployment.
- Preserved all six original GIF/cast pairs. Historical supporting pages now lead readers to the curated index and archive caveats. The original fast runbook is outside the primary viewing list.

## Files delivered

- Four source JSON files under [recordings/sources](../walkthroughs/_build/sources/), carrying screen text, narration and original source ranges.
- Four generated sets of `.html`, `.cast` and `.gif` files, linked above.
- Four synchronized `narration-*.md` scripts, linked above.
- [Viewing index](../walkthroughs/README.md), [historical archive](README.md), [build recipe](../walkthroughs/_build/BUILD.md), [timing manifest](../walkthroughs/_build/timings.json).
- [Exporter](../walkthroughs/_build/build.py) and [player logic checks](../walkthroughs/_build/check_players.cjs).
- Root README discovery link and historical-source notices on the three older walkthrough pages, the MCP article and three old MCP narration scripts.

## Validation

- Visually inspected all **41 final GIF chapter frames**, using contact sheets and a native-size detail check. No clipped lines or inherited scrollback; the heading contrast was improved after the first render.
- Decoded every GIF frame. All 41 frame delays match their narration-derived chapter timings, all total durations match, and infinite looping is disabled.
- Checked all source ranges, terminal width/height bounds, clear-screen cast events, generated narration and HTML data for consistency.
- Executed player logic checks for all 41 chapters: content, pause, previous/next, restart, chapter selection, slower pace, keyboard actions, full playback and stopping at the end.
- Verified the original six GIFs, six casts and GUI HTML byte-for-byte against HEAD. No originals were altered.
- Checked relative document links and whitespace in the affected documentation.

The browser tool rejected opening the local HTML file under its URL policy. HTML layout therefore has not been visually verified in a browser; player behavior was tested in an offline DOM harness, which is not a layout engine. GIF rendering was inspected directly. No spoken-audio synchronization trial or live cluster operation was performed. The source capture log remains the provenance record; the new recordings summarize it rather than independently revalidating the historic installation.

## Repository hygiene

No uncommitting, deletion, history rewrite, force-push or publishing was necessary. Existing links remain valid because originals retain their paths. The six original GIFs occupy **28,621,182 bytes (28.6 MB)**. The reachable Git history for those paths contains six GIF blobs, one per original, rather than a series of duplicate revisions. The four new GIFs together occupy about **0.90 MB**.

This size does not justify disrupting history for this cleanup. If future repeated binary revisions cause repository growth, Git LFS or release-hosted previews can be discussed separately. This change leaves the historical record intact and uses compact generated previews with reproducible sources.
