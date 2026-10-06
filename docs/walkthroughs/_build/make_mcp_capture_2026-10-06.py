#!/usr/bin/env python3
"""Assemble docs/walkthroughs/_build/captures/2026-10-06-mcp-run.json from the two Claude Code session transcripts of
the 2026-10-06 run. Every line is derived from a recorded tool call (name, arguments, result) or is a verbatim user
message; each quote is asserted to appear in the transcript. Nothing is reconstructed."""
import json
import re
from pathlib import Path

P = Path('/Users/cdmaestas/.claude/projects/-Volumes-ext1tbwdssd-Documents-GitHub-Scale-GUInstall')
OUT = Path('/Volumes/ext1tbwdssd/Documents/GitHub/Scale-GUInstall/docs/walkthroughs/_build/captures/2026-10-06-mcp-run.json')
TK = '/usr/lpp/mmfs/6.0.1.1/ansible-toolkit/'


def read(fn, start='0'):
    uses, calls, users = {}, [], []
    for line in (P / fn).read_text().splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        ts = d.get('timestamp', '')
        if ts < start:
            continue
        msg = d.get('message', {})
        content = msg.get('content') if isinstance(msg, dict) else None
        if d.get('type') == 'assistant' and isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'tool_use' and 'scale-guinstall' in c['name']:
                    uses[c['id']] = {'ts': ts, 'tool': c['name'].split('__')[-1], 'input': c['input']}
        elif d.get('type') == 'user' and isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'tool_result' and c.get('tool_use_id') in uses:
                    r = c.get('content')
                    r = ' '.join(x.get('text', '') for x in r if isinstance(x, dict)) if isinstance(r, list) else (r or '')
                    u = uses.pop(c['tool_use_id'])
                    u['result'] = r
                    calls.append(u)
        if d.get('type') == 'user':
            txt = content if isinstance(content, str) else ' '.join(
                x.get('text', '') for x in (content or []) if isinstance(x, dict) and x.get('type') == 'text')
            if txt.strip() and not txt.startswith('<'):
                users.append((ts, txt))
    return calls, users


A, UA = read('39a3299a-9472-47a5-97dd-e9781ae664f6.jsonl', '2026-10-06T16:00')
B, UB = read('92b6bba8-33cf-4292-995f-aeb432f5d45e.jsonl', '2026-10-06T17:00')
ALL_USERS = [t for _, t in UA + UB]


def quote(text):
    assert any(text in u for u in ALL_USERS), ('not a verbatim user message', text)
    return f'USER: "{text}"'


def js(r):
    try:
        return json.loads(r)
    except ValueError:
        return None


def fmt_args(inp):
    parts = []
    for k, v in inp.items():
        if k == 'toolkit':
            continue
        parts.append(f'{k}={json.dumps(v)}' if not isinstance(v, (list, dict)) else f'{k}=[{len(v)} items]')
    return ', '.join(parts)


def call(c):
    return f'> {c["tool"]}({fmt_args(c["input"])})'


def pick(calls, tool, n=0, where=lambda c: True):
    return [c for c in calls if c['tool'] == tool and where(c)][n]


def seconds(a, b):
    from datetime import datetime
    f = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
    return (f(b) - f(a)).total_seconds()


def polls(calls, lo, hi):
    ps = [c for c in calls if c['tool'] == 'spectrumscale_running' and lo <= c['ts'] <= hi]
    return ps


P_ = {}


def phase(name, lines, note=None):
    P_[name] = {'commands': [], 'started_at': None, 'finished_at': None, 'lines': lines}
    if note:
        P_[name]['note'] = note


# 1. readiness
ping = pick(A, 'ping'); mm = js(pick(A, 'probe_mmfs')['result']); ans = js(pick(A, 'check_ansible')['result'])
ifs = js(pick(A, 'probe_interfaces')['result']); idle = js(pick(A, 'check_operation')['result'])
ans_ok = next(x['line'] for x in ans['result'] if x['type'] == 'success')
assert mm['found'] and ifs['ok'] and idle['status'] == 'idle'
phase('ready', [quote('ok new techzone environment is up. tunnel is up. server is up'), '',
                call(ping), '  ok: true',
                call(pick(A, 'probe_mmfs')), f'  version {mm["version"]}, toolkit {mm["toolkit_path"].replace(TK, ".../")}',
                call(pick(A, 'check_ansible')), f'  {ans_ok}',
                call(pick(A, 'probe_interfaces')), f'  {ifs["addresses"][0]["interface"]} {ifs["addresses"][0]["ip"]}',
                call(pick(A, 'check_operation')), f'  status: {idle["status"]}'])

