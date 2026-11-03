#!/usr/bin/env python3
"""The Controls drawer with its rows built only while open (reports/rts-feel/staged/border_closed.py) against today's page,
in a real WKWebView (the app's engine): the same HUD updates to both (a real model, tests/work-human-model.json, then
selection changes: buttons blocked with a reason, active flags turning, a control dropping out, an extra command coming
in), then the drawer opened and every row read out; then closed, two more updates while shut, and opened again. PASS
when both pages show the same rows (labels, descriptions, keys, reasons, buttons, icons, hidden flags, order, counts) each
time it opens.
    python3 tools/rts_feel/chop/drawer_check.py [--page game/Interface/remastered.html] [--wkpan PATH]
Builds wkpan (tools/worldlook_wkpan.swift) into a temp folder if --wkpan isn't given. Exit 1 on any difference."""
import argparse, http.server, json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser()
ap.add_argument('--page', type=Path, default=ROOT/'game/Interface/remastered.html')
ap.add_argument('--wkpan', default='')
ap.add_argument('--broken', action='store_true', help='control: the patch without its render on open (must FAIL)')
a = ap.parse_args()

work = Path(tempfile.mkdtemp(prefix='rf-drawer-'))
try:
    site = work/'site'; site.mkdir()
    for f in a.page.parent.iterdir():   # the page's own folder (its icons and scripts), linked
        if f.name != a.page.name: (site/f.name).symlink_to(f)
    shutil.copy2(a.page, site/'today.html'); shutil.copy2(a.page, site/'patched.html')
    r = subprocess.run([sys.executable, str(ROOT/'reports/rts-feel/staged/border_closed.py'), str(site/'patched.html')], capture_output=True, text=True)
    if r.returncode: sys.exit('patch failed: ' + r.stdout + r.stderr)
    if a.broken:
        t = (site/'patched.html').read_text(encoding='utf-8'); k = ' if(borderLast)renderBorderControls(borderLast,true);'
        assert t.count(k) == 1; (site/'patched.html').write_text(t.replace(k, ''), encoding='utf-8')
    wk = a.wkpan
    if not wk:
        wk = str(work/'wkpan')
        subprocess.run(['swiftc', '-O', str(ROOT/'tools/worldlook_wkpan.swift'), '-o', wk], check=True)
    model = json.loads((ROOT/'tests/work-human-model.json').read_text())
    js = r"""
const M0 = %s;
const w = ms => new Promise(r => setTimeout(r, ms));
const C = x => JSON.parse(JSON.stringify(x));
const bc = document.getElementById('bootcover'); if (bc) bc.remove();
function dump() {
  const rows = [...document.querySelectorAll('#borderControls article.bordercontrol')].map(r => {
    const q = s => r.querySelector(s), b = q('.controlaction button, div button'), img = q('img');
    return [r.dataset.control, r.dataset.active, r.dataset.hasIcon, r.hidden, r.parentNode && r.parentNode.id || (r.parentNode && r.parentNode.className),
      q('h4') && q('h4').textContent, q('.controlmeta') && q('.controlmeta').innerHTML, q('.controlmeta') && q('.controlmeta').hidden,
      q('p:not(.reason)') && q('p:not(.reason)').textContent, q('.reason') && q('.reason').textContent, q('.reason') && q('.reason').hidden,
      b ? [b.textContent, b.disabled, b.title] : (q('.controlindicator') ? 'indicator' : null), img && [img.getAttribute('src'), img.hidden]];
  });
  const secs = [...document.querySelectorAll('#borderControls section')].map(s => [s.id || s.className, s.hidden]);
  const t = id => { const e = document.getElementById(id); return e ? [e.textContent, e.hidden] : null; };
  return { rows, secs, count: t('controlsCount'), empty: t('controlsEmpty'), vis: t('borderVisibility'), day: (() => { const e = document.getElementById('worldDayIcon'); return e ? [e.getAttribute('src'), e.hidden] : null; })() };
}
const out = [];
const send2 = m => { updateHUD(m); };
// 1. the model as it comes, twice (as the sweep does)
send2(C(M0)); await w(150); send2(C(M0)); await w(150);
// 2. selection changes while the drawer is shut
let M1 = C(M0); M1.selection = (M1.units || []).slice(0, 1).map(u => u.ref);
M1.border.controls.forEach((c, i) => { if (i %% 3 === 0) c.reason = 'Select a unit that can do this first.'; if (i %% 5 === 0) c.active = 1; });
send2(M1); await w(120);
let M2 = C(M1); M2.border.controls = M2.border.controls.filter((c, i) => i !== 4);
M2.border.controls.forEach((c, i) => { if (i %% 4 === 1) c.reason = ''; if (i %% 7 === 2) c.label = c.label + ' (2)'; });
send2(M2); await w(120);
let M3 = C(M2); M3.commands = (M3.commands || []).concat([{ id: 'extraTest', label: 'Extra', key: 'X' }]); M3.border.visible = !M3.border.visible;
send2(M3); await w(120);
openControls('all', null); await w(200); out.push(dump());
// 3. closed again, two more updates while shut, opened again
closeControls(); await w(100);
let M4 = C(M3); M4.border.controls.forEach((c, i) => { if (i %% 2 === 0) c.reason = 'Busy (test).'; c.active = i %% 3 === 0 ? 1 : 0; });
send2(M4); await w(120);
let M5 = C(M4); M5.border.controls = M5.border.controls.concat([C(M0.border.controls[4])]);
send2(M5); await w(120);
openControls('all', null); await w(200); out.push(dump());
// 4. an update while it is open: both pages render it at once
let M6 = C(M5); M6.border.controls.forEach(c => { c.reason = ''; });
send2(M6); await w(150); out.push(dump());
return JSON.stringify(out);
""" % json.dumps(model)
    (work/'probe.js').write_text(js)

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(s, *x, **k): super().__init__(*x, directory=str(site), **k)
        def log_message(s, *x): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    res = {}
    for name in ('today', 'patched'):
        p = subprocess.run([wk, f'http://127.0.0.1:{port}/{name}.html?overlay', '1440', '900', str(work/'probe.js'), str(work/f'{name}.png'), '120'],
                           capture_output=True, text=True, timeout=200)
        line = [l for l in p.stdout.splitlines() if l.startswith('PROBE ')]
        errs = [l for l in p.stdout.splitlines() if l.startswith('ERROR') or l.startswith('console.error') or 'SCRIPT-ERROR' in l]
        if not line or line[0].startswith('PROBE nil') or 'SCRIPT-ERROR' in line[0]: sys.exit(f'{name}: no result\n' + p.stdout[-2000:])
        res[name] = (json.loads(line[0][6:]), errs)
    srv.shutdown()
    A, B = res['today'][0], res['patched'][0]
    ok = True
    for i, (x, y) in enumerate(zip(A, B)):
        same = x == y
        ok &= same
        rows = len(x['rows'])
        print(f"{'  ' if same else '!!'} opening {i + 1}: {rows} rows, {sum(1 for r in x['rows'] if not r[3])} shown; "
              f"{'the same' if same else 'DIFFER'}; count {x['count']}, day icon {x['day']}")
        if not same:
            for k in x:
                if x[k] != y[k]:
                    if k == 'rows':
                        for j, (r1, r2) in enumerate(zip(x['rows'], y['rows'])):
                            if r1 != r2: print('   row', j, '\n     today  ', r1, '\n     patched', r2); break
                        if len(x['rows']) != len(y['rows']): print('   rows', len(x['rows']), 'vs', len(y['rows']))
                    else: print('  ', k, x[k], 'vs', y[k])
    for name in res:
        if res[name][1]: print(name, 'page errors:', res[name][1][:5])
    print('PASS' if ok and len(A) == len(B) == 3 else 'FAIL')
    sys.exit(0 if ok else 1)
finally:
    shutil.rmtree(work, ignore_errors=True)
