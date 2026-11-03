#!/usr/bin/env python3
"""Listening previews of our war drums (Interface/audio.js, played on the drum recordings in Interface/sounds/), rendered
offline through the engine's real chain at the default volumes (rmSfx.drumScore + rmSfx.offline, headless Chrome): for each
of the three themes a battle that starts (the roll), grows from a skirmish (4 bars) to a battle (4 bars) to a great battle
(8 bars) and ends on the last hit, over the forest bed. Writes reports/polish-2026-10-22/audio/war-drums/<theme>.wav and
.m4a, and levels.json (peak, loudness); fails if a preview clips or a recording is missing.
    python3 tools/render_war_drums.py [<dir with audio.js and sounds/>]   (default game/Interface)"""
import base64, functools, http.server, json, shutil, subprocess, sys, tempfile, threading, wave
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'game/Interface'
OUT = BASE/'reports/polish-2026-10-22/audio/war-drums'
html = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8')
sfx = (SRC/'audio.js').read_text(encoding='utf-8')
files = sorted(f.name for f in (SRC/'sounds').glob('*.m4a'))
html = html.replace('<!--rm-audio-->', '<script>window.rmSoundFiles=' + json.dumps(files) + ';' + sfx + '</script>').replace('window.location.href=', 'window.testLastURL=')
LEVELS = [1] * 4 + [2] * 4 + [3] * 8 + [0]
RENDER = r"""
async ([th,levels])=>{const ev=rmSfx.drumScore(th,levels,3),end=ev.reduce((m,e)=>Math.max(m,e.t),0)+6;ev.unshift({t:0,file:'amb-forest.m4a',cat:'amb',loop:true});
 const R=await rmSfx.offline(end,ev),L=R.ch[0],Rr=R.ch[1],n=L.length;let pk=0,sum=0;for(let i=0;i<n;i++){const m=Math.max(Math.abs(L[i]),Math.abs(Rr[i]));if(m>pk)pk=m;sum+=(L[i]*L[i]+Rr[i]*Rr[i])/2}
 const pcm=new Int16Array(n*2);for(let i=0;i<n;i++){pcm[2*i]=Math.max(-32768,Math.min(32767,Math.round(L[i]*32767)));pcm[2*i+1]=Math.max(-32768,Math.min(32767,Math.round(Rr[i]*32767)))}
 const u8=new Uint8Array(pcm.buffer);let s='';for(let i=0;i<u8.length;i+=32768)s+=String.fromCharCode.apply(null,u8.subarray(i,i+32768));
 return {sr:R.sr,secs:Math.round(n/R.sr*10)/10,hits:ev.length-1,peak:Math.round(20*Math.log10(pk+1e-9)*10)/10,rms:Math.round(10*Math.log10(sum/n+1e-12)*10)/10,missing:R.missing,pcm:btoa(s)}}
"""
errors, levels = [], {}
OUT.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='wardrums-') as tmp, sync_playwright() as pw:
    (Path(tmp)/'remastered.html').write_text(html, encoding='utf-8')
    for f in files: shutil.copy2(SRC/'sounds'/f, Path(tmp)/f)
    quiet = type('Quiet', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(quiet, directory=tmp))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{httpd.server_address[1]}/remastered.html?overlay', wait_until='domcontentloaded')
    page.mouse.click(5, 5)   # starts the audio, which loads the recordings
    page.evaluate('rmSfx.ready()')
    for th, name in enumerate(['march', 'charge', 'deep']):
        r = page.evaluate(RENDER, [th, LEVELS])
        pcm = base64.b64decode(r.pop('pcm'))
        with wave.open(str(OUT/f'{name}.wav'), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(r['sr']); w.writeframes(pcm)
        subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '160000', str(OUT/f'{name}.wav'), str(OUT/f'{name}.m4a')], check=True, capture_output=True)
        levels[name] = r
    browser.close(); httpd.shutdown()
ok = not errors and all(v['peak'] < -0.5 and not v['missing'] for v in levels.values())
(OUT/'levels.json').write_text(json.dumps(dict(passed=ok, levels=levels, errors=errors[:5]), indent=1) + '\n')
print(json.dumps(dict(passed=ok, levels=levels, errors=errors[:5]), indent=1))
raise SystemExit(0 if ok else 1)
