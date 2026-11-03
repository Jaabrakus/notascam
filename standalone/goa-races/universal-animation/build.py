"""Source-backed universal clips and an isolated GOA human mapping preview."""
from pathlib import Path
from PIL import Image
import json,base64,hashlib,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
source=json.loads((HERE/'source-clips.json').read_text());clips={}
for name,d in source['defs'].items():
 category='Work' if d.get('work') or name in ['lift','carry','hold'] else 'Reactions' if name.startswith('d_') or name in ['getup','block','parry','dodge'] else 'Combat'
 clips[name]=dict(id=name,label=name.replace('_',' ').title(),category=category,keys=d['keys'],duration=d['keys'][-1][0]+.25,events={k:d[k] for k in ['hit','release','trail'] if k in d},source='art/gear3d/'+('deaths.js' if name.startswith('d_') else 'work.js' if category=='Work' else 'skills.js'),sourceDefinition=d,status='source-keyed clip; mapping preview')
physics=['fall','crumple','spin','shot','flying','hammer','throw','stiff','liedown','melt','heap','ko','flinch','armoff','legoff','armcut','legcut']
for name in physics:
 cid='reaction.'+name
 clips[cid]=dict(id=cid,label=name.title(),category='Physics reactions',duration=1.4 if name not in ['ko','flinch'] else 3.5 if name=='ko' else .7,physics=name,keys=[[0],[1]],source='art/gear3d/ragdoll.js#rdKind',status='deterministic sprite-preview adaptation; live physics retained separately')
for name,d in source['causes'].items():
 cid='death.'+name;act=d['act'];duration=clips[act]['duration']+1.3
 clips[cid]=dict(id=cid,label=name.title()+' death',category='Death sequences',duration=duration,sequence=[act,'reaction.'+d['fall']],tint=d.get('tint'),keys=[[0],[duration]],source='art/gear3d/deaths.js#DZDEF',effects='Live particles/tints remain external to body clips',status='source-defined sequence; external effects not baked')
custom={
 'idle':dict(duration=1.2,keys=[[0],[.6,{'crouch':.025}],[1.2]]),
 'walk':dict(duration=.8,procedural='walk',keys=[[0],[.8]]),
 'walk_armed':dict(duration=.9,procedural='walk',holdProfile='reference_guard',keys=[[0],[.9]]),
 'idle_armed':dict(duration=1.6,holdProfile='reference_guard',keys=[[0],[.8,{'crouch':.025}],[1.6]]),
 'run':dict(duration=.55,procedural='run',keys=[[0],[.55]]),
 'sleep':dict(duration=1.6,physics='liedown',keys=[[0],[1.6]]),
 'bow_shot':dict(duration=1.2,keys=[[0],[.25,{'Lfx':13,'Lfy':-4,'Rhx':3,'Rhy':-4}],[.65,{'Lfx':15,'Lfy':-3,'Rhx':3,'Rhy':3}],[.8,{'Lfx':15,'Lfy':-3,'Rhx':7,'Rhy':4}],[1.2]],events={'release':.8}),
 'spear_short_jab':dict(duration=1.2,weaponViewDirections=[None,None,[1,-.35],[-1,-.35]],keys=[[0,{'Rfx':4,'Rfy':-10,'W':-.4}],[.25,{'Rfx':2,'Rfy':-10,'W':-.4}],[.45,{'Rfx':8,'Rfy':-11,'W':-.4}],[.75,{'Rfx':5,'Rfy':-10,'W':-.4}],[1.2]],events={'hit':[.45]},oneHanded=True),
 'anticipation_hop':dict(duration=.7,keys=[[0],[.17,{'rootForward':-.15,'hop':.22}],[.34,{'rootForward':.15,'hop':.22}],[.5,{'rootForward':.1}],[.7]],oneHanded=True),
 'universal_flinch':dict(duration=.42,keys=[[0],[.07,{'lean':-.14,'crouch':.06,'rootForward':-.1}],[.16,{'lean':-.18,'crouch':.09,'rootForward':-.12}],[.42]],retainEquipment=True)
}
for name,d in custom.items():clips[name]=dict(id=name,label=name.replace('_',' ').title(),category='New and locomotion',source='Universal authoring additions',status='authored universal clip draft',**d)
clips['reaction.today']=dict(id='reaction.today',label="Today's death",category='Physics reactions',duration=1.2,physics='crumple',keys=[[0],[1.2]],source='Legacy standing death presentation',status='deterministic sprite-preview adaptation')
# Preserve arena variants (different staff/projectile/load names) as aliases, not duplicated body clips.
import re
arena=(ROOT/'standalone/remastered/art/gear3d/arena-anim.html').read_text();aliases=[]
for m in re.finditer(r'<button\b([^>]*)>(.*?)</button>',arena):
 attrs=dict(re.findall(r'([\w-]+)="([^"]*)"',m[1]));kind=next((k for k in ['data-k','data-work','data-a','data-die','data-carry','data-climb'] if k in attrs),None)
 if not kind:continue
 key=attrs[kind];target=key
 if kind=='data-work' and key=='chop':target='woodchop'
 if kind=='data-a':target='reaction.'+key
 if kind=='data-die':target='death.'+key
 if kind=='data-carry':target='carry'
 if kind=='data-climb':target='climb'
 aliases.append(dict(label=re.sub('<.*?>','',m[2]),clip=target,weapon=attrs.get('data-wp'),load=key if kind=='data-carry' else None,live=attrs.get('data-live')=='1',source=kind,resolved=target in clips))
