#!/usr/bin/env python3
"""The HUD's sound engine (Interface/audio.js) in headless Chrome, inlined the way the server sends the page (Audio.dm
RemasterHUDPage: the recordings' names in rmSoundFiles, then audio.js, for the <!--rm-audio--> marker), with ?overlay,
served over local HTTP with the recordings (Interface/sounds/) beside it. Checks: no script errors; the Sound section in
Settings (Master, Effects, Interface, Ambience, War drums and the background switch); a real click starts the audio and
the recordings load; interface sounds from hover and click; order acknowledgements (a voice too while voices are on);
combat from the hits feed (swing, hit, parry, kill, arrows) brings in the war drums; chopping and a tree falling from
block-break updates; 50 hits at once are throttled; level-up from XP drops; the forest bed plays and the synthesized
ambience and music don't; the settings save to the server (rm=audioprefs) and come back from the model."""
import functools, http.server, json, shutil, threading
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
html = (BASE/'game/Interface/remastered.html').read_text(encoding='utf-8')
sfx = (BASE/'game/Interface/audio.js').read_text(encoding='utf-8')
recs = sorted(f.name for f in (BASE/'game/Interface/sounds').glob('*.m4a'))
assert '<!--rm-audio-->' in html, 'marker missing from remastered.html'
assert '</script' not in sfx, 'audio.js must not contain a closing script tag'
VOICES = 'var VOICES_ON=false' not in sfx   # unit voices are off for now (the user, 2026-10-23)
html = html.replace('<!--rm-audio-->', '<script>window.rmSoundFiles=' + json.dumps(recs) + ';' + sfx + '</script>').replace('window.location.href=', 'window.testLastURL=')
m = json.loads((BASE/'tests/idle-model-available.json').read_text())
for x in m['units']: x['selected'] = False
u = m['units'][0]; u['selected'] = True; u['race'] = 'Dwarf'
m['hits'] = []; m['xpDrops'] = []
for k in ('hudPrefs', 'audio'): m.pop(k, None)   # models recorded from a live server carry these; the restore tests add them later
errors, warns = [], []
out = BASE/'reports/polish-2026-10-22/audio'
with tempfile.TemporaryDirectory(prefix='audio-hud-') as tmp, sync_playwright() as pw:
    page_file = Path(tmp)/'remastered.html'
    page_file.write_text(html, encoding='utf-8')
    for f in recs: shutil.copy2(BASE/'game/Interface/sounds'/f, Path(tmp)/f)
    quiet = type('Quiet', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None})
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(quiet, directory=tmp))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    browser = pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=720))
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda c: (errors if c.type == 'error' else warns).append(c.text[:300]) if c.type in ('error', 'warning') and 'Failed to load resource' not in c.text else None)
    page.goto(f'http://127.0.0.1:{httpd.server_address[1]}/remastered.html?overlay', wait_until='domcontentloaded')
    page.evaluate('m=>updateHUD(m)', m)
    page.evaluate("()=>{const c=document.getElementById('bootcover');if(c)c.remove()}")   # the loading cover waits for 3D land
    page.wait_for_timeout(200)
    seen = {}
    seen['api'] = page.evaluate("typeof rmSfx==='function'&&typeof rmSfx.order==='function'&&typeof rmSfx.at==='function'")
    seen['wrapped'] = page.evaluate("['updateHUD','update3D','send','logPush'].every(n=>(rmSfx._E.wired||[]).includes(n))")   # others may wrap after (rts-feel), calling through
    seen['before_click'] = page.evaluate('rmSfx.stats().state')
    # the Sound section in Settings
    page.evaluate("document.getElementById('settings').hidden=false")
    seen['sliders'] = page.evaluate("[...document.querySelectorAll('#rmSound input[type=range]')].map(i=>i.dataset.k+'='+i.value+'/'+i.parentNode.querySelector('output').textContent)")
    seen['bg_switch'] = page.evaluate("!!document.querySelector('#rmSound input[type=checkbox][data-k=bg]')")
    # a real click starts the audio (the page's autoplay rule)
    page.mouse.click(5, 5)
    page.wait_for_timeout(300)
    seen['after_click'] = page.evaluate('rmSfx.stats().state')
    p0 = page.evaluate('rmSfx.stats().played')
    # interface: hover and click a real button
    box = page.locator('#setClose').bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    page.wait_for_timeout(80)
    page.evaluate("document.getElementById('settings').hidden=false")
    page.mouse.down(); page.mouse.up()
    page.wait_for_timeout(150)
    seen['ui_played'] = page.evaluate('rmSfx.stats().played') - p0
    # the worker renders every one-shot ahead of time
    seen['ready'] = page.evaluate('rmSfx.ready()')
    seen['worker'] = page.evaluate('rmSfx.stats().worker')
    seen['rec'] = page.evaluate('rmSfx.stats().rec')
    # every named sound that is on plays through the engine; the synthesized ambience and music are off
    names = page.evaluate("Object.keys(rmSfx.synth.SND).filter(n=>!rmSfx.synth.SND[n].loop)")
    off = page.evaluate("Object.keys(rmSfx.synth.SND).filter(n=>{const d=rmSfx.synth.SND[n];return !d.rec&&(d.cat==='amb'&&!rmSfx.features.amb||d.cat==='mus'&&!rmSfx.features.music)})")
    res = page.evaluate("ns=>{const r={};for(const n of ns){try{rmSfx.hush();rmSfx._E.live=[];rmSfx._E.state.delete(n);r[n]=!!rmSfx(n,{gain:0.3})}catch(e){r[n]=e.message}}rmSfx.hush();return r}", names)
    seen['named_sounds'] = len(names)
    seen['named_failed'] = [n for n in names if n not in off and res[n] is not True]
    seen['off_but_playing'] = [n for n in names if n in off and res[n] is not False]
    page.wait_for_timeout(400)
    # orders: acknowledgement cue and a voice (dwarf)
    v0 = page.evaluate("rmSfx._E.played")
    page.evaluate("rmSfx._E.lastAck=0;rmSfx.order('attack',{})")
    page.wait_for_timeout(50)
    seen['order_played'] = page.evaluate("rmSfx._E.played") - v0
    seen['voice_live'] = page.evaluate("rmSfx._E.live.filter(l=>l.cat==='vo').length")
    # a click in 3D on a tree tile predicts "chop" (send wrapper)
    seen['predict_move'] = page.evaluate("rmSfx._E.lastAck=0;send('click3d','10|10||0|0');window.testLastURL.includes('click3d')")
    # combat from the hits feed: the first model's hits are old news, the next are played
    m2 = dict(m); m2['hits'] = [{'id': 'h0', 'x': 1, 'y': 1, 'n': 3, 'k': '', 'mine': 0, 'ax': 2, 'ay': 1, 'w': 'sword'}]
    page.evaluate('m=>updateHUD(m)', m2)
    c0 = page.evaluate('rmSfx._E.played')
    m3 = dict(m); m3['hits'] = [
        {'id': 'h1', 'x': 1, 'y': 1, 'n': 7, 'k': '', 'mine': 0, 'ax': 2, 'ay': 1, 'w': 'axe'},
        {'id': 'h2', 'x': 3, 'y': 1, 'n': 0, 'k': 'parry', 'mine': 0, 'ax': 4, 'ay': 1, 'w': 'sword'},
        {'id': 'h3', 'x': 5, 'y': 2, 'n': 12, 'k': 'kill', 'mine': 1, 'ax': 6, 'ay': 2, 'w': 'mace'},
        {'id': 'h4', 'x': 9, 'y': 2, 'n': 4, 'k': '', 'mine': 0, 'ax': 2, 'ay': 2, 'w': 'bow', 'p': 'arrow'},
        {'id': 'h5', 'x': 9, 'y': 3, 'n': 0, 'k': 'burn', 'mine': 0, 'ax': 8, 'ay': 3, 'w': ''}]
    page.evaluate('m=>updateHUD(m)', m3)
    page.wait_for_timeout(100)
    seen['combat_played'] = page.evaluate('rmSfx._E.played') - c0
    page.wait_for_timeout(500)
    seen['drums'] = page.evaluate('rmSfx.stats().drums')
    # world-look's landing hooks and rts-feel's moment names
    page.evaluate("for(const n of ['parry','hit.flesh','hit.armor','death.fall','ui.pick','ui.error','ui.groupset','built','built.wood'])rmSfx._E.state.delete(n)")
    page.evaluate("rmSfx.at('impact',3,3,{k:'parry',w:'sword',spark:true});rmSfx.at('impact',4,3,{k:'',w:'axe'});rmSfx.at('fall',4,3);rmSfx('select');rmSfx('group-set');rmSfx('deny');rmSfx.at('built',2,2,{kind:'wall'});rmSfx.at('built',2,4,{kind:'floor'})")
    page.wait_for_timeout(200)
    seen['hook_names'] = page.evaluate("['parry','death.fall','ui.pick','ui.groupset','ui.error','built','built.wood'].filter(n=>rmSfx._E.state.get(n)&&rmSfx._E.state.get(n).times&&rmSfx._E.state.get(n).times.length)")
    seen['impact_body'] = page.evaluate("['hit.flesh','hit.armor'].some(n=>rmSfx._E.state.get(n)&&rmSfx._E.state.get(n).times&&rmSfx._E.state.get(n).times.length)")
    # throttle: 50 swings and hits at once on the same spot
    t0 = page.evaluate('[rmSfx._E.played,rmSfx._E.skipped]')
    page.evaluate("for(const n of ['hit.flesh','swing.light'])rmSfx._E.state.delete(n);for(let i=0;i<50;i++){rmSfx('hit.flesh',{x:1,y:1});rmSfx('swing.light',{x:1,y:1})}")
    t1 = page.evaluate('[rmSfx._E.played,rmSfx._E.skipped]')
    # a sound with a long gap (the warning bell: 3 s) is held back across the whole gap, not just 2 s
    seen['long_gap'] = page.evaluate("(()=>{rmSfx._E.state.delete('ui.warn');return !!rmSfx('ui.warn')})()")
    page.wait_for_timeout(2400)
    seen['long_gap'] = [seen['long_gap'], page.evaluate("!!rmSfx('ui.warn')")]
    seen['throttle_played'] = t1[0] - t0[0]; seen['throttle_skipped'] = t1[1] - t0[1]
    # work: block-break updates (update3D) - blows on a tree, then it falls
    page.evaluate("""()=>{try{V3.terrain=V3.terrain||{x0:0,y0:0,w:20,h:20,tiles:new Array(400).fill(1),kinds:[{kind:'tree'}]}}catch(e){}
      window.v3kindAt=window.v3kindAt||function(){return {kind:'tree'}}}""")
    w0 = page.evaluate('rmSfx._E.played')
    for blows, broken in [(1, 0), (2, 0), (3, 0), (3, 1)]:
        page.evaluate('d=>update3D(JSON.stringify(d))', {'z': 1, 'cx': 5, 'cy': 5, 'night': False, 'work': [[5, 6, 10, blows, 0, 1, broken, 0]], 'things': []})
        page.wait_for_timeout(60)
    seen['work_played'] = page.evaluate('rmSfx._E.played') - w0
    seen['work_names'] = page.evaluate("[...rmSfx._E.state.entries()].filter(([k,v])=>['chop','tree.fall','mine','rock.break'].includes(k)&&v.last>0).map(([k])=>k)")
    # specials: a dragon's breath and a dwarf's slam from the specialFx feed
    page.evaluate("for(const n of ['spell.fire','slam'])rmSfx._E.state.delete(n)")
    m6 = dict(m); m6['specialFx'] = []
    page.evaluate('m=>updateHUD(m)', m6)
    m7 = dict(m); m7['specialFx'] = [{'id': 5, 'sp': 'breath', 'sx': 2, 'sy': 2, 'tx': 5, 'ty': 2, 'el': 'fire'}, {'id': 6, 'sp': 'slam', 'sx': 3, 'sy': 3, 'tx': 3, 'ty': 3}]
    page.evaluate('m=>updateHUD(m)', m7)
    seen['specials'] = page.evaluate("['spell.fire','slam'].filter(n=>rmSfx._E.state.get(n)&&rmSfx._E.state.get(n).times&&rmSfx._E.state.get(n).times.length)")
    # level-up from XP drops
    l0 = page.evaluate("rmSfx._E.state.get('ui.levelup')?rmSfx._E.state.get('ui.levelup').last:-1")
    m4 = dict(m); m4['xpDrops'] = [{'id': 'x1', 'unit': u['ref'], 'name': 'Dwarf', 'skill': 'Mining', 'xp': 40, 'level': 5}]
    page.evaluate("rmSfx._E.state.delete('ui.levelup')")
    page.evaluate('m=>updateHUD(m)', m4)
    seen['levelup'] = page.evaluate("!!rmSfx._E.state.get('ui.levelup')")
    # settings: a slider change saves locally and to the server; the model's copy is applied back
    page.evaluate("const i=document.querySelector('#rmSound input[data-k=wd]');i.value=20;i.dispatchEvent(new Event('input',{bubbles:true}))")
    page.wait_for_timeout(900)
    seen['saved_url'] = page.evaluate("decodeURIComponent(window.testLastURL||'')")[:160]
    seen['saved_local'] = page.evaluate("localStorage.getItem('rmAudio')")
    m5 = dict(m); m5['audio'] = json.dumps({'master': 64, 'fx': 80, 'ui': 50, 'vo': 70, 'amb': 45, 'mus': 33, 'bg': 1}, separators=(',', ':'))
    page.evaluate('m=>updateHUD(m)', m5)
    seen['from_server'] = page.evaluate("[rmSfx.prefs().master,document.querySelector('#rmSound input[data-k=master]').value]")
    # mute in the background: the app bridge says another app is in front, then that the game is back
    page.evaluate('window.dmAppActive(false)'); page.wait_for_timeout(700)
    seen['bg_inactive'] = page.evaluate('rmSfx.stats().state')
    page.evaluate('window.dmAppActive(true)'); page.wait_for_timeout(300)
    seen['bg_active'] = page.evaluate('rmSfx.stats().state')
    # the HUD's other settings come back from the player's profile and are mirrored to it when they change
    hp = json.dumps({'rmSettings': json.dumps({'scale': 'auto', 'cb': True, 'look': 'hd2d', 'xp': False}), 'rm-edgescroll': '0'}, separators=(',', ':'))
    m8 = dict(m); m8['hudPrefs'] = hp
    page.evaluate('m=>updateHUD(m)', m8)
    seen['restored'] = page.evaluate("[rmSfx._E.persistRestored,document.body.classList.contains('cb'),localStorage.getItem('rm-edgescroll'),document.getElementById('setEdge')?document.getElementById('setEdge').checked:null]")
    page.evaluate("localStorage.setItem('rm-rclick','orders')")
    page.wait_for_timeout(3300)
    seen['mirrored'] = page.evaluate("decodeURIComponent(window.testLastURL||'')")[:200]
    # ambience and music come up (forced quickly here); nothing the audio does may hold the page's main thread 50 ms or more
    page.evaluate("window.auLong=[];try{new PerformanceObserver(l=>{for(const e of l.getEntries())auLong.push(Math.round(e.duration))}).observe({type:'longtask',buffered:false})}catch(e){}")
    page.evaluate("rmSfx._E.mus.next=0.01;rmSfx._E.amb.next=0;rmSfx._E.night=true")
    page.wait_for_timeout(3500)
    page.evaluate("rmSfx._E.z=2;rmSfx._E.mus.phrase=null;rmSfx._E.mus.next=0.01")
    page.wait_for_timeout(3500)
    seen['long_tasks'] = page.evaluate('window.auLong')
    st = page.evaluate('rmSfx.stats()')
    seen['stats'] = st
    browser.close()
    httpd.shutdown()
