"""Retarget installed Dungeon Master runtime definitions into an isolated Elf library."""
from pathlib import Path
import json,hashlib,shutil,base64
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'Dungeon Master Sample/GOA Sword and Shield Rig/library'
ELF=ROOT/'Dungeon Master Sample/Unique Body Equipment Rig'
GEAR=ROOT/'standalone/goa-races/armor-designs/racial-redraws-v1/parts'
OUT.mkdir(parents=True,exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
source=json.loads((HERE/'runtime-source.json').read_text());clips={};images={};hashes=dict(source['hashes'])
def tracked(path):
 hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
 return path

def asset(path,name):
 path=tracked(path);shutil.copyfile(path,OUT/'assets'/name)
 images[name]='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
 return name

for name,d in source['defs'].items():
 category='Work' if d.get('work') or name in ['lift','carry','hold','climb'] else 'Death gestures' if name.startswith('d_') else 'Defense' if name in ['getup','block','parry','dodge','riposte'] else 'Combat'
 clips[name]={'id':name,'label':name.replace('_',' ').title(),'category':category,'keys':d['keys'],'duration':d['keys'][-1][0]+.25,'events':{k:d[k] for k in ['hit','release','trail'] if k in d},'definition':d,'source':'deaths.js' if name.startswith('d_') else 'work.js' if category=='Work' else 'skills.js','status':'Keys loaded by the installed game; retargeted Elf preview.'}
physics=['fall','crumple','spin','shot','flying','hammer','throw','stiff','liedown','melt','heap','ko','flinch','armoff','legoff','armcut','legcut']
for name in physics:
 cid='reaction.'+name
 clips[cid]={'id':cid,'label':name.title(),'category':'Physics reactions','duration':.7 if name=='flinch' else 1.4,'keys':[[0],[1.4]],'events':{},'physics':name,'source':'ragdoll.js / rdKind','status':'Deterministic sprite adaptation of live physics; not a captured simulation.'}
for name,d in source['causes'].items():
 cid='death.'+name;seq=[d['act'],'reaction.'+d['fall']]
 clips[cid]={'id':cid,'label':name.title()+' death','category':'Death sequences','sequence':seq,'duration':sum(clips[x]['duration'] for x in seq),'keys':[[0]],'events':{},'source':'deaths.js / DZDEF','definition':d,'status':'Game death gesture and fall sequence. Particle effects remain external.'}
# These are runtime sprite-strip behaviors, not the arena's extra authored clips.
for name,mode,duration in [('idle','idle',1.2),('walk','walk',.8),('idle_armed','idle',1.2),('walk_armed','walk',.8),('sprite_attack','fallback',.9)]:
 clips[name]={'id':name,'label':name.replace('_',' ').title(),'category':'Sprite movement','duration':duration,'keys':[[0],[duration]],'events':{},'mode':mode,'source':'remastered.html sprite draw / View3D.dm','status':'Current sprite sequence retargeted to the approved Elf frames.'}
if not source['flags']['rm_g3_work_mine_chop']:
 for name in ['mine','woodchop']:
  clips[name]['inactiveDefinition']=clips[name].pop('definition')
  clips[name].update(keys=[[0],[.36],[.585],[.9]],duration=.9,events={},mode='fallback',source='Gear3D.dm rm_g3_work_mine_chop=0; remastered.html attack strip',status='Current game uses its attack strip for this job. Separate keyed work move is disabled.')
# The live bow is procedural rdShotDraw, not an SK.defs keyframed skill.
for name,label in [('bow_ready','Bow ready'),('bow_shot','Bow draw and release')]:
 clips[name]={'id':name,'label':label,'category':'Ranged','duration':1.75,'mode':'bow',
  'keys':[[0],[.32],[.72],[.9],[1.15],[1.75]],'events':{'release':.9} if name=='bow_shot' else {},
  'source':'ragdoll.js / rdShoot + rdShotDraw','status':'Live bow timing adapted to Elf: raise, draw, release at 0.9s, lower at 1.15s, recover by 1.75s.'}
clips['throw'].update(label='Spear throw',category='Ranged')
for name,label in [('throw_axe','Axe throw'),('throw_dagger','Dagger throw')]:
 clips[name]={**clips['throw'],'id':name,'label':label}
arrow=asset(ROOT/'Dungeon Master Sample/Sprites/Combat/Human/arrow.png','arrow.png')
rig=json.loads(tracked(ELF/'rig.json').read_text());views=[]
for d,view in enumerate(rig['directions']):
 p=view['fullBody'];record={'name':view['name'],'arms':view['arms'],'legs':p['legs'],'waist':p['waist'],'neck':p['neck'],'nearLeg':p['nearLeg'],'parts':{},'walk':[]}
 for key,file in p['parts'].items():record['parts'][key]=asset(ELF/'assets'/file,f'{d}-{key}.png')
 for f,frame in enumerate(view['frames']):
  record['walk'].append({k:asset(ELF/'assets'/frame[k],f'{d}-walk-{f}-{k}.png') for k in ['refined-torso','render-head']})
 record['jointColors']={}
 for side in ['right','left']:
  for label,part,point in [('Elbow','Forearm',view['arms'][side][1]),('Wrist','Hand',view['arms'][side][2]),('Knee','Shin',p['legs'][side][1]),('Ankle','Foot',p['legs'][side][2])]:
   image=Image.open(ELF/'assets'/p['parts'][side+part]).convert('RGBA')
   candidates=[(x,y,image.getpixel((x,y))) for y in range(64) for x in range(64) if (lambda c:c[3]>=200 and c[0]>c[1]*1.08 and c[1]>c[2]*1.08 and c[2]>40)(image.getpixel((x,y)))]
   assert candidates,(side,part)
   record['jointColors'][side+label]=min(candidates,key=lambda v:(v[0]-point[0])**2+(v[1]-point[1])**2)[2]
 views.append(record)
# Reuse measured item grips from the accepted attack where available.
accepted=json.loads(tracked(ROOT/'Dungeon Master Sample/GOA Sword and Shield Rig/rig.json').read_text());items={}
for ident,profile in accepted['weapons'].items():
 item={'label':profile['label'],'views':[],'two':False}
 for d,F in enumerate('SNEW'):
  v=profile['facings'][F];item['views'].append({'image':asset(ROOT/'Dungeon Master Sample/GOA Sword and Shield Rig/assets'/v['image'],f'gear-{ident}-{d}.png'),'grip':v['grip']})
 items[ident]=item
extra={'spear':('polearms-tools/weapon.spear',48,10,True),'halberd':('polearms-tools/weapon.halberd',48,18,True),'battle_axe':('melee-weapons/weapon.battle_axe',38,21,True),'longsword':('melee-weapons/weapon.longsword',38,12,True),'staff':('magic-staves/weapon.crystal_staff',48,14,False),'bow':('polearms-tools/weapon.bow',36,12,True),'pickaxe':('polearms-tools/weapon.pickaxe',34,24,True),'hammer':('polearms-tools/weapon.hammer',24,16,False),'spade':('polearms-tools/weapon.spade',38,13,True),'harpoon':('polearms-tools/weapon.harpoon',45,10,True),'fishing_rod':('polearms-tools/weapon.fishing_rod',48,18,False),'morning_star':('polearms-tools/weapon.morning_star',28,17,False)}
for ident,(folder,height,width,two) in extra.items():
 item={'label':ident.replace('_',' ').title(),'views':[],'two':two}
 for d,F in enumerate(['South','North','East','West']):
  src=tracked(GEAR/folder/(F+'.png'));im=Image.open(src).convert('RGBA');im=im.resize((min(width,max(3,round(im.width*height/im.height))),height),Image.Resampling.NEAREST)
  y=round(height*(.52 if ident in ['spear','halberd','staff','harpoon','bow','fishing_rod'] else .8));xs=[x for x in range(im.width) if im.getpixel((x,y))[3]>128]
  grip=[xs[len(xs)//2] if xs else im.width//2,y];name=f'gear-{ident}-{d}.png';im.save(OUT/'assets'/name)
  images[name]='data:image/png;base64,'+base64.b64encode((OUT/'assets'/name).read_bytes()).decode();item['views'].append({'image':name,'grip':grip})
 items[ident]=item
items['shield']={'label':'Round shield','views':[]}
for d,F in enumerate('SNEW'):
 items['shield']['views'].append({'image':asset(ROOT/f'Dungeon Master Sample/GOA Sword and Shield Rig/assets/gear/{F}-shield.png',f'shield-{d}.png'),'grip':[9 if F=='E' else 11,12]})
for k,c in clips.items():
 d=c.get('definition',{});weapon='sword';shield=c['category'] in ['Combat','Defense'] or k.endswith('_armed')
 if d.get('bare') or k.startswith('d_') or k.startswith('death.') or k in ['idle','walk','getup']:weapon='none';shield=False
 elif k in ['chop','cleave','heavyblow','woodchop']:weapon='battle_axe';shield=False
 elif k in ['smash','skullcracker']:weapon='mace'
 elif k=='launch':weapon='warhammer';shield=False
 elif k in ['thrust','skewer','throw','spearfish']:weapon='harpoon' if k=='spearfish' else 'spear';shield=False
 elif k=='sweep':weapon='halberd';shield=False
 elif k in ['stab','flurry']:weapon='dagger'
 elif d.get('spell') or k in ['cast','firewave','runebolt','bonespear','raiseskeleton','calllightning','frozenhamstring']:weapon='staff';shield=False
 elif k in ['mine','smith','build','fish','till']:weapon={'mine':'pickaxe','smith':'hammer','build':'hammer','fish':'fishing_rod','till':'spade'}[k];shield=False
 if k.startswith('bow_'):weapon='bow';shield=False
 if k=='throw_axe':weapon='hand_axe';shield=False
 if k=='throw_dagger':weapon='dagger';shield=False
 if d.get('stowShield'):shield=False
 if k.startswith('reaction.'):weapon='sword';shield=True
 c['equipment']={'weapon':weapon,'shield':shield}
data={'arrow':arrow,'revision':'rig-package-16','clips':clips,'views':views,'items':items,'images':images,'grips':[{'right':r['swordGrip'],'left':r['shieldGrip']} for r in accepted['frames']['idle'][0]],'runtime':source,'cellSize':192,'origin':[64,64],'limitations':['Elf male body mapping; other appearances require calibrated profiles.','Deep bends and physics falls need visual polish.','World projectile collisions, particles, carried loads and live damage are separate game systems.','Source game files and the accepted attack preview are preserved.']}
(OUT/'library.json').write_text(json.dumps({k:v for k,v in data.items() if k!='images'},indent=2))
(OUT/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
for f in ['engine.js','app.js']:shutil.copyfile(HERE/f,OUT/f)
html=(HERE/'viewer.html').read_text().replace('/*DATA*/', 'const DATA='+json.dumps(data)+';')
(OUT/'index.html').write_text(html)
(OUT/'README.md').write_text('''# Dungeon Master game animations on the approved Elf

Source: the installed Banners of the Deep / Dungeon Master app's gear3d.js is byte-identical to the working game runtime. Its included skills/work/death scripts are checked before extraction. source-hashes.json records inputs. runtime-source.json is rebuilt from these scripts; no arena-only clips are imported.

The current game has doll animations enabled, but mining and woodcutting doll work moves disabled. Those jobs use the 0.9-second attack-strip behavior here. Idle/walk use the approved Elf drawn frames. Combat, defenses, work gestures and death gestures retain the runtime's key times and event markers. Runtime lunge, step and rear-foot channels are projected to four facings and fitted to the Elf's leg lengths.

Physics reactions are deterministic sprite approximations of rdKind, not recorded live simulations. Body artwork is the approved Elf male's 15-part rig, with its existing inferred far leg. Polish pass 2 adds source-palette joint backing, forearm-following fists, weapon-axis support grips, a corrected West counterbalance and exact guard recovery. Deep poses and limb seams remain review drafts. Pass 3 removes double-applied torso lean from absolute weapon angles. Bow ready/shot follow rdShotDraw timing; Side bow stances use the right bow hand: East uses the back-facing body with East head, West uses the front-facing body with West head, per the approved stance request. North/South show only a short arrow tip, with North occluded by the body. The other hand draws a separate string, then a preview arrow leaves the bow. North/South throw windups and release grips stay at the anatomical right shoulder. Spear/axe/dagger throws release at the original throw event with a detached preview projectile. Preview projectiles fade before reaching the padding boundary; collisions, damage, world flight, particles and carried loads remain external. This library does not replace game files.

Use category and animation selectors, pause/scrub, native zoom, joints, and equipment toggles. Each PNG export has four S/N/E/W columns, 192px cells, original 64px body origin [64,64], and an adjacent metadata file containing sample times and events. Source clip data and per-frame joints make the conversion reviewable. The previously accepted sword/shield preview remains at ../index.html.

Rebuild: node standalone/goa-races/elf-game-animations/extract.js; python3 standalone/goa-races/elf-game-animations/build.py. verify_export.py tests and bakes every clip through the browser renderer.
''')
print(json.dumps({'clips':len(clips),'parts':15,'output':str(OUT),'images':len(images)}))