# Body reference pixels come from the other limb pipeline, read only. Snapshot them here.
assets=HERE/'assets';assets.mkdir(exist_ok=True)
limbs=ROOT/'standalone/goa-races/limbs/pixel-assets/human';core=Image.open(limbs/'core.png').convert('RGBA');parts=Image.open(limbs/'parts.png').convert('RGBA')
part_names=['head','torso','armRu','armRl','armLu','armLl','legRu','legRl','legLu','legLl'];atlas=Image.new('RGBA',(640,256));views=[]
for v in range(4):
 c=core.crop((v*64,0,v*64+64,64));head=c.copy();head.paste((0,0,0,0),(0,33,64,64));torso=c.copy();torso.paste((0,0,0,0),(0,0,64,33));pieces={'head':head,'torso':torso}
 for slot,row,cut in [('armR',3,40),('armL',0,40),('legR',9,56),('legL',6,56)]:
  layer=parts.crop((v*64,row*64,v*64+64,row*64+64));upper=layer.copy();upper.paste((0,0,0,0),(0,cut,64,64));lower=layer.copy();lower.paste((0,0,0,0),(0,0,64,cut));pieces[slot+'u']=upper;pieces[slot+'l']=lower
 for col,name in enumerate(part_names):atlas.paste(pieces[name],(col*64,v*64))
 if v==0:R=[[22,34],[21,40],[20,46]];L=[[42,34],[43,40],[44,46]];lr=[[27,52],[25,56],[24,60]];ll=[[37,52],[39,56],[40,60]]
 elif v==1:R=[[42,34],[43,40],[44,46]];L=[[22,34],[21,40],[20,46]];lr=[[37,52],[39,56],[40,60]];ll=[[27,52],[25,56],[24,60]]
 elif v==2:R=[[24,35],[24,41],[26,47]];L=[[35,35],[35,41],[36,46]];lr=[[29,52],[28,56],[27,60]];ll=[[37,52],[36,56],[36,60]]
 else:R=[[29,35],[29,41],[28,46]];L=[[40,35],[40,41],[38,47]];lr=[[27,52],[28,56],[28,60]];ll=[[35,52],[36,56],[37,60]]
 bones={'head':dict(root=[32,32],tip=[32,17]),'torso':dict(root=[32,52],tip=[32,33])}
 for prefix,pts in [('armR',R),('armL',L),('legR',lr),('legL',ll)]:
  bones[prefix+'u']=dict(root=pts[0],tip=pts[1]);bones[prefix+'l']=dict(root=pts[1],tip=pts[2],parent=prefix+'u')
 views.append(bones)
