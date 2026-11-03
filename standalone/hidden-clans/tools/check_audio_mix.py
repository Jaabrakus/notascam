#!/usr/bin/env python3
"""Final mix levels through the HUD sound engine's real chain (category volumes at their defaults, the two reverb rooms,
bus compressor, make-up gain, limiter), rendered offline in headless Chrome (rmSfx.offline). Two scenes:
  scene  - 30 s of play over the forest bed: a dwarf selected and sent to chop, the Sound panel, a skirmish that brings in
           the war drums, a level-up;
  battle - 12 s of the busiest fight the throttle allows (6 hits, 5 swings and 3 parries overlapping, a siege boulder) with
           the war drums at their heaviest, over the bed.
What is off in the engine (voices, the synthesized ambience and music) is left out of the scenes.
Checks: no clipping (peak under -0.5 dBFS), the scene sits at a normal level (active-part RMS -30..-17 dBFS), the battle
stays under the limiter. Writes reports/polish-2026-10-22/audio/mix-scene.wav, mix-battle.wav and check-audio-mix.json."""
import base64, functools, http.server, json, math, shutil, tempfile, threading, wave
from pathlib import Path
import numpy as np
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
OUT = BASE/'reports/polish-2026-10-22/audio'
html = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8')
sfx = (BASE/'game/Interface/audio.js').read_text(encoding='utf-8')
recs = sorted(f.name for f in (BASE/'game/Interface/sounds').glob('*.m4a'))
VOICES = 'var VOICES_ON=false' not in sfx   # unit voices are off for now (the user, 2026-10-23): left out of the scenes
html = html.replace('<!--rm-audio-->', '<script>window.rmSoundFiles=' + json.dumps(recs) + ';' + sfx + '</script>').replace('window.location.href=', 'window.testLastURL=')
SCENES = r"""
(()=>{const S=[],B=[];
const ev=(t,name,o)=>S.push(Object.assign({t,name},o||{})),vo=(t,race,kind,o)=>S.push(Object.assign({t,voice:[race,'m',kind,0]},o||{}));
for(const [n,g] of [['bed.wind',0.6],['bed.leaves',0.6],['bed.insects',0.3]])S.push({t:0,name:n,gain:g,loop:true});
[[2.5,-0.6,0],[9.5,0.5,1],[17,-0.3,2],[25,0.6,3]].forEach(([t,pan,v])=>ev(t,'bird.song',{gain:0.45,pan,v}));
ev(1,'ui.click');vo(1.05,'Dwarf','select');ev(2.2,'cmd.work');vo(2.25,'Dwarf','work');
for(let k=0;k<6;k++)ev(3.4+k*0.95,'chop',{gain:0.7,pan:0.25,v:k%5});ev(9.2,'tree.fall',{gain:0.75,pan:0.25});
ev(11,'ui.open');ev(11.8,'ui.tab');ev(12.3,'ui.hover');ev(12.6,'ui.hover',{v:1});ev(13.2,'ui.close');
ev(14,'ui.click');vo(14.05,'Orc','select');ev(14.8,'cmd.attack');vo(14.85,'Orc','attack');
[['swing.heavy','hit.flesh'],['swing.light','parry'],['swing.heavy','hit.armor'],['swing.light','hit.flesh'],['swing.heavy','block'],['swing.light','hit.big']].forEach(([sw,h],k)=>{const t=16+k*0.62,pan=k%2?0.3:-0.2;ev(t,sw,{gain:0.8,pan,v:k%4});ev(t+0.07,h,{gain:0.8,pan,v:k%3})});
ev(19.9,'hit.flesh',{gain:0.8,pan:0.3});ev(20.05,'death.fall',{gain:0.8,pan:0.3});vo(20.1,'Human','death',{gain:0.7,pan:0.3});
const D=[['drum.taiko',1],null,['drum.frame',0.5],['drum.frame',0.35],['drum.taiko',0.8],['drum.frame',0.5],null,['drum.frame',0.6]];
for(let k=0;k<32;k++){const d=D[k%8];if(d)ev(16+k*60/96/2,d[0],{gain:d[1]*Math.min(1,(32-k)/10),v:k%3})}
ev(23.5,'ui.levelup');
const music=(arr,t0,bars)=>{const beat=60/68,bar=beat*4,root=62,prog=[[0,3,7],[-2,2,5],[0,3,7],[5,9,12]];for(let b=0;b<bars;b++){const at=t0+b*bar,ch=prog[b%4],amp=Math.min(1,(b+1)/2)*(b===bars-1?0.7:1);
 if(b%2===0)arr.push({t:at,inst:['pad',[ch.map(x=>root+x-12),bar*2+1.5]],gain:0.5*amp});[0,1,2,1,0,1,2,1].forEach((i,k)=>arr.push({t:at+k*beat/2,inst:['lute',[root+ch[i]]],gain:(k%2?0.28:0.36)*amp,pan:(k%3-1)*0.3}))}};
music(S,2,7);
// battle: what the throttle lets through at most, all at once, again and again
for(const [n,g] of [['bed.wind',0.6],['bed.leaves',0.4]])B.push({t:0,name:n,gain:g,loop:true});music(B,0,3);
for(let w=0;w<10;w++){const t0=0.5+w*1.0;for(let k=0;k<6;k++)B.push({t:t0+k*0.04,name:k%3?'hit.flesh':'hit.armor',v:k%4,gain:1,pan:(k-3)*0.15});for(let k=0;k<5;k++)B.push({t:t0+k*0.04-0.07,name:k%2?'swing.heavy':'swing.light',v:k%4,pan:(k-2)*0.2});
 for(let k=0;k<3;k++)B.push({t:t0+0.3+k*0.05,name:'parry',v:k,pan:(k-1)*0.3});B.push({t:t0+0.5,name:'block',v:w%3});if(w%3===0){B.push({t:t0+0.2,name:'death.fall',v:w%3});B.push({t:t0+0.25,voice:['Orc','m','death',0]})}B.push({t:t0+0.1,voice:['Dwarf','m','attack',w%3]})}
for(let k=0;k<64;k++){const d=D[k%8];if(d)B.push({t:0.3+k*60/96/2,name:d[0],gain:d[1],v:k%3})}
B.push({t:4,name:'siege.impact',v:0});B.push({t:7.5,name:'siege.impact',v:1});
return {S,B}})()
"""
STATS = r"""
(R)=>{const sr=R.sr,L=R.ch[0],Rr=R.ch[1],n=L.length;let pk=0,clip=0,sum=0,act=0,actN=0;const w=Math.round(0.4*sr);let acc=0,stmax=0;
 for(let i=0;i<n;i++){const a=Math.abs(L[i]),b=Math.abs(Rr[i]),m=a>b?a:b;if(m>pk)pk=m;if(m>=0.999)clip++;const e=(L[i]*L[i]+Rr[i]*Rr[i])/2;sum+=e;acc+=e;if(i>=w){const o=(L[i-w]*L[i-w]+Rr[i-w]*Rr[i-w])/2;acc-=o}if(i>=w&&(i%w===0)){const v=acc/w;if(v>stmax)stmax=v;if(v>1e-6){act+=v;actN++}}}
 const db=v=>v>0?Math.round(10*Math.log10(v)*10)/10:-120;
 const pcm=new Int16Array(n*2);for(let i=0;i<n;i++){pcm[2*i]=Math.max(-32768,Math.min(32767,Math.round(L[i]*32767)));pcm[2*i+1]=Math.max(-32768,Math.min(32767,Math.round(Rr[i]*32767)))}
 const u8=new Uint8Array(pcm.buffer);let s='';for(let i=0;i<u8.length;i+=32768)s+=String.fromCharCode.apply(null,u8.subarray(i,i+32768));
 return {sr,peak:db(pk*pk),clipped:clip,rms:db(sum/n),active:db(actN?act/actN:0),loudest400ms:db(stmax),missing:R.missing,pcm:btoa(s)}}
"""
errors = []
result = {}
with tempfile.TemporaryDirectory(prefix='audio-mix-') as tmp, sync_playwright() as pw:
    f = Path(tmp)/'remastered.html'; f.write_text(html, encoding='utf-8')
    for r in recs: shutil.copy2(BASE/'game/Interface/sounds'/r, Path(tmp)/r)
    quiet = type('Quiet', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(quiet, directory=tmp))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: errors.append(c.text[:300]) if c.type == 'error' and 'Failed to load resource' not in c.text else None)
    page.goto(f'http://127.0.0.1:{httpd.server_address[1]}/remastered.html?overlay', wait_until='domcontentloaded')
    page.mouse.click(5, 5)   # starts the audio, which loads the recordings
    page.evaluate('rmSfx.ready()')
    sc = page.evaluate(SCENES)
    if not VOICES: sc = {k: [e for e in v if 'voice' not in e] for k, v in sc.items()}
    # what is off stays out; the forest bed under both, our war drums in the fights (a skirmish, then the heaviest)
    sc = page.evaluate("""sc=>{const SND=rmSfx.synth.SND,F=rmSfx.features,on=e=>e.voice?true:e.inst?F.music:SND[e.name].cat==='amb'?F.amb:SND[e.name].cat==='mus'?F.music:true,bed={t:0,file:'amb-forest.m4a',cat:'amb',loop:true};
      return {S:[bed,...sc.S.filter(on),...rmSfx.drumScore(0,[1,1,2,2,0],15.4)],B:[bed,...sc.B.filter(on),...rmSfx.drumScore(1,[3,3,3,3,3],0)]}}""", sc)
    for name, events, secs in (('scene', sc['S'], 30), ('battle', sc['B'], 12)):
        page.evaluate('evs=>rmSfx.fetch(evs.map(e=>e.file?{file:e.file}:e.voice?{voice:e.voice}:e.inst?{inst:e.inst}:{name:e.name,v:e.v||0}))', events)
        st = page.evaluate('([s,evs])=>rmSfx.offline(s,evs).then(' + STATS + ')', [secs, events])
        pcm = base64.b64decode(st.pop('pcm'))
        with wave.open(str(OUT/f'mix-{name}.wav'), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(st['sr']); w.writeframes(pcm)
        result[name] = st
    browser.close()
    httpd.shutdown()
s, b = result['scene'], result['battle']
checks = {'no_script_errors': not errors, 'all_buffers': not s['missing'] and not b['missing'],
          'scene_no_clipping': s['peak'] < -0.5 and s['clipped'] == 0, 'scene_level_normal': -30 <= s['active'] <= -17,
          'battle_no_clipping': b['peak'] < -0.5 and b['clipped'] == 0, 'battle_louder_than_scene': b['active'] > s['active']}
out = dict(passed=all(checks.values()), checks=checks, levels=result, errors=errors[:5])
(OUT/'check-audio-mix.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
raise SystemExit(0 if out['passed'] else 1)
