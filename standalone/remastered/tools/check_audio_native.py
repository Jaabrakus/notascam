#!/usr/bin/env python3
"""The HUD's sound engine in the real client (packaged engine + client, real WebKit page, from a temporary copy of
game/ with a test-only hook). Run it through the lock, under caffeinate:
    caffeinate -d -i -u python3 tools/runlock.py --who audio -- python3 tools/check_audio_native.py
Checks: Audio.dm puts audio.js into the page (rmSfx exists) and sends the recordings, the audio is running (the app's web
view lets it start before any click; if it does not, one real AppKit click in the 3D view starts it), sounds play through
WebKit's audio (the engine's output meter moves), no script errors, the forest bed plays (no synthesized ambience or
music), a chop and a fight are heard from the model and the fight brings in the war drums, and the Sound settings
round-trip through the server (rm=audioprefs -> the player's profile -> the HUD model's "audio").
The hook reports with send('ckprobe', ...), which the client log records. Writes
reports/polish-2026-10-22/audio/check-audio-native.json and a screenshot."""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPRT = ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime'
REPLICA = ROOT.parent/'replica'
sys.path.insert(0, str(REPLICA/'tools'))
from skin_layout import write_hints
OUT = ROOT/'reports/polish-2026-10-22/audio'
dotnet = APPRT/'dotnet/dotnet'
work = Path(tempfile.mkdtemp(prefix='dm-audio-')); world = work/'world'; probe = work/'probe'; probe.mkdir()
shutil.copytree(ROOT/'game', world, ignore=shutil.ignore_patterns('Cave Crawlers.json', 'ErrorLog.txt', 'units', 'players'))
(world/'units').mkdir(); (world/'players').mkdir()
(world/'test-race.txt').write_text('Dwarf')   # Onboarding.dm: keep the native race prompt, which the client answers (DM_TEST_RACE)
HOOK = r"""
// TEST HOOK (audio check, temporary copy only): report the sound engine's state; once a real click has started the
// audio, play a few sounds, sample the output meter and save a setting.
window.auErr=[];addEventListener('error',e=>auErr.push((String(e.message||e)+' @'+e.lineno+':'+e.colno).slice(0,180)));
window.auStage=0;window.auPeak=0;let auN=0;window.auEver=new Set();
window.auDrums=0;setInterval(()=>{const S=window.rmSfx;if(S){for(const [k,v] of S._E.state)if(v&&v.times&&v.times.length)auEver.add(k);const d=S.stats().drums;if(d)window.auDrums=Math.max(window.auDrums,d.level)}},100);   // every sound heard and the war drums' heaviest level, over the whole run
setInterval(()=>{const S=window.rmSfx;if(S){const st=S.stats();if(st.state==='running'){window.auPeak=Math.max(window.auPeak,st.peak);if(!window.auStage){window.auStage=1;window.auAt=performance.now();
  S('ui.levelup');setTimeout(()=>S.order('move',{}),500);setTimeout(()=>S('ui.notify'),1600);setTimeout(()=>{S.set(Object.assign(S.prefs(),{wd:31}));try{localStorage.setItem('rm-hftab','health')}catch(e){}window.auStage=2},2200)}}}},100);
// once the scripted scene starts (the first chop heard), record 30 s of the game's own sound (MediaRecorder on the engine's
// last bus) and pass it out in base64 pieces through send('ckrec', 'k/N/data'), which the client log records
window.auRec=null;
setInterval(()=>{const S=window.rmSfx;if(!S||window.auRec||!S._E.ctx||!window.MediaRecorder)return;const st=S._E.state.get('chop');if(!(st&&st.times&&st.times.length))return;
 try{const E=S._E,d=E.ctx.createMediaStreamDestination();E.out.connect(d);const r=new MediaRecorder(d.stream,{mimeType:'audio/mp4',audioBitsPerSecond:64000}),ch=[];window.auRec={state:'rec'};
  r.ondataavailable=e=>ch.push(e.data);r.onstop=()=>{new Blob(ch).arrayBuffer().then(ab=>{const u8=new Uint8Array(ab);let s='';for(let i=0;i<u8.length;i+=8192)s+=String.fromCharCode.apply(null,u8.subarray(i,i+8192));
   const b64=btoa(s),N=Math.ceil(b64.length/3000);window.auRec={state:'send',n:N,size:u8.length};let k=0;const tick=()=>{if(k>=N){window.auRec.state='done';return}send('ckrec',k+'/'+N+'/'+b64.slice(k*3000,(k+1)*3000));k++;setTimeout(tick,150)};tick()})};
  r.start();setTimeout(()=>r.stop(),30000)}catch(e){window.auRec={state:'err',err:String(e)}}},500);
setInterval(()=>{auN++;const S=window.rmSfx;send('ckprobe',JSON.stringify({au:auN,played:[...auEver],s:S?S.stats():null,err:auErr.slice(0,4),audio:model&&model.audio||null,stage:window.auStage,peak:window.auPeak,drums:window.auDrums,vis:document.visibilityState,hidden:S?S._E.hidden:null,rec:window.auRec,z:S?S._E.z:null,model:!!(S&&S._E.model),wired:S?S._E.wired:null}))},2000);
"""
# play scenario (temporary copy only): once the player's units are in and the HUD is up, a tree beside one of them (given
# an axe) is ordered chopped through the real click path, and a goblin wakes beside another so they fight
SCENE = r'''
var/au_done = 0
world/New()
	..()
	spawn(50) AuLoop()
proc/AuLoop()
	var/n = 0
	while(!au_done)
		sleep(10)
		n++
		for(var/Player/P in world) if(P.client)
			var/list/U = list()
			for(var/mob/Monsters/M in P.UnitList) if(M.HP > 0) U += M
			if(n % 10 == 0) world.log << "AU|wait|ready=[P.remaster_hud_ready]|units=[length(U)]"
			if(!P.remaster_hud_ready || !length(U)) continue
			au_done = 1
			sleep(80)
			AuSetup(P, U)
proc/AuSetup(Player/P, list/U)
	var/mob/Monsters/A = U[1]
	var/mob/Monsters/B = length(U) >= 2 ? U[2] : null
	var/turf/C = locate(clamp(A.x, 20, world.maxx - 20), clamp(A.y, 20, world.maxy - 20), 1)
	for(var/turf/T in block(locate(C.x - 6, C.y - 6, 1), locate(C.x + 6, C.y + 6, 1)))
		if(T.density)
			var/turf/grounds/grass/G = new(T)
			G.density = 0
	for(var/mob/M in range(6, C)) if(!(M in U) && M != P && !istype(M, /mob/WorkShops)) del(M)
	A.loc = C
	A.destination = null
	if(B)
		B.loc = locate(C.x + 4, C.y, 1)
		B.destination = null
	var/turf/T = locate(C.x + 1, C.y, 1)
	new /turf/grounds/Trees/Tree1(T)
	var/obj/Items/I = new /obj/Items/Equipment/Weapon/Axes/MetalAxe(A)
	I.suffix = "(Carrying)"
	A.weight += I.weight
	P.loc = C
	P.Selected = list(A)
	P.Remaster3DClick("[T.x]|[T.y]||0|0")
	world.log << "AU|setup|[C.x],[C.y]|[A.remaster_active ? A.remaster_active.kind : "-"]|units=[length(U)]"
	if(!B)
		sleep(120)   // one unit: let it chop a while first
		B = A
	var/mob/Monsters/G = new /mob/Monsters/Goblin/NPC/Scout(locate(B.x + 1, B.y + 1, 1))
	G.destination = null
	G.Sleeping = 0
	for(var/k = 1, k <= 2, k++)   // a few more, so the fight is a battle (the war drums come in with the hits)
		var/mob/Monsters/G2 = new /mob/Monsters/Goblin/NPC/Scout(locate(B.x + 1, B.y - k, 1))
		G2.destination = null
		G2.Sleeping = 0
	P.Selected = list(B)
	P.RemasterAttackOrder(G)   // the card's Attack: a fight for sure, heard through the hits feed
	world.log << "AU|goblin|[G.x],[G.y]|[B.remaster_active ? B.remaster_active.kind : "-"]"
'''
(world/'ZZAudio.dm').write_text(SCENE, encoding='latin-1')
with (world/'Cave Crawlers.dme').open('a', encoding='latin-1') as f: f.write('\n#include "ZZAudio.dm"\n')
hud = world/'Interface/remastered.html'; h = hud.read_text(encoding='utf-8'); k = "send('ready','');"; assert h.count(k) == 1
hud.write_text(h.replace(k, HOOK + '\n' + k), encoding='utf-8')
env = dict(os.environ, DOTNET_ReadyToRun='0')
with (work/'compile.log').open('w') as out:
    subprocess.run([str(dotnet), str(REPLICA/'runtime/macos-x64/compiler/DMCompiler.dll'), str(world/'Cave Crawlers.dme')], env=env, stdout=out, stderr=subprocess.STDOUT, check=True)