atlas.save(assets/'human-parts.png')
armed=atlas.copy()
# The live game's ragdoll uses near-arm pixels for an otherwise hidden arm. Keep anatomical slots separate.
for view,source_upper,target_upper,dx in [(2,2,4,11),(3,4,2,-11)]:
 for segment in [0,1]:
  piece=atlas.crop(((source_upper+segment)*64,view*64,(source_upper+segment+1)*64,(view+1)*64))
  shifted=Image.new('RGBA',(64,64));shifted.paste(piece,(dx,0))
  armed.paste(shifted,((target_upper+segment)*64,view*64))
armed.save(assets/'human-armed-parts.png')

rig=dict(id='human-calibration',race='Human',directions=['South','North','East','West'],image='assets/human-parts.png',cellSize=64,parts=part_names,views=views,status='Mapping calibration draft; far-side hidden limb pixels are absent, not invented.',sourceHashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [limbs/'core.png',limbs/'parts.png']})
rig['holdProfiles']={'reference_guard':json.loads((HERE/'guard-profile.json').read_text())}
(HERE/'human-rig.json').write_text(json.dumps(rig,indent=2));(HERE/'clips.json').write_text(json.dumps(dict(schema='universal-humanoid-clips-v1',directions=rig['directions'],clips=clips,arenaAliases=aliases),indent=2))
# Existing gear renderer can supply material-colored directional item textures.
cat=json.loads((ROOT/'standalone/goa-races/armory/catalog.json').read_text());cat['items']=[i for i in cat['items'] if i['id'] in ['weapon.arming sword','weapon.spear','weapon.warhammer','weapon.bow','weapon.crystal staff','shield.round']]
paths={p for i in cat['items'] for p in i.get('strips',[])};images={name:'data:image/png;base64,'+base64.b64encode((ROOT/name).read_bytes()).decode() for name in paths};images['skin']='data:image/png;base64,'+base64.b64encode((assets/'human-parts.png').read_bytes()).decode()
images['armedSkin']='data:image/png;base64,'+base64.b64encode((assets/'human-armed-parts.png').read_bytes()).decode()
data=dict(clips=clips,aliases=aliases,rig=rig,images=images,catalog=cat,bodies=[],gear=json.loads((ROOT/'standalone/remastered/game/Interface/gear3d/gear3d-pix.json').read_text()))
html=(HERE/'template.html').read_text().replace('/*DATA*/null',json.dumps(data)).replace('/*EQUIPMENT*/',(ROOT/'standalone/goa-races/armory/equipment.js').read_text()).replace('/*ENGINE*/',(HERE/'engine.js').read_text()).replace('/*APP*/',(HERE/'app.js').read_text())
(HERE/'index.html').write_text(html);(ROOT/'Dungeon Master Sample/GOA Universal Animation Library.html').write_text(html)
proof_data={**data,'defaultPreview':{'clip':'walk_armed','weapon':'weapon.arming sword','shield':True,'bones':False}}
proof=(HERE/'template.html').read_text().replace('/*DATA*/null',json.dumps(proof_data)).replace('/*EQUIPMENT*/',(ROOT/'standalone/goa-races/armory/equipment.js').read_text()).replace('/*ENGINE*/',(HERE/'engine.js').read_text()).replace('/*APP*/',(HERE/'app.js').read_text())
proof=proof.replace('Universal animation library','Our sprites · sword and shield walk').replace("Shared humanoid clips from Dungeon Master's current actions, plus the low spear jab, anticipation hop and universal flinch. The Human skin demonstrates the limb mapping; each race supplies its own pixels and joints.",'The existing Human sprites, posed to follow the sword-and-shield guard in your reference. Body and equipment remain separate layers; wrists carry the held gear.')
proof=proof.replace('<details open>','<details>').replace('<canvas width="192" height="192"></canvas>','<canvas width="128" height="128"></canvas>')
(HERE/'armed-walk.html').write_text(proof)
(ROOT/'Dungeon Master Sample/GOA Armed Walk Pose.html').write_text(proof)
print(json.dumps(dict(clips=len(clips),sourceKeyed=len(source['defs']),arenaVariants=len(aliases),unresolvedAliases=[a['label'] for a in aliases if not a['resolved']])))
