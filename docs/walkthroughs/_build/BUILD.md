# Rebuilding the MCP and CLI walkthrough players

The four JSON files in `_build/sources/` are the editable source of truth. Three of them are edited reenactments whose chapters cite a time range of an archived cast; `cli-run.json` is built from a **capture** of a real run instead (see below). The GUI walkthrough is separate and is not generated here. Each chapter contains a title, short screen text, exact narration, and the original cast section used as evidence. Do not edit the generated HTML, cast, GIF or narration separately.

## Requirements and commands

Use Python 3.10+ and `agg` (tested with 1.9.0), with the Menlo font installed. GIF validation also needs Pillow. No network or backend is needed for generation; no command shown in a recording is executed.

From the repository root:

```sh
# Build text outputs only (Python standard library).
python3 docs/walkthroughs/_build/build.py

# Build all outputs and validate the GIFs (agg + Pillow required).
python3 docs/walkthroughs/_build/build.py --gif

# Validate existing exports without changing them.
python3 docs/walkthroughs/_build/build.py --check --gif

# Rebuild one recording.
python3 docs/walkthroughs/_build/build.py --gif --only mcp-install-and-debug

# Check player logic and generated-file consistency.
node docs/walkthroughs/_build/check_players.cjs
```

The builder invokes `agg` with Menlo at 20 pixels, an 88 × 24 terminal, the github-dark background, explicit high-contrast true-color text, no looping, and an idle limit of 120 seconds. The final hold equals the final chapter's duration. Font and renderer versions can change pixel output; timing and content are validated independently.

Narration timing uses whitespace-delimited words × 60 / 135 + 2 seconds, rounded to hundredths per chapter. The same durations drive cast timestamps, GIF frame holds, HTML playback, narration chapter markers and `timings.json`. Each chapter is rendered in one clear-screen event; no scrolling or simulated typing competes with narration. One GIF frame corresponds to one complete chapter.

The builder checks source ranges, line width, screen height, scene order, cast text, narration correspondence, HTML embedded data, GIF frame count, every frame duration and total duration. `check_players.cjs` exercises control logic in a minimal DOM harness; it is not a browser-layout test. Visually inspect the generated GIF at native size after changing the text or font.

## Capture-backed sources

`cli-run.json` has no hand-typed command or output. Each chapter's `lines` mix editorial strings with references that the builder resolves against `_build/captures/<name>.json`, and the build fails if a referenced line is missing:

- `{"cmd": "<phase>", "n": 0}`: the command the backend echoed for that phase, shown as `$ ...` (the toolkit path is shortened).
- `{"out": "<phase>", "has": "<text>", "nth": 0}`: the logged output line containing the text (the `INFO` marker is dropped, nothing else changes).
- `{"out": "<phase>", "from": "<text>", "to": "<text>"}`: a block of consecutive lines, kept unwrapped for tables.
- `{"count": "<phase>", "has": "<text>", "all_have": "<text>", "text": "{n} x ..."}`: how many logged lines match, asserting that every match also contains `all_have`.
- `{"duration": "<phase>", "label": "..."}`: the operation's finish minus start time.

A capture file records, per phase, the echoed `commands`, `started_at` / `finished_at`, and the verbatim `lines` used (headline lines only for very long logs), plus a `note` where something was not seen. `captures/2026-10-05-run.json` was assembled from the backend's operation logs for that run. A source sets its own on-screen `footer` and `note`; the reenactment text is the default. Per-line timing is not recorded, so playback pacing is generated like the others.

## Files and boundaries

- `_build/sources/*.json`: four story definitions. Three cite a time range of an original cast; `cli-run.json` cites phases of a capture.
- `_build/captures/*.json`: verbatim excerpts of a real run's operation logs.
- `_build/build.py`: reproducible generation and consistency checks.
- `_build/check_players.cjs`: player-logic checks.
- `_build/timings.json`: generated chapter and timing manifest.
- Outputs, next to each track: `mcp/install-and-debug`, `mcp/extra-examples`, `mcp/ces-nfs-case-study` and `cli/install-run`, each as `.html`, `.cast`, `.gif` and `.narration.md`.
- The original casts that the source ranges cite are in `../../archive/recordings/`, unchanged.
- `../README.md` is the editorial index; update its totals when narration changes.

The builder only writes the four allow-listed names above. It does not regenerate or overwrite any archived original, the GUI walkthrough, or historical narration. Source ranges refer to original cast time, not GIF time, because the old exports have differing final holds and idle handling.