hints = work/'layout.json'; write_hints(world/'skin.dmf', hints)
cd = work/'client'; shutil.copytree(APPRT/'client/Space Station 14.app/Contents/Resources', cd, ignore=shutil.ignore_patterns('user_data', '.DS_Store'))
cenv = dict(env, DM_SKIN_LAYOUT_HINTS=str(hints), DM_TEST_RACE='Dwarf', DM_NATIVE_UI_PROBE=str(probe), DM_GAME_SNAPSHOT=str(probe/'game.png'),
            ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW=str(APPRT/'webview-webkit'))
slp = work/'server.log'; clp = work/'client.log'; elog = world/'ErrorLog.txt'


def wait(cond, t):
    d = time.monotonic() + t
    while time.monotonic() < d:
        v = cond()
        if v: return v
        time.sleep(.25)
    return None


def reports():
    out = []
    for m in re.findall(r'rm=ckprobe&value=([^\s&]+)', clp.read_text(errors='replace')):
        try:
            d = json.loads(urllib.parse.unquote(m))
            if 'au' in d: out.append(d)
        except Exception: pass
    return out


def act(**a):
    (probe/'action.pending').write_text(json.dumps(a)); (probe/'action.pending').replace(probe/'action.json')
    wait(lambda: not (probe/'action.json').exists(), 10); time.sleep(1.2)


