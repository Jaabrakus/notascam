"""Native image-generation specifications; this file does not create image art."""
from pathlib import Path
import json,argparse
HERE=Path(__file__).resolve().parent
DIRECTIONS=['South','North','East','West']
SETS={
 'arms':['NoLeftArm','NoRightArm','NoArms'],
 'legs':['NoLeftLeg','NoRightLeg','NoLegs','None'],
 'mixedA':['NoRightLegNoLeftArm','NoLeftLegNoRightArm','NoRightArmNoRightLeg','NoLeftArmNoLeftLeg'],
 'mixedB':['NoLegsNoRightArm','NoLegsNoLeftArm','NoArmsNoRightLeg','NoArmsNoLeftLeg'],
 'detached':['LeftArm','RightArm','LeftLeg','RightLeg']}

def plan(race,category):
 rows=SETS[category];detached=category=='detached';stone=race=='Gargoyle';bone=race=='Skeleton'
 blood=('This is STONE: dark grey angular fracture ends, lighter stone flecks, absolutely NO BLOOD or red flesh.' if stone else 'This is a SKELETON: ivory broken-bone ends and dark bone cavities, absolutely NO BLOOD, skin or red flesh.' if bone else 'Keep wound ends tiny and pixel-clustered like the old game: dark burgundy #64212a and #832b37, muted red #9d3d33, sparse bright red #bd0000/#ff0000 accent pixels. Keep the dark outline around the cut. No oversized red circles or painterly pink ends. This is small stylized game injury art, not realistic gore or an anatomical illustration.')
 if race=='Vampire':blood+=' Vampire wounds retain the old dark crimson pixels, but NO dripping blood, sprays, trails or puddles.'
 mapping='Anatomical left/right belongs to the CHARACTER: South/front left is viewer-right; North/back left is viewer-left. Facing East, RIGHT arm and leg are near/visible and LEFT are far/mostly hidden. Facing West, LEFT are near and RIGHT are far. Preserve original far-side occlusion; do not erase a near limb just because the hidden far limb is absent.'
 if detached:
  task='Create matching DETACHED LIMB ITEM assets: only the separate severed limb in each cell, no whole character and no body stump. Row1 LEFT arm with hand; row2 RIGHT arm with hand; row3 LEFT leg with foot; row4 RIGHT leg with foot. Columns show the piece as viewed from South/front, North/back, East/right and West/left. Keep the same limb length, muscle/build, toes/fingers, skin/fur/scales/bone/stone palette, dark outlines and pixel size as the approved body. Each part has a small cut end at the shoulder/upper thigh, with the old game blood pixel language. Keep forearms and upper arms connected; never replace an entire arm with just a hand. No attached torso, no head, no shoulder pad, no weapons, no extra detached parts or blood pool. Center each isolated object in its own equal64-pixel logical cell without enlarging it to the size of a whole body. These are ground item pieces, not graft/prosthetic overlays; do not add stitches or metal.'
 else:
  task='Create INJURED BODY sprites. Preserve image1’s EXACT UPDATED approved race identity, head, ears, hair, proportions, skin, black shorts and pixel shading. Image2 supplies ONLY missing-limb poses, laterality and tiny stump/blood pixels; never copy its obsolete thin body shape. Each row corresponds to the following exact state: '+ '; '.join(f'ROW{i+1}: {state}' for i,state in enumerate(rows))+'. Remove ONLY the limb or limbs named by that state. Any unlisted limb MUST stay intact. For NoArms remove both arms including hands, keep both legs. For NoLegs remove both legs including feet, keep both arms. None means all FOUR limbs absent: head and torso with shorts remain. Missing limbs must actually be ABSENT; do not merely paint blood over an intact limb, hide it behind the torso, keep a ghost hand, or regrow it. Small cut surfaces sit at the correct shoulder/thigh boundary. Preserve each original source facing and standing pose. Keep source body registration so the injured torso/head occupies the same relative cell space as the intact body. No head loss and no new poses.'
 prompt=f'''Use case: identity-preserve / game-sprite asset generation. Race: {race}. Input1 is the UPDATED APPROVED body to match. Input2 is an OLD source guide for injury/limb details only; input3 when present is the old blood/stone pixel reference.
{task}
{mapping}
{blood}
Output EXACTLY FOUR COLUMNS by {len(rows)} ROWS, {len(rows)*4} distinct cells, direction order SOUTH, NORTH, EAST, WEST in every row. Equal cell grid with complete sprites and transparent separator margins; constant race scale across all rows, no touching adjacent cells. Crisp clustered PIXEL ART, match the input1 pixel cluster size and chunky dark outline; no smooth vector shapes or blurred miniature painting. Real transparent background. No labels, letters, frame borders, grid lines, scenery or cast shadows. No color-key background. Do not add normal/intact reference rows or extra subjects. This is a static pose/asset sheet, not a walk animation.''' 
 source=HERE/'references'/f'{race}-{category}-source.png' if not detached else HERE/'references'/f'{race}-self-graft-source.png'
 if race=='Elf' and detached:source=HERE/'references/Human-self-graft-source.png'
 refs=[str(HERE/'references'/f'{race}-approved-body.png'),str(source)]
 if detached:refs.append(str(HERE/'references/blood-and-stone-source.png'))
 return dict(id=f'{race}-{category}',race=race,category='detached' if detached else 'injury',label=f'{race} · {category}',path=str(HERE/'generated'/f'{race}-{category}-v1.png'),columns=4,rows=len(rows),rowLabels=rows,directionOrder=DIRECTIONS,status='draft',prompt=prompt,references=refs)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('race');p.add_argument('--sets',default=','.join(SETS));a=p.parse_args();print(json.dumps([plan(a.race,k) for k in a.sets.split(',')],ensure_ascii=False))