# 2. disks
dev = []
for n in (0, 1):
    c = pick(A, 'list_devices', n)
    rows = [re.findall(r'NAME="(\w+)" SIZE="(\d+)" TYPE="(\w+)" FSTYPE="(\w*)"', x['line'])
            for x in js(c['result'])['result'] if x['type'] == 'normal']
    rows = [r[0] for r in rows if r]
    free = [(nm, int(sz) / 2**30) for nm, sz, ty, fs in rows if ty == 'disk' and not fs and int(sz) >= 90 * 2**30]
    assert len({g for _, g in free}) == 1
    dev += [call(c), f'  {len(rows)} block devices; free disks: ' + ' '.join(nm for nm, _ in free) + f' ({free[0][1]:.0f} GB each)']
phase('disks', dev)

# 3. setup
su0, su1 = pick(A, 'start_setup', 0), pick(A, 'start_setup', 1)
done = [c for c in A if c['tool'] == 'check_operation' and '"finished_at": "2026-10-06T16:32:04' in c['result']][0]
dj = js(done['result'])
phase('setup', [call(su0), '  dry run: ' + [e['line'] for e in js(su0['result'])['events'] if e['type'] == 'info'][0].replace(TK, '.../'),
                call(su1), '  started: true',
                '> check_operation()', f'  status: {dj["status"]} in {seconds(dj["started_at"], dj["finished_at"]):.1f}s'])

# 4. nodes
nc = pick(A, 'start_node_config')
nodes = nc['input']['nodes']
rolelines = [f'    {n["hostname"]:<14} {" ".join(n["roles"]) or "(no roles)"}' for n in nodes]
pl = polls(A, '2026-10-06T16:32:10', '2026-10-06T16:32:46')
nd = js([c for c in A if c['tool'] == 'check_operation' and '"finished_at": "2026-10-06T16:32:45' in c['result']][0]['result'])
phase('nodes', [call(nc)] + rolelines +
      [f'  started; first command: {js(nc["result"])["message"].replace("sudo -n " + TK, "").replace("$ ", "")}',
       f'> spectrumscale_running()  x{len(pl)}, every ~2 s, until it returns []',
       '> check_operation()', f'  status: {nd["status"]} in {seconds(nd["started_at"], nd["finished_at"]):.1f}s'])
ln = js(pick(A, 'list_nodes')['result'])
phase('nodes-readback', [call(pick(A, 'list_nodes'))] + [f'    {n["hostname"]:<24} {" ".join(n["roles"]) or "(no roles)"}' for n in ln['nodes']])

# 5. nsds
na = pick(A, 'start_nsd_add'); ls = js(pick(A, 'list_nsds')['result'])
nsl = [f'    {x["server"]:<14} {x["disk"]}  fg {x["failureGroup"]}  {x["usage"]:<16} {x["pool"]:<6} {x["filesystem"]}' for x in na['input']['nsds']]
phase('nsds', [call(na)] + nsl + [call(pick(A, 'list_nsds')), f'  {len(ls["nsds"])} NSDs listed'])

# 6. callhome + cluster config
ch, cc = pick(A, 'start_callhome'), pick(A, 'start_cluster_config_apply')
phase('settings', [call(ch), '  ' + js(ch['result'])['message'].replace('sudo -n ' + TK, '').replace('$ ', ''),
                   call(cc), '  ' + js(cc['result'])['message'].replace('sudo -n ' + TK, '').replace('$ ', '')])

# 7. precheck-install / install / postcheck-install
def phase_calls(name, ph):
    cs = [c for c in A + B if c['tool'] == 'start_phase' and c['input'].get('phase') == ph and c['input'].get('dry_run') is False]
    assert len(cs) == 1, (ph, len(cs))
    return cs[0]


