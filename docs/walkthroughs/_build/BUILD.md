# Rebuilding the MCP and CLI walkthrough players

The four JSON files in `_build/sources/` are the editable source of truth. The GUI walkthrough is separate and is not generated here. Each chapter contains a title, short screen text, exact narration, and the original cast section used as evidence. Do not edit the generated HTML, cast, GIF or narration separately.

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

## Files and boundaries

- `_build/sources/*.json`: four story definitions, each chapter citing a time range of an original cast.
- `_build/build.py`: reproducible generation and consistency checks.
- `_build/check_players.cjs`: player-logic checks.
- `_build/timings.json`: generated chapter and timing manifest.
- Outputs, next to each track: `mcp/install-and-debug`, `mcp/extra-examples`, `mcp/ces-nfs-case-study` and `cli/overview`, each as `.html`, `.cast`, `.gif` and `.narration.md`.
- The original casts that the source ranges cite are in `../../archive/recordings/`, unchanged.
- `../README.md` is the editorial index; update its totals when narration changes.

The builder only writes the four allow-listed names above. It does not regenerate or overwrite any archived original, the GUI walkthrough, or historical narration. Source ranges refer to original cast time, not GIF time, because the old exports have differing final holds and idle handling.
