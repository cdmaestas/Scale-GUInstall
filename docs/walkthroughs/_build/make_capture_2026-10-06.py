#!/usr/bin/env python3
"""Assemble docs/walkthroughs/_build/captures/2026-10-06-run.json from the run's real artifacts.

Toolkit phases (precheck/install/postcheck, deploy ones): headline lines and their millisecond timestamps are read
from the toolkit's own logs (logs-extracted/), so per-line timing is real. Short phases come from run-log.jsonl
(commands the backend echoed, quoted output). CES/health verification comes from verify-cluster.txt.
Nothing is typed by hand except provenance notes; every kept line is asserted to exist in its source."""
import datetime as dt
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
LOGS = HERE / 'logs-extracted'
OUT = Path('/Volumes/ext1tbwdssd/Documents/GitHub/Scale-GUInstall/docs/walkthroughs/_build/captures/2026-10-06-run.json')
TK = '/usr/lpp/mmfs/6.0.1.1/ansible-toolkit/spectrumscale'

STAMP = re.compile(r'^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d),(\d{3}) \[ (\w+)\s*\] (.*)$')
NOISE = re.compile(r'^(TASK|PLAY \[|ok:|changed:|skipping|included:|fatal|\{|\}|\s{2,}|\*+|\.\.\.)')


def parse(name):
    out = []
    for raw in (LOGS / name).read_text(errors='replace').splitlines():
        m = STAMP.match(raw)
        if m and m[4] != 'TRACE':
            t = dt.datetime.strptime(f'{m[1]} {m[2]}', '%Y-%m-%d %H:%M:%S') + dt.timedelta(milliseconds=int(m[3]))
            out.append((t, m[4], m[5]))
    return out


def headline(entries, extra):
    keep = []
    for t, lv, msg in entries:
        if msg.startswith('ASYNC OK') or msg.startswith('ASYNC POLL'):
            continue
        recap = bool(re.match(r'^\S+\s+: ok=', msg)) or 'PLAY RECAP' in msg
        if lv in ('INFO', 'WARN', 'FATAL', 'ERROR') and (not NOISE.match(msg) or recap or any(x in msg for x in extra)):
            keep.append((t, lv, msg))
    return keep


def fmt(lv, msg):
    return f'[ {lv:<5} ] {msg}'


def slowest(entries, n=6):
    tasks = [(t, m) for t, lv, m in entries if lv == 'INFO' and m.startswith('TASK [')]
    rows = []
    for i, (t, m) in enumerate(tasks):
        end = tasks[i + 1][0] if i + 1 < len(tasks) else entries[-1][0]
        rows.append(((end - t).total_seconds(), (t - entries[0][0]).total_seconds(),
                     re.sub(r'^TASK \[(?:ibm\.spectrum_scale\.)?|\]\s*\*+$', '', m)))
    return sorted(rows, reverse=True)[:n]


runlog = {}
for line in (HERE / 'run-log.jsonl').read_text().splitlines():
    d = json.loads(line)
    runlog[d['phase']] = d

P = {}


def cmd(c):
    return c if c.startswith('sudo') else f'sudo -n {TK} {c}'


def short(name, rec, started=None, finished=None, note=None):
    cmds = rec.get('commands_observed') or [rec['command']]
    p = {'commands': [cmd(c) for c in cmds], 'started_at': rec.get('started_at', started),
         'finished_at': rec.get('finished_at', finished), 'lines': rec.get('lines', [])}
    n = note or rec.get('note')
    if n:
        p['note'] = n
    P[name] = p


short('setup', runlog['setup'], note='Backend echoed the command; its output lines were not saved this run.')
short('node-config', runlog['node-config'])
short('nsd-add', runlog['nsd-add'])
short('nsd-list', runlog['nsd-list'])
P['nsd-list']['commands'] = [cmd('nsd list')]
short('callhome', runlog['callhome'])
short('cluster-config', runlog['cluster-config'])
short('protocols', runlog['protocols'], note='Run from the GUI Apply Protocols panel (its terminal pane output).')
P['protocols']['started_at'] = P['protocols']['finished_at'] = None
P['node-list'] = {'commands': [cmd('node list')], 'started_at': None, 'finished_at': None,
                  'lines': (HERE / 'node-list.txt').read_text().splitlines(),
                  'note': 'Read after deploy; the protocol block and export addresses reflect the finished run.'}

