#!/usr/bin/env python3
"""The HUD's sound engine in a real WKWebView (the engine the game's HUD runs in; headless Chrome can hide WebKit-only
problems, see rts-feel's finding of 2026-10-22), with no game and no lock needed: tools/audio_wk.swift loads
remastered.html with audio.js inlined the way the server sends it (Audio.dm), served over local HTTP with the recordings
(Interface/sounds/) beside it, in a window kept off screen. Checks: no script errors, the engine is there and wired into
the page, WebKit fetches and decodes every recording (AAC in .m4a) and the forest bed loops without a gap (its decoded
length is the loop's), the worker renders the synthesized one-shots ahead of time, audio starts without a click (the
app's web view allows it), sound comes out (output meter), and with "mute in background" on, the app going to the
background (window.dmAppActive(false), as WebKitBridge.swift says it) suspends the audio. Writes reports/polish-2026-10-22/audio/check-audio-webkit.json."""
import functools, http.server, json, re, shutil, subprocess, tempfile, threading
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE/'reports/polish-2026-10-22/audio'
html = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8')
sfx = (BASE/'game/Interface/audio.js').read_text(encoding='utf-8')
recs = sorted(f.name for f in (BASE/'game/Interface/sounds').glob('*.m4a'))
PREFS = {'master': 70, 'fx': 80, 'ui': 55, 'vo': 75, 'amb': 50, 'mus': 35}
EXPR = "JSON.stringify({t:typeof rmSfx,wired:rmSfx&&rmSfx._E.wired,stats:rmSfx&&rmSfx.stats(),bedSecs:rmSfx&&(rmSfx._E.buffers.get('amb-forest.m4a')||{}).duration,hidden:rmSfx&&rmSfx._E.hidden,master:rmSfx&&rmSfx._E.master?rmSfx._E.master.gain.value:null,vis:document.visibilityState})"


def run(tool, page, secs, bg, extra=()):
    st = json.dumps(dict(PREFS, bg=bg), separators=(',', ':'))
    # caffeinate: a sleeping display stalls WebKit (memory note "display off stalls client")
    out = subprocess.run(['caffeinate', '-d', '-i', '-u', str(tool), str(page), EXPR, str(secs), '--storage', 'rmAudio=' + st, *extra], capture_output=True, text=True, timeout=secs + 60).stdout
    errors = [l for l in out.splitlines() if l.startswith(('ERROR', 'console.error'))]
    m = re.search(r'^RESULT (.*?) ?$', out, re.M)
    try: res = json.loads(m.group(1)) if m else None
    except Exception: res = None
    return res, errors


with tempfile.TemporaryDirectory(prefix='audio-wk-') as tmp:
    tool = Path(tmp)/'audio_wk'
    subprocess.run(['swiftc', '-O', str(BASE/'tools/audio_wk.swift'), '-o', str(tool)], check=True, capture_output=True)
    site = Path(tmp)/'site'; site.mkdir()
    (site/'remastered.html').write_text(html.replace('<!--rm-audio-->', '<script>window.rmSoundFiles=' + json.dumps(recs) + ';' + sfx + '</script>'), encoding='utf-8')
    for r in recs: shutil.copy2(BASE/'game/Interface/sounds'/r, site/r)
    quiet = type('Quiet', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(quiet, directory=str(site)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    page = f'http://127.0.0.1:{httpd.server_address[1]}/remastered.html'
    # wait for the page rather than a fixed time: the machine may be busy (other sessions' servers and clients)
    playing, err1 = run(tool, page, 60, 0, ('--until', "window.rmSfx&&rmSfx.stats().pending===0&&rmSfx.stats().buffers>150&&rmSfx.stats().rec.files>0&&rmSfx.stats().rec.loaded+rmSfx.stats().rec.failed>=rmSfx.stats().rec.files&&rmSfx.stats().bed&&rmSfx.stats().state==='running'&&rmSfx.stats().peak>0.001"))
    # muted in the background, told the way the app tells it (WebKitBridge.swift: another app in front), so the result
    # doesn't hang on how this machine classes an off-screen window
    muted, err2 = run(tool, page, 40, 1, ('--at-start', "setTimeout(()=>{try{window.dmAppActive(false)}catch(e){}},4000)", '--until', "window.rmSfx&&rmSfx._E.ctx&&rmSfx._E.hidden&&(rmSfx._E.ctx.state==='suspended'||rmSfx._E.master.gain.value<0.01)"))
    httpd.shutdown()
s = (playing or {}).get('stats') or {}
checks = {
    'no_script_errors': not err1 and not err2,
    'engine_in_page': (playing or {}).get('t') == 'function',
    'wired': sorted((playing or {}).get('wired') or []) == ['logPush', 'send', 'update3D', 'updateHUD'],
    'recordings_decoded': (s.get('rec') or {}).get('files') == len(recs) > 0 and (s.get('rec') or {}).get('loaded') == len(recs),
    'forest_bed_loops_gapless': s.get('bed') is True and abs(((playing or {}).get('bedSecs') or 0) - 10 * 12 * 60 / 110) < 0.005,
    'worker_rendered_all': s.get('worker') == 'yes' and s.get('pending') == 0 and (s.get('buffers') or 0) >= 150,
    'starts_without_click': s.get('state') == 'running',
    'sound_comes_out': (s.get('peak') or 0) > 0.001 and s.get('bed') is True,
    # no input has reached this page, so "background" mutes by the master gain (a suspended context could not come back
    # without a click); with input it also suspends (the headless and real-client checks cover that)
    'muted_in_background': (muted or {}).get('hidden') is True and (((muted or {}).get('stats') or {}).get('state') == 'suspended' or ((muted or {}).get('master') is not None and (muted or {}).get('master') < 0.01)),
}
result = dict(passed=all(checks.values()), checks=checks, playing=playing, muted=muted, errors=(err1 + err2)[:8])
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'check-audio-webkit.json').write_text(json.dumps(result, indent=1) + '\n')
print(json.dumps(result, indent=1)[:2500])
raise SystemExit(0 if result['passed'] else 1)