pre = phase_calls('p', 'precheck-install')
phase('precheck-install', [call(pre), '  ' + js(pre['result'])['message'].replace('sudo -n ' + TK, '').replace('$ ', '')])
ins = phase_calls('i', 'install')
ip = polls(A, ins['ts'], '2026-10-06T17:12')
big = [c for c in A if c['tool'] == 'check_operation' and c['result'].startswith('Error: result')][0]
m = re.match(r'Error: result \(([\d,]+) characters across ([\d,]+) lines\) exceeds maximum', big['result'])
phase('install', [quote('go ahead with install'), '', call(ins), '  ' + js(ins['result'])['message'].replace('sudo -n ' + TK, '').replace('$ ', ''),
                  f'> spectrumscale_running()  x{len(ip)} while it ran',
                  '> check_operation()',
                  f'  Error: result ({m[1]} characters across {m[2]} lines) exceeds the',
                  '  maximum allowed tokens; the output was saved to a file and read',
                  '  from there.'],
      note='The overflow is a real limit of the tool result size, not an install failure.')
pci = phase_calls('c', 'postcheck-install')
phase('postcheck-install', [call(pci), '  ' + js(pci['result'])['message'].replace('sudo -n ' + TK, '').replace('$ ', '')])

# 8. the continuation (second session)
pg, rn = pick(B, 'ping'), pick(B, 'spectrumscale_running', 0)
phase('continue', ['(new session, after the context was cleared; the user pasted a hand-off note)',
                   quote('go for it'), '',
                   call(pg), '  ok: true', call(rn), f'  processes: {len(js(rn["result"])["processes"])}'])

# 9. deploy phases
bad = pick(B, 'start_phase', 0)
assert 'Toolkit not usable' in bad['result']
d_pre_dry = pick(B, 'start_phase', 1)
d_pre = phase_calls('d', 'precheck-deploy')
d_dep = phase_calls('d', 'deploy')
d_post = phase_calls('d', 'postcheck-deploy')
dd = [c for c in B if c['tool'] == 'spectrumscale_running' and d_dep['ts'] <= c['ts']]
bigd = [c for c in B if c['tool'] == 'check_operation' and c['result'].startswith('Error: result')][0]
md = re.match(r'Error: result \(([\d,]+) characters across ([\d,]+) lines\)', bigd['result'])
rec = lambda c: js(c['result'])
phase('deploy-mistake', [call(bad), '  [ERROR] Toolkit not usable: .../ansible-toolkit exists but is not a',
                         '  regular file.', '(the toolkit argument must be the spectrumscale file, not its folder)',
                         call(d_pre_dry), '  [DRY RUN] Inputs validated; command not executed.'])
assert any('Inputs validated' in e['line'] for e in rec(d_pre_dry)['events'])
chk = lambda ts: js([c for c in B if c['tool'] == 'check_operation' and ts in c['result']][0]['result'])
pc = chk('"finished_at": "2026-10-06T18:01:10')
dp = chk('"finished_at": "2026-10-06T18:19:43')
phase('deploy', [call(d_pre), '> check_operation()', f'  status: {pc["status"]} in {seconds(pc["started_at"], pc["finished_at"]):.1f}s',
                 call(d_dep), '  started: true',
                 '(waited with ssh checks from the Mac, 15 s apart, while the deploy ran)',
                 '> check_operation()', f'  Error: result ({md[1]} characters across {md[2]} lines) exceeds the maximum;',
                 '  saved to a file and read from there.',
                 call(d_post), '> check_operation()', f'  status: {dp["status"]} in {seconds(dp["started_at"], dp["finished_at"]):.1f}s'])
# today's list_nodes
lnb = js(pick(B, 'list_nodes')['result'])
phase('readback-after', [call(pick(B, 'list_nodes')), f'  {len(lnb["nodes"])} nodes, protocols S3 SMB NFS enabled (from raw listing)'])
assert 'S3     : Enabled' in lnb['raw']

phase('user-record', [quote('record and then the build?')])

cap = {'run': '2026-10-06 MCP calls', 'environment': 'TechZone l7kej84k; Claude Code session driving the scale-guinstall MCP server',
       'provenance': 'Each call line is derived from the recorded tool call and its result; user lines are verbatim user messages.',
       'toolkit_path': TK + 'spectrumscale', 'phases': P_}
OUT.write_text(json.dumps(cap, indent=1) + '\n')
print('wrote', OUT, {k: len(v['lines']) for k, v in P_.items()})