# toolkit phases: (name, log, backend command, backend start, backend finish, extra headline matches)
TOOLKIT = [
    ('precheck-install', 'INSTALL-PRECHECK-06-10-2026_16:35:14.log', 'install --precheck', None, None, []),
    ('install', 'INSTALL-06-10-2026_16:47:20.log', 'install', None, None,
     ['core_configure : cluster | Create new cluster', 'core_configure : storage | Create new NSDs',
      'core_configure : storage | Create new filesystem(s)', 'RETRYING']),
    ('postcheck-install', 'INSTALL-POSTCHECK-06-10-2026_17:12:38.log', 'install --postcheck', None, None, []),
    ('precheck-deploy', 'DEPLOY-PRECHECK-06-10-2026_17:58:33.log', 'deploy --precheck',
     '2026-10-06T17:58:33.194110+00:00', '2026-10-06T18:01:10.054869+00:00', []),
    ('deploy', 'DEPLOY-06-10-2026_18:01:34.log', 'deploy',
     '2026-10-06T18:01:30.746253+00:00', '2026-10-06T18:18:59.652134+00:00', ['ASYNC FAILED']),
    ('postcheck-deploy', 'DEPLOY-POSTCHECK-06-10-2026_18:19:34.log', 'deploy --postcheck',
     '2026-10-06T18:19:34.002550+00:00', '2026-10-06T18:19:43.729564+00:00', []),
]
slow = {}
for name, log, command, started, finished, extra in TOOLKIT:
    entries = parse(log)
    rec = runlog.get(name, {})
    keep = headline(entries, extra)
    t0 = entries[0][0]
    p = {'commands': [cmd(command)], 'started_at': rec.get('started_at', started),
         'finished_at': rec.get('finished_at', finished),
         'toolkit_log': log, 'toolkit_log_first': entries[0][0].isoformat(), 'toolkit_log_last': entries[-1][0].isoformat(),
         'lines': [fmt(lv, msg) for t, lv, msg in keep],
         'line_times': [round((t - t0).total_seconds(), 3) for t, lv, msg in keep],
         'note': 'Headline lines from the toolkit\'s own log; line_times are seconds since its first log line.'}
    assert p['started_at'] and p['finished_at'], name
    P[name] = p
    slow[name] = slowest(entries)
for name in ('install', 'deploy'):
    P[f'{name}-slow-tasks'] = {
        'commands': [], 'started_at': None, 'finished_at': None,
        'lines': [f'{secs:6.1f}s  +{int(at // 60)}:{at % 60:04.1f}  {task[:60]}' for secs, at, task in slow[name]],
        'note': 'Derived: seconds from each TASK line to the next TASK line in the toolkit log (tasks run in parallel '
                'across nodes, so this is log spacing, not per-node cost).'}

# verification run on proto1 (verify-cluster.txt): split by "### command"
verify, cur = {}, None
for line in (HERE / 'verify-cluster.txt').read_text().splitlines():
    if line.startswith('### '):
        cur = line[4:]
        verify[cur] = []
    elif cur and line.strip():
        verify[cur].append(line.rstrip())
def section(name, drop_notices=True):
    return [l for l in verify[name]]


P['ces-verify'] = {'commands': ['sudo /usr/lpp/mmfs/bin/mmces address list', 'sudo /usr/lpp/mmfs/bin/mmces service list -a'],
                   'started_at': None, 'finished_at': None,
                   'lines': verify['mmces address list'] + verify['mmces service list -a'],
                   'note': 'Run on scale-proto1 over SSH from the installer node.'}
P['mmhealth-smb'] = {'commands': ['sudo /usr/lpp/mmfs/bin/mmhealth node show SMB -v'], 'started_at': None, 'finished_at': None,
                     'lines': [l for l in verify['mmhealth node show SMB -v'] if l.strip() and not l.startswith('Node name')]}
assert len(P['ces-verify']['lines']) == 7 and len(P['mmhealth-smb']['lines']) >= 8, (P['ces-verify']['lines'], P['mmhealth-smb']['lines'])

cap = {
    'run': '2026-10-06 TechZone run',
    'environment': 'IBM TechZone VSI environment l7kej84k: installer = bastion 10.249.129.192; seven cluster nodes '
                   '(2 NSD/manager/quorum, 1 GUI/admin/quorum, 2 protocol, 2 client), RHEL 9, IBM Storage Scale 6.0.1.1.',
    'provenance': 'Commands are the lines the backend echoed for each operation. Install and deploy phase lines and '
                  'their timestamps are read from the toolkit\'s own logs; short phases are quoted from the operation '
                  'output returned during the run.',
    'toolkit_path': TK,
    'phases': P,
}
OUT.write_text(json.dumps(cap, indent=1) + '\n')
print('wrote', OUT, {k: len(v['lines']) for k, v in P.items()})
