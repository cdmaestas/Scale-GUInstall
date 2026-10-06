#!/usr/bin/env python3
"""Build the GUI walkthrough (player, GIF, narration script, README) from sources/gui-tour.json and gui/screenshots/.

Usage: python3 docs/walkthroughs/_build/build_gui.py [--gif]   (the GIF needs Pillow)
Timing matches the other walkthroughs: words * 60 / words_per_minute + buffer_seconds per slide."""
import argparse
import base64
import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUI = ROOT.parent / 'gui'
SHOTS = GUI / 'screenshots'


def load():
    data = json.loads((ROOT / 'sources' / 'gui-tour.json').read_text())
    t = 0.0
    for s in data['slides']:
        words = len((s.get('narration') or s['text']).split())
        s['duration'] = round(words * 60 / data['words_per_minute'] + data['buffer_seconds'], 2)
        s['start'] = round(t, 2)
        t += s['duration']
        if 'image' in s:
            assert (SHOTS / s['image']).exists(), s['image']
    data['duration'] = round(t, 2)
    used = {s['image'] for s in data['slides'] if 'image' in s}
    assert used == {p.name for p in SHOTS.glob('*.jpg')}, ('unused or missing screenshots', used ^ {p.name for p in SHOTS.glob('*.jpg')})
    return data


def clock(sec):
    return f'{int(sec // 60)}:{int(sec % 60):02d}'


def narration(data):
    out = ['# Narration script: GUI walkthrough', '',
           'Companion narration for [`player.html`](player.html), a narration-paced slideshow of the screenshots in [README.md](README.md). '
           'Open the player, press Play, and read each passage aloud while its slide is showing; each slide holds for the time its words take at '
           f'{data["words_per_minute"]} words per minute plus {data["buffer_seconds"]} seconds. Generated from `_build/sources/gui-tour.json`; do not edit by hand.', '',
           f'Total length {clock(data["duration"])}.', '', '---', '']
    for s in data['slides']:
        out += [f'### {s["title"]} ({clock(s["start"])}, {s["duration"]:.1f}s)', '', f'"{s.get("narration") or s["text"]}"', '']
    return '\n'.join(out)


def readme(data):
    out = ['# GUI walkthrough: configuring a real cluster', '',
           'A tour of the Scale GUInstall interface, built from screenshots taken while a real IBM Storage Scale 6.0.1.1 cluster was installed on '
           '**2026-10-06** (installer plus seven nodes on a TechZone environment that no longer exists). For the commands that ran underneath, see the '
           '[CLI walkthrough](../cli/README.md); for the conversation that drove them, the [MCP walkthrough](../mcp/README.md).', '',
           '| Recording | Length | Slides | Watch | Narration |', '|---|---:|---:|---|---|',
           f'| **GUI tour** | {clock(data["duration"])} | {len(data["slides"])} | [Player](player.html) · [GIF](tour.gif) | [Script](narration.md) |', '',
           '## What is real and what is not', '',
           '- **The screenshots are real.** They were taken from the GUI in a browser against the installer node\'s backend, through an SSH tunnel.',
           '- **Dry Run was on for nearly every step.** The one live action was Apply Protocols (slides 15 and 16); Dry Run was switched back on afterwards.',
           '- **The install and deploy did not run from the GUI.** They were run through the MCP tools, so the GUI\'s header still says "No cluster configured" '
           'and "Install Service: Not Run": it shows GUI-side state, not what the backend did.',
           '- **The GUI previews and the backend\'s real commands agree.** Both use the same flags per node, in a different order (slide 6), and the real NSD commands also set the filesystem and pool.',
           '- **The Skip SSH check option** is ticked in the screenshot of the install page; the real run\'s install and deploy commands did not use it.',
           '- **Enable Daemon and node identity (TLS)** is marked required for 6.0.1+ on the install page; the MCP runs skipped it and the deploys still passed. This is untested territory (slide 19).',
           '- **Not run:** Populate from Cluster and Pre/Post Checks are shown idle.', '',
           '## The tour', '']
    for i, s in enumerate(data['slides']):
        out += [f'### {s["title"]}', '']
        if 'image' in s:
            out += [f'![{s["title"]}](screenshots/{s["image"]})', '']
        out += [f'> {s.get("narration") or s["text"]}', '']
    out += ['## Rebuilding', '',
            'Edit `_build/sources/gui-tour.json` (or replace a screenshot with the same name), then run `python3 docs/walkthroughs/_build/build_gui.py --gif` '
            'from the repository root. Pillow is needed for the GIF. The player, narration script, GIF and this page are generated; do not edit them by hand.', '']
    return '\n'.join(out)


