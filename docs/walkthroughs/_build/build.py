#!/usr/bin/env python3
"""Build the curated walkthrough outputs from JSON scenes; originals are never overwritten.

Python 3.10+; GIF export requires agg 1.9.0 (tested). --check uses Pillow.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent           # docs/walkthroughs/_build (sources, timings)
OUT = ROOT.parent                                 # docs/walkthroughs (gui/, mcp/, cli/)
ARCHIVE = ROOT.parents[1] / 'archive' / 'recordings'  # original casts cited by each scene's source range
# source slug -> output stem under docs/walkthroughs/ (adds .cast, .html, .gif, .narration.md)
SLUGS = {
    'mcp-install-and-debug': 'mcp/install-and-debug',
    'terminal-overview': 'cli/overview',
    'mcp-extra-examples': 'mcp/extra-examples',
    'ces-nfs-case-study': 'mcp/ces-nfs-case-study',
}
COLS, ROWS = 88, 24


def out(slug, suffix):
    return OUT / f'{SLUGS[slug]}{suffix}'


def load(slug):
    data = json.loads((ROOT / 'sources' / f'{slug}.json').read_text())
    elapsed = 0
    for scene in data['scenes']:
        assert '\x1b' not in json.dumps(scene), 'Source must not contain terminal escapes'
        words = len(scene['narration'].split())
        scene['duration'] = round(words * 60 / data['words_per_minute'] + data['buffer_seconds'], 2)
        scene['start'] = round(elapsed, 2)
        elapsed += scene['duration']
        ref = scene['source']
        source = ARCHIVE / ref['file']
        assert source.exists() and ref['start'] < ref['end']
        events = [json.loads(line) for line in source.read_text().splitlines()[1:]]
        assert ref['end'] <= events[-1][0] + .001
    data['duration'] = round(elapsed, 2)
    return data


def stamp(seconds):
    return f'{int(seconds // 60)}:{seconds % 60:05.2f}'


def screen_lines(data, scene, index):
    # Hard-wrap each independent source line; never retain another scene's scrollback.
    lines = [f'{index + 1:02d}/{len(data["scenes"]):02d}  {scene["title"]}', '']
    for line in scene['lines']:
        lines.extend(textwrap.wrap(line, width=COLS - 4, break_long_words=False,
                                   break_on_hyphens=False) or [''])
    lines += ['', 'EDITED REENACTMENT | Silent preview; narration supplied separately.']
    assert all(len(line) <= COLS - 2 for line in lines), scene['title']
    assert len(lines) <= ROWS - 1, (scene['title'], len(lines))
    return lines


def terminal_screen(lines):
    rendered = ['\x1b[1;38;2;139;233;253m' + lines[0] + '\x1b[0m']
    rendered.extend('\x1b[38;2;243;244;246m' + line + '\x1b[0m' for line in lines[1:])
    return '\x1b[2J\x1b[H\x1b[?25l' + '\r\n'.join(rendered)


def player(data):
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    template = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
*{box-sizing:border-box}body{margin:0;background:#111827;color:#f3f4f6;font:18px/1.5 system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:24px}h1{font-size:26px;margin:0 0 12px}h2{color:#8be9fd;font-size:24px}
#screen{background:#1f2937;padding:24px;border:1px solid #64748b;border-radius:10px;min-height:330px}
pre{font:clamp(13px,1.65vw,20px)/1.55 ui-monospace,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere;color:#f3f4f6}
#narration{max-width:1000px;font-size:19px;min-height:100px}button,select{font:inherit;padding:8px 14px;background:#243b53;color:white;border:1px solid #94a3b8;border-radius:5px}button:disabled{opacity:.4}nav{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:16px 0}progress{width:100%;height:12px}#position,.note,summary{color:#cbd5e1;font-size:15px}a{color:#8be9fd}#chapters{max-width:100%}
</style></head><body><main><h1>__TITLE__</h1>
<p class="note">Edited reenactment. Silent playback; read the synchronized narration aloud. Starts paused.</p>
<nav><button id="prev">Previous</button><button id="play">Play</button><button id="next">Next</button><button id="restart">Restart</button><label>Chapter <select id="chapters"></select></label><label>Pace <select id="speed"><option value="0.85">Slower</option><option value="1" selected>Normal</option><option value="1.15">Faster</option></select></label></nav>
<div id="position"></div><progress id="progress" max="1" value="0"></progress>
<section id="screen"><h2 id="heading"></h2><pre id="body"></pre></section>
<details open><summary>Narration</summary><p id="narration"></p></details>
<p class="note">Space: play/pause · Arrow keys: chapters · Home: restart. Playback stops at the end.</p>
<details><summary>Source and provenance</summary><p id="source" class="note"></p></details>
</main><script>
const data=__DATA__;
let index=0,elapsed=0,playing=false,last=null;
const el=id=>document.getElementById(id);
data.scenes.forEach((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=s.title;el('chapters').appendChild(o)});
function render(){const s=data.scenes[index];el('heading').textContent=s.title;el('body').textContent=s.lines.join('\n');el('narration').textContent=s.narration;el('source').textContent=`Source: ${s.source.file}, ${s.source.start}–${s.source.end} seconds. Edited summary; not verbatim command footage.`;el('chapters').value=index;el('prev').disabled=index===0;el('next').disabled=index===data.scenes.length-1;update();}
function update(){const s=data.scenes[index];el('progress').value=Math.min(1,elapsed/s.duration);el('position').textContent=`Chapter ${index+1} of ${data.scenes.length} · ${s.duration.toFixed(2)} seconds · Total ${data.duration.toFixed(2)} seconds`;el('play').textContent=playing?'Pause':'Play';}
function go(i){index=Math.max(0,Math.min(data.scenes.length-1,i));elapsed=0;last=null;render()}
function toggle(){if(!playing&&index===data.scenes.length-1&&elapsed>=data.scenes[index].duration)go(0);playing=!playing;last=null;update()}
el('prev').onclick=()=>go(index-1);el('next').onclick=()=>go(index+1);el('restart').onclick=()=>{playing=false;go(0)};el('play').onclick=toggle;el('chapters').onchange=e=>go(Number(e.target.value));
document.addEventListener('keydown',e=>{if(['SELECT','BUTTON'].includes(document.activeElement.tagName))return;if(e.key===' '){e.preventDefault();toggle()}if(e.key==='ArrowRight')go(index+1);if(e.key==='ArrowLeft')go(index-1);if(e.key==='Home'){playing=false;go(0)}});
function tick(t){if(last!==null&&playing){elapsed+=(t-last)/1000*Number(el('speed').value);if(elapsed>=data.scenes[index].duration){if(index<data.scenes.length-1){go(index+1)}else{elapsed=data.scenes[index].duration;playing=false}}update()}last=t;requestAnimationFrame(tick)}
render();requestAnimationFrame(tick);
</script></body></html>'''
    return template.replace('__TITLE__', html.escape(data['title'])).replace('__DATA__', payload)


def build(slug, export_gif):
    data = load(slug)
    header = dict(version=2, width=COLS, height=ROWS, title=data['title'],
                  duration=data['duration'], env={'TERM': 'xterm-256color'})
    events = [json.dumps(header)]
    narration = [f'# {data["title"]} — narration', '', data['description'], '',
                 'Generated from the matching JSON in `docs/walkthroughs/_build/sources/`. Edit that source, then rebuild.', '',
                 f'Pace: {data["words_per_minute"]} words/minute + {data["buffer_seconds"]} seconds per chapter. Total: {stamp(data["duration"])}.', '']
    for i, scene in enumerate(data['scenes']):
        events.append(json.dumps([scene['start'], 'o', terminal_screen(screen_lines(data, scene, i))]))
        narration += [f'## {stamp(scene["start"])} — {scene["title"]}', '', scene['narration'], '',
                      f'Source: `{scene["source"]["file"]}` {scene["source"]["start"]}–{scene["source"]["end"]} seconds. Hold {scene["duration"]:.2f}s.', '']
    (out(slug, '.cast')).write_text('\n'.join(events) + '\n')
    (out(slug, '.html')).write_text(player(data))
    (out(slug, '.narration.md')).write_text('\n'.join(narration))
    if export_gif:
        subprocess.run(['agg', '--font-family', 'Menlo', '--font-size', '20', '--theme', 'github-dark',
                        '--idle-time-limit', '120', '--last-frame-duration', str(data['scenes'][-1]['duration']),
                        '--no-loop', str(out(slug, '.cast')), str(out(slug, '.gif'))], check=True)
    return data


def check(slug, gif):
    data = load(slug)
    events = [json.loads(s) for s in (out(slug, '.cast')).read_text().splitlines()]
    assert len(events) == len(data['scenes']) + 1
    assert events[0]['duration'] == data['duration']
    page = (out(slug, '.html')).read_text()
    embedded = json.loads(re.search(r'const data=(.*);\nlet index=', page).group(1))
    assert embedded == data
    narration = (out(slug, '.narration.md')).read_text()
    for i, scene in enumerate(data['scenes']):
        assert events[i + 1] == [scene['start'], 'o', terminal_screen(screen_lines(data, scene, i))]
        assert scene['narration'] in narration
    result = {'slug': slug, 'chapters': len(data['scenes']), 'seconds': data['duration']}
    if gif:
        from PIL import Image
        im = Image.open(out(slug, '.gif'))
        assert im.info.get('loop', 1) != 0, 'Preview must not loop forever'
        delays = []
        for i in range(im.n_frames):
            im.seek(i)
            delays.append(im.info.get('duration', 0) / 1000)
        assert abs(sum(delays) - data['duration']) < .25, (slug, sum(delays), data['duration'])
        assert im.n_frames == len(data['scenes']), (slug, im.n_frames)
        # One scene per frame: verify each chapter's hold, not only total time.
        assert all(abs(d - s['duration']) < .02 for d, s in zip(delays, data['scenes'], strict=True))
        result.update(gif_seconds=round(sum(delays), 2), frames=im.n_frames,
                      dimensions=list(im.size), bytes=(out(slug, '.gif')).stat().st_size)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gif', action='store_true', help='Render GIFs with agg')
    parser.add_argument('--check', action='store_true', help='Check generated outputs (Pillow for GIFs)')
    parser.add_argument('--only', choices=SLUGS)
    args = parser.parse_args()
    if args.gif and not args.check and not shutil.which('agg'):
        parser.error('agg is required for --gif')
    results = []
    for slug in ([args.only] if args.only else SLUGS):
        if not args.check:
            build(slug, args.gif)
        result = check(slug, args.gif)
        results.append(result)
        print(json.dumps(result))
    if not args.check:
        manifest = {slug: load(slug) for slug in SLUGS}
        (ROOT / 'timings.json').write_text(json.dumps({s: {'seconds': d['duration'], 'chapters': [
            {'title': c['title'], 'start': c['start'], 'duration': c['duration']} for c in d['scenes']
        ]} for s, d in manifest.items()}, indent=2) + '\n')


if __name__ == '__main__':
    main()