def front(pid):
    subprocess.run(['osascript', '-e', f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'], capture_output=True, timeout=10)


seen = {}; server = client = None
try:
    with slp.open('w') as sl, clp.open('w') as cl:
        server = subprocess.Popen([str(dotnet), str(APPRT/'server/Robust.Server.dll'), '--data-dir', str(work/'data'), '--cvar', f'opendream.json_path={world/"Cave Crawlers.json"}',
            '--cvar', 'opendream.topic_port=25671', '--cvar', 'net.bindto=127.0.0.1', '--cvar', 'net.port=12171', '--cvar', 'auth.mode=0', '--cvar', 'status.enabled=false',
            '--cvar', 'hub.advertise=false', '--cvar', 'game.auto_pause_empty=false'], env=env, stdout=sl, stderr=subprocess.STDOUT, cwd=world)
        assert wait(lambda: ' -> Ready' in slp.read_text(errors='replace'), 300), 'server not ready'
        client = subprocess.Popen([str(dotnet), str(cd/'Robust.Client.dll'), '--mount-zip', str(APPRT/'server/Content.Client.zip'), '--connect', '--connect-address', 'udp://127.0.0.1:12171',
            '--username', 'AudioCheck', '--self-contained', '--cvar', 'web.headless=false', '--cvar', 'discord.enabled=false'], cwd=cd, env=cenv, stdout=cl, stderr=subprocess.STDOUT)
        assert wait(lambda: (probe/'game.png').exists(), 300), 'client never reached the game'
        front(client.pid)
        r = wait(lambda: [x for x in reports() if x.get('s')], 90)
        assert r, 'the page never reported (no rmSfx?)'
        seen['before_click'] = r[-1]['s']['state']
        time.sleep(3)
        # one real click in the 3D view, away from the HUD panels
        st = json.loads((probe/'state.json').read_text()); win = ([w for w in st['windows'] if w.get('viewports')] or [max(st['windows'], key=lambda w: w['width'] * w['height'])])[0]
        front(client.pid)
        act(window=win['id'], kind=5, x=0.5, y=0.42, code=0, modifiers=0, text='')
        r = wait(lambda: [x for x in reports() if x.get('s') and x['s']['state'] == 'running'], 30)
        seen['after_click'] = r[-1]['s']['state'] if r else (reports()[-1]['s']['state'] if reports() else None)
        if not r:   # some web views need the click on the page itself: try the settings button area too
            act(window=win['id'], kind=5, x=0.5, y=0.55, code=0, modifiers=0, text='')
            r = wait(lambda: [x for x in reports() if x.get('s') and x['s']['state'] == 'running'], 20)
            seen['after_second_click'] = r[-1]['s']['state'] if r else None
        front(client.pid)
        r = wait(lambda: [x for x in reports() if x.get('stage') == 2 and x.get('audio') and '"wd":31' in x['audio']], 40)
        # the play scenario: chopping and a fight, heard through the model (not called by the hook)
        front(client.pid)
        seen['setup'] = wait(lambda: re.findall(r'AU\|setup\|[^\r\n]*', elog.read_text(errors='replace') if elog.exists() else '') or re.findall(r'AU\|setup\|[^\r\n]*', slp.read_text(errors='replace')), 120)
        wait(lambda: (lambda P: 'chop' in P and any(n in P for n in ('hit.flesh', 'hit.armor', 'hit.big', 'parry', 'block')))(set((reports() or [{}])[-1].get('played') or [])), 60)
        wait(lambda: 'wd.boom' in ((reports() or [{}])[-1].get('played') or []), 60)   # the war drums, once the fight is a battle
        # the recording: 30 s from the first chop, then its pieces
        front(client.pid)
        wait(lambda: ((reports() or [{}])[-1].get('rec') or {}).get('state') in ('done', 'err'), 120)
        # mute in the background: another app comes to the front (WebKitBridge.swift tells the page), then the game again
        subprocess.run(['osascript', '-e', 'tell application "Finder" to activate'], capture_output=True, timeout=10)
        r = wait(lambda: [x for x in reports()[-2:] if (x.get('s') or {}).get('state') == 'suspended'], 12)
        seen['app_inactive'] = [(r[-1].get('s') or {}).get('state'), r[-1].get('hidden')] if r else [((reports() or [{}])[-1].get('s') or {}).get('state'), (reports() or [{}])[-1].get('hidden')]
        front(client.pid)
        r = wait(lambda: [x for x in reports()[-1:] if (x.get('s') or {}).get('state') == 'running'], 12)
        seen['app_back'] = (r[-1].get('s') or {}).get('state') if r else None
        time.sleep(2)
        last = reports()[-1]
        seen['last'] = last; seen['round_trip'] = bool(r)
        shutil.copy2(probe/'game.png', OUT/'native-game.png') if (probe/'game.png').exists() else None
finally:
    for p in (client, server):
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(15)
            except Exception: p.kill()
# put the recording back together
parts = {}
for m in re.findall(r'rm=ckrec&value=([^\s&]+)', clp.read_text(errors='replace') if clp.exists() else ''):
    k, n, data = urllib.parse.unquote(m).split('/', 2)
    parts[int(k)] = (int(n), data)
if parts and len(parts) == next(iter(parts.values()))[0]:
    import base64
    (OUT/'real-play.m4a').write_bytes(base64.b64decode(''.join(parts[k][1] for k in sorted(parts))))
    seen['recording'] = f'real-play.m4a ({len(parts)} pieces)'
else:
    seen['recording'] = f'incomplete: {len(parts)} pieces'
errs = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|Exception occurred:|runtime error).*$', (elog.read_text(errors='replace') if elog.exists() else ''), re.I | re.M)
prof = list((world/'units').glob('remaster_profile_*.sav'))
saved = any(re.search(rb'wd(\\u0022|\\?")?\s*:\s*31', p.read_bytes()) for p in prof)   # the drum volume set above (the savefile writes quotes as \u0022)
hud_saved = any(b'rm-hftab' in p.read_bytes() for p in prof)
hud_sent = 'rm=hudprefs' in (clp.read_text(errors='replace') if clp.exists() else '')
last = seen.get('last') or {}
s = last.get('s') or {}
checks = {
    'engine_in_page': bool(s),
    'audio_running': 'running' in (seen.get('before_click'), seen.get('after_click'), seen.get('after_second_click')),
    'sounds_played': (s.get('played') or 0) >= 4,
    'output_meter_moved': (last.get('peak') or 0) > 0.0005,
    'no_audio_errors': (s.get('errors') or 0) == 0 and not [e for e in (last.get('err') or []) if 'audio' in e.lower() or 'rmSfx' in e],
    'settings_round_trip': seen.get('round_trip', False),
    'saved_in_profile': saved,
    'hud_settings_mirrored': hud_sent and hud_saved,
    'mutes_when_app_inactive': seen.get('app_inactive', [None])[0] == 'suspended' and seen.get('app_back') == 'running',
    'no_runtime_errors': not [e for e in errs if 'Audio' in e],
    'model_hooks_live': bool(last.get('model')) and last.get('z') in (1, 2, 3, 4) and sorted(last.get('wired') or []) == ['logPush', 'send', 'update3D', 'updateHUD'],
    'forest_bed_no_synth_ambience_or_music': s.get('bed') is True and not s.get('amb') and not s.get('music'),
    'recordings_sent_and_loaded': (s.get('rec') or {}).get('files', 0) >= 28 and (s.get('rec') or {}).get('loaded') == (s.get('rec') or {}).get('files'),
    'war_drums_in_the_fight': any(n.startswith('wd.') for n in (last.get('played') or [])) and (last.get('drums') or 0) >= 1,
    'play_chop_from_model': 'chop' in (last.get('played') or []),
    'play_combat_from_model': any(n in (last.get('played') or []) for n in ('hit.flesh', 'hit.armor', 'hit.big', 'parry', 'block', 'swing.light', 'swing.heavy', 'swing.thrust')),
}
result = dict(passed=all(checks.values()), checks=checks, page_errors_other_code=(last.get('err') or [])[:4], seen=seen, runtime_errors=errs[:6], profiles=[p.name for p in prof], work=str(work))
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'check-audio-native.json').write_text(json.dumps(result, indent=1) + '\n')
print(json.dumps(result, indent=1)[:3000])
raise SystemExit(0 if result['passed'] else 1)