PLAYER = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GUI walkthrough: configuring a real cluster</title>
<style>
:root{--bg:#0a0a0a;--panel:#161616;--border:#2a2a2a;--text:#e8e8e8;--dim:#9a9a9a;--accent:#0f62fe}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;height:100%;overflow:hidden}
#stage{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;padding:20px;gap:14px}
#counter{font-size:13px;color:var(--dim);letter-spacing:.04em}#title{font-size:22px;font-weight:600;text-align:center}
#wrap{flex:1;width:100%;max-width:1000px;display:flex;align-items:center;justify-content:center;min-height:0}
#wrap img{max-width:100%;max-height:100%;border:1px solid var(--border);border-radius:8px;box-shadow:0 8px 40px rgba(0,0,0,.5);object-fit:contain}
#textslide{max-width:760px;font-size:24px;line-height:1.5;text-align:center;padding:40px}
#caption{max-width:900px;font-size:17px;line-height:1.55;color:var(--dim);text-align:center;min-height:5em}
#track{width:100%;max-width:1000px;height:4px;background:var(--border);border-radius:2px;overflow:hidden}#fill{height:100%;width:0;background:var(--accent)}
#controls{display:flex;align-items:center;gap:16px;padding:6px 0}
button{background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px 16px;font-size:14px;cursor:pointer}button:hover{background:#222}button:disabled{opacity:.4;cursor:default}
#hint{position:fixed;bottom:10px;right:16px;font-size:11px;color:#666}
</style></head><body>
<div id="stage"><div id="counter"></div><div id="title"></div><div id="wrap"></div><div id="caption"></div>
<div id="track"><div id="fill"></div></div>
<div id="controls"><button id="prev">&larr; Prev</button><button id="play">Play</button><button id="next">Next &rarr;</button></div></div>
<div id="hint">Silent playback; read the narration script aloud. Starts paused. Space = play/pause, arrows = navigate.</div>
<script>
const slides = __SLIDES__;
let idx = 0, playing = false, elapsed = 0, last = null;
const $ = id => document.getElementById(id);
function render() {
  const s = slides[idx];
  $('counter').textContent = `${idx + 1} / ${slides.length}`;
  $('title').textContent = s.title;
  const wrap = $('wrap'); wrap.innerHTML = '';
  if (s.image) { const im = document.createElement('img'); im.src = s.image; im.alt = s.title; wrap.appendChild(im); $('caption').textContent = s.narration; }
  else { const d = document.createElement('div'); d.id = 'textslide'; d.textContent = s.text; wrap.appendChild(d); $('caption').textContent = ''; }
  $('fill').style.width = '0%'; elapsed = 0;
  $('prev').disabled = idx === 0; $('next').disabled = idx === slides.length - 1;
}
function tick(ts) {
  if (last === null) last = ts;
  const dt = (ts - last) / 1000; last = ts;
  if (playing) {
    elapsed += dt; const s = slides[idx];
    $('fill').style.width = Math.min(100, elapsed / s.duration * 100) + '%';
    if (elapsed >= s.duration) next(true);
  }
  requestAnimationFrame(tick);
}
function next(auto) { if (idx < slides.length - 1) { idx++; render(); } else if (auto) { playing = false; $('play').textContent = 'Play'; } }
function prev() { if (idx > 0) { idx--; render(); } }
function toggle() { playing = !playing; $('play').textContent = playing ? 'Pause' : 'Play'; }
$('next').onclick = () => next(false); $('prev').onclick = prev; $('play').onclick = toggle;
document.addEventListener('keydown', e => { if (e.key === ' ') { e.preventDefault(); toggle(); } if (e.key === 'ArrowRight') next(false); if (e.key === 'ArrowLeft') prev(); });
render(); requestAnimationFrame(tick);
</script></body></html>
'''


def player(data):
    slides = []
    for s in data['slides']:
        d = {'title': s['title'], 'duration': s['duration']}
        if 'image' in s:
            d['image'] = 'data:image/jpeg;base64,' + base64.b64encode((SHOTS / s['image']).read_bytes()).decode()
            d['narration'] = s['narration']
        else:
            d['text'] = s['text']
        slides.append(d)
    return PLAYER.replace('__SLIDES__', json.dumps(slides, ensure_ascii=False).replace('<', '\\u003c'))


def gif(data):
    from PIL import Image, ImageDraw, ImageFont
    W, H, IMG_H = 1000, 800, 600
    title_f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 24)
    body_f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 17)
    frames, durations = [], []
    for s in data['slides']:
        im = Image.new('RGB', (W, H), (10, 10, 10))
        d = ImageDraw.Draw(im)
        d.text((W // 2, 24), s['title'], font=title_f, fill=(232, 232, 232), anchor='mm')
        text = s.get('narration') or s['text']
        if 'image' in s:
            im.paste(Image.open(SHOTS / s['image']).convert('RGB'), ((W - 800) // 2, 50))
            y = 50 + IMG_H + 14
            for line in textwrap.wrap(text, 112)[:5]:
                d.text((W // 2, y), line, font=body_f, fill=(170, 170, 170), anchor='ma')
                y += 24
        else:
            y = 220
            for line in textwrap.wrap(text, 52):
                d.text((W // 2, y), line, font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 28), fill=(232, 232, 232), anchor='ma')
                y += 42
        frames.append(im.quantize(colors=96, method=Image.Quantize.MEDIANCUT))
        durations.append(int(round(s['duration'] * 1000)))
    frames[0].save(GUI / 'tour.gif', save_all=True, append_images=frames[1:], duration=durations, loop=1, optimize=True)
    check = Image.open(GUI / 'tour.gif')
    assert check.n_frames == len(data['slides'])
    total = 0
    for i in range(check.n_frames):
        check.seek(i)
        total += check.info['duration']
    assert abs(total / 1000 - data['duration']) < 0.2 * len(data['slides']), (total, data['duration'])
    return (GUI / 'tour.gif').stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gif', action='store_true')
    args = ap.parse_args()
    data = load()
    (GUI / 'player.html').write_text(player(data))
    (GUI / 'narration.md').write_text(narration(data))
    (GUI / 'README.md').write_text(readme(data))
    result = {'slides': len(data['slides']), 'seconds': data['duration']}
    if args.gif:
        result['gif_bytes'] = gif(data)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
