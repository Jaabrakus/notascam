"""Batch reusable sprite-pixel limbs and limb-loss sheets for the existing game.

Default: 15 ground-body families. --all also exports standing hybrid/flying
calibration drafts. No AI API, new anatomy drawing, or fly-off simulation.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REGISTRY=HERE.parent/'armory/bodies.json'
SLOTS={
 'LeftArm':dict(event='Left Arm',g3Parts=['armLu','armLl'],lostBit=2),
 'RightArm':dict(event='Right Arm',g3Parts=['armRu','armRl'],lostBit=1),
 'LeftLeg':dict(event='Left Leg',g3Parts=['legLu','legLl'],lostBit=8),
 'RightLeg':dict(event='Right Leg',g3Parts=['legRu','legRl'],lostBit=4),
}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group()
 g.add_argument('--only',help='Comma-separated body IDs, for example human,orc,dwarf')
 g.add_argument('--all',action='store_true',help='Include all 94 registered appearances; variant/flight masks still need anatomical calibration')
 p.add_argument('--output',type=Path,default=HERE/'pixel-assets')
 p.add_argument('--no-wounds',action='store_true',help='Export pure cutouts without the optional wound overlay')
 p.add_argument('--gallery',action='store_true',help='Rebuild the static asset review page; no new physics demo')
 a=p.parse_args();registry=json.loads(REGISTRY.read_text())
 bodies=registry['bodies']
 if a.only:
  requested=set(a.only.split(','));known={b['id'] for b in bodies}
  if requested-known:p.error('Unknown body IDs: '+','.join(sorted(requested-known)))
  bodies=[b for b in bodies if b['id'] in requested]
 elif not a.all:bodies=[b for b in bodies if b['variant']=='Base' and b['status']!='flight']
 args=[sys.executable,str(HERE/'build_pixel_assets.py'),'--registry',str(REGISTRY),'--output',str(a.output),'--only',','.join(b['id'] for b in bodies)]
 if a.no_wounds:args.append('--no-wounds')
 subprocess.run(args,check=True)
 output=a.output.resolve();proof=json.loads((output/'verification.json').read_text())
 binding=dict(format='goa-existing-game-limb-assets',version=1,frameSize=[64,64],directionOrder=['South','North','East','West'],
  slots=SLOTS,
  existingGame=dict(server='standalone/remastered/game/Code/Creatures/Combats.dm:LimbFling',
   event='standalone/remastered/game/Code/Remastered/Gear3D.dm:RmG3Limb',
   client='standalone/remastered/art/gear3d/game.js:g3hit(limb)',
   physics='standalone/remastered/art/gear3d/ragdoll.js:rdStart(armcut/legcut)',
   bodyStates='standalone/remastered/game/Code/Remastered/Surgery.dm:rm_limb_states',
   blood='standalone/remastered/game/Icons/Blood.dmi (existing pixels and effects retained)'),
  registrationStatus='asset package only; existing runtime still needs updated body/part-map registration',
  missingLimbBitOrders=dict(surgery=['LeftArm','RightArm','LeftLeg','RightLeg'],g3Lost=['RightArm','LeftArm','RightLeg','LeftLeg']),
  bodies=[dict(id=b['id'],raceKey=b['raceKey'],variant=b['variant'],parts=b['id']+'/parts.dmi',
   injured=b['id']+('/injuries.dmi' if a.no_wounds else '/injuries-with-blood.dmi'),
   pureInjury=b['id']+'/injuries.dmi',sourceReference=b['id']+'/normal.png',metadata=b['id']+'/metadata.json') for b in bodies],
  limitations=['Shared cut geometry is a conservative calibration draft; visual review is separate from exact pixel-preservation checks.',
   'Hidden limbs stay empty: the script does not invent unseen artwork.',
   'Cross-race graft attachment/material binding and flight/variant calibration are separate work.',
   'No live game assets or physics code are replaced.'])
 (output/'existing-game-binding.json').write_text(json.dumps(binding,indent=2))
 (output/'README.md').write_text('''# Sprite-pixel limbs and missing-limb bodies

These pieces come from the approved body sprites, sampled once into their 64px fitting space. No replacement limb anatomy is generated. Pure part pixels keep their original RGBA; masking removes exactly those pixels from the body. Wounds are a separate overlay of at most four existing-palette pixels per visible cut. Bone and stone do not receive red blood.

Each body folder contains normal/core references, four source limb layers and masks, 16 canonical missing-limb combinations, optional bloody versions, PNG/DMI atlases, timing/slot metadata and reconstruction proofs. DMI walk playback encodes neutral/step A/neutral/step B. That preserves existing poses; it does not establish full anatomical calibration of every motion frame.

Reuse the existing LimbFling/RmG3Limb/ragdoll path. existing-game-binding.json records the slot names, the different Surgery/G3 bit orders and the existing blood asset. These are asset exports, not a replacement simulation or a completed live-game integration. Updated body textures and their part maps must be registered together when integrating. The classic32px item icon path is separate from these64px body assets.

The default15 base families have a visual cutout review. Other appearances exported with --all remain shared-mask calibration drafts. Pure RGBA reconstruction proves preservation, not correct anatomical segmentation. Original images are never overwritten.
''')
 archive=ROOT/'Dungeon Master Sample/Sprite Limb Assets.zip'
 files={'normal.png','normal.dmi','core.png','parts.png','parts.dmi','part-masks.png',
  'injuries.png','injuries.dmi','metadata.json','proof.json'}
 if not a.no_wounds:files.update({'wound-caps.png','wound-caps.dmi','injuries-with-blood.png','injuries-with-blood.dmi'})
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for b in bodies:
   for file in sorted((output/b['id']).iterdir()):
    if file.is_file() and file.name in files:z.write(file,file.relative_to(output))
  for name in ['README.md','existing-game-binding.json','verification.json','manifest.json']:z.write(output/name,name)
 if a.gallery:subprocess.run([sys.executable,str(HERE/'build.py')],check=True)
 print(json.dumps(dict(bodies=len(bodies),sourceFrames=sum(len(b['sourceRects']) for b in bodies),
  partsViewCells=sum(len(b['sourceRects'])*16 for b in bodies),injuryViewsChecked=proof['injuryViewsChecked'],
  exactRGBAReconstruction=proof['exactRGBAReconstruction'],geometryApproved=False,output=str(output),archive=str(archive))))

if __name__=='__main__':main()