checks = {
    'no_script_errors': not errors,
    'api_and_wrapping': seen['api'] and seen['wrapped'],
    'sound_settings': [s.split('=')[0] for s in seen['sliders']] == ['master', 'fx', 'ui', 'amb', 'wd'] and seen['bg_switch'] and all(s.split('=')[1].split('/')[0] == s.split('/')[1] for s in seen['sliders']),
    'recordings_load': seen['rec']['files'] == len(recs) > 0 and seen['rec']['loaded'] == len(recs),
    'starts_on_click': seen['before_click'] == 'none' and seen['after_click'] == 'running',
    'ui_hover_and_click': seen['ui_played'] >= 2,
    'every_named_sound': not seen['named_failed'],
    'synth_ambience_and_music_off': not seen['off_but_playing'],
    'rendered_by_worker': seen['ready'] and seen['worker'] == 'yes',
    'order_cue_and_voice': seen['order_played'] >= 2 if VOICES else (seen['order_played'] >= 1 and seen['voice_live'] == 0),
    'combat_from_hits': seen['combat_played'] >= 8,
    'war_drums_in_the_fight': bool(seen['drums']),
    'impact_fall_and_moment_hooks': len(seen['hook_names']) == 7 and seen['impact_body'],
    'throttled': seen['throttle_played'] <= 12 and seen['throttle_skipped'] >= 80 and seen['long_gap'] == [True, False],
    'work_from_blows': 'chop' in seen['work_names'] and 'tree.fall' in seen['work_names'],
    'levelup': seen['levelup'],
    'specials': len(seen['specials']) == 2,
    'saves_to_server': 'rm=audioprefs' in seen['saved_url'] and '"wd":20' in seen['saved_url'] and '"wd":20' in (seen['saved_local'] or ''),
    'applies_server_copy': seen['from_server'] == [64, '64'],
    'hud_settings_restored': 'rmSettings' in (seen['restored'][0] or []) and seen['restored'][1] is True and seen['restored'][2] == '0' and seen['restored'][3] in (False, None),
    'hud_settings_mirrored': 'rm=hudprefs' in seen['mirrored'] and 'orders' in seen['mirrored'],
    'forest_bed_no_music': st['bed'] and not st['amb'] and not st['music'],
    'output_moves': st['peak'] > 0.001 or st['played'] > 0,
    'no_engine_errors': st['errors'] == 0,
    'no_long_tasks': not seen['long_tasks'],
    'mutes_in_background': seen['bg_inactive'] == 'suspended' and seen['bg_active'] == 'running',
}
result = dict(passed=all(checks.values()), checks=checks, seen=seen, errors=errors[:8], warnings=warns[:8])
out.mkdir(parents=True, exist_ok=True)
(out/'check-audio-hud.json').write_text(json.dumps(result, indent=1) + '\n')
print(json.dumps(result, indent=1)[:4000])
raise SystemExit(0 if result['passed'] else 1)
