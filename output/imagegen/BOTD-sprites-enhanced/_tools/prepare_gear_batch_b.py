from pathlib import Path
import json
import hashlib
from PIL import Image
from validate_dmi import load_asset
from export_sprite_height import native_cell_reference

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
SELECTION = {
 'dragonhide': ['helmet.kettle.dragonhide','chest.leather.dragonhide','legs.leather.dragonhide','arms.leather.dragonhide.L'],
 'gold': ['helmet.great helm.gold','chest.plate.gold','legs.plate.gold','weapon.arming sword.gold'],
 'hell': ['helmet.horned.hell','chest.plate.hell','legs.plate.hell','weapon.arming sword.hell'],
 'iron': ['helmet.great helm.iron','chest.plate.iron','legs.plate.iron','weapon.arming sword.iron'],
 'leather': ['helmet.kettle.leather','chest.leather.leather','legs.leather.leather','shield.round.leather'],
 'magic': ['magic.crystal staff','magic.skull staff','magic.rune sword','magic.void blade'],
 'silver': ['helmet.winged.silver','chest.plate.silver','legs.plate.silver','weapon.arming sword.silver'],
 'spiderfang': ['weapon.dagger.spiderfang','weapon.arming sword.spiderfang','weapon.scimitar.spiderfang','weapon.spear.spiderfang'],
 'spidersilk': ['helmet.kettle.spidersilk','chest.leather.spidersilk','legs.leather.spidersilk','arms.leather.spidersilk.L'],
 'wood': ['helmet.kettle.wood','chest.plate.wood','legs.plate.wood','weapon.arming sword.wood'],
}
MATERIALS = {
 'dragonhide': 'Dark red dragonhide armor, russet scarlet scales and warm orange edge facets; leather silhouettes rather than metal plate. Fourth item is one detached LEFT arm guard, no flesh.',
 'gold': 'Rich warm golden plate with amber shadows, bright pale gold edge facets, dark brown grips; true gold identity rather than yellow cloth.',
 'hell': 'Infernal red and black metal armor with orange ember-like edge facets; horned helmet as in the native source, no added fire particles.',
 'iron': 'Dark neutral iron plate, charcoal shadows and crisp cool steel-gray highlights; restrained utilitarian metal with brown grip.',
 'leather': 'Warm brown leather armor with stitched russet panels and tan edge highlights; final item is a round wooden buckler covered in brown leather.',
 'magic': 'Four different magic equipment classes: violet crystal-tipped staff, bone skull-topped staff, cyan runed longsword, dark violet void blade. Match the shapes and palettes in the native reference; all glow contained inside the object silhouette, no particles.',
 'silver': 'Clean silver plate with cool blue-gray shadows, bright white-silver facets and brown weapon grip. Winged helmet preserves the small lateral silver wings.',
 'spiderfang': 'Pale ivory spiderfang weapons with dark chitin fittings and warm brown grips. Four clearly distinct classes: short pointed dagger, straight arming sword, curved scimitar, long spear. No spider body or loose fangs.',
 'spidersilk': 'Pale cool ivory-gray woven spidersilk armor with slate blue shadows and clean white silk facets; soft cloth construction, not plate. Fourth item one detached LEFT sleeve/bracer, no flesh.',
 'wood': 'Golden brown carved wooden armor and sword with visible restrained wood-grain facets, dark bark shadows and warm tan edges; clearly wood, not bronze or metal.',
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

report = dict(schema_version=1, worker_model='gpt-6.1-sol', generation_mode='builtin_image_gen', status='planned',
              scope='Ten representative base design kits, not animation atlases or runtime equipment overlays',
              complete_source_sheets=False, runtime_installed=False, three_dimensional_conversion=False,
              external_api_used=False, families={})
for family, names in SELECTION.items():
    native = ROOT / 'standalone/remastered/game/Icons/Remastered/Gear64/Human' / (family+'.dmi')
    asset = load_asset(native.read_bytes())
    refs=[]
    canvas=Image.new('RGBA',(1024,1024),(0,0,0,0))
    for quadrant,name in enumerate(names):
        state = next(s for s in asset.metadata.states if json.loads(s.name)==name)
        for cell in range(state.start_cell,state.start_cell+state.directions*state.frames):
            cols=asset.image.width//64;x=(cell%cols)*64;y=(cell//cols)*64
            crop=asset.image.crop((x,y,x+64,y+64))
            if crop.getchannel('A').getbbox(): break
        else: raise ValueError(name+' is empty')
        ref=native_cell_reference(native,cell);ref['quadrant']=quadrant;ref['slug']=name.replace(' ','-').replace('.','-')
        refs.append(ref)
        canvas.alpha_composite(crop.resize((512,512),Image.Resampling.NEAREST),((quadrant%2)*512,(quadrant//2)*512))
    source=BASE/'players-gear/source-art/gear'/family;source.mkdir(parents=True,exist_ok=True)
    destination=BASE/'players-gear/ai-designs/gear'/family;destination.mkdir(parents=True,exist_ok=True)
    reference=source/'native-selected.png';canvas.save(reference)
    prior=BASE/'Gear'/(family+'.png')
    if not prior.exists(): prior=BASE/'Gear'/family/'page-01.png'
    if not prior.exists(): prior=Path('/Users/kiwimango/Downloads/BOTD-sprites/Gear')/(family+'.png')
    prompt=("Use case: stylized-concept. Asset: fantasy game equipment base design kit for later 3D conversion. "
            "Create one genuinely transparent square 2x2 sprite kit with FOUR isolated equipment objects, one centered in each equal quadrant. "
            "Input image 1 is exact native identity and quadrant ordering reference; input image 2 is the family palette/style reference. "
            "Redraw the four selected native objects with the polished enhanced pixel-art treatment: crisp dark contour, deliberate chunky pixels, stepped faceted highlights, readable material texture, clean silhouette. "
            "NO realistic photography, no soft painterly blur. Preserve the selected equipment classes and material identity. "
            + MATERIALS[family] + " Quadrant order: TOP LEFT "+names[0]+"; TOP RIGHT "+names[1]+"; BOTTOM LEFT "+names[2]+"; BOTTOM RIGHT "+names[3]+". "
            "Keep armor front-facing, weapons at the same angle as native source. Objects must be isolated equipment only: empty helmets, detached chest armor, empty paired leg armor, detached weapon/shield/arm guard. "
            "No head, face, wearer, mannequin, hands, skin, human body or feet added. Do not join the armor pieces into a character. "
            "Each complete object fits comfortably inside its own quadrant, 20 percent empty margin from the quadrant edges, wide completely transparent horizontal and vertical central gutters, no object crosses the center lines. "
            "Exactly four objects only. No labels, letters, numbers, watermark, panels, background, cast shadow, floor, checkerboard drawing, particles, extra decorations or loose floating pieces. Preserve true alpha transparency.")
    promptpath=BASE/'_meta/prompts'/('players-gear-b-'+family+'.txt');promptpath.write_text(prompt+'\n')
    report['families'][family]=dict(status='planned', native_source=str(native),native_sha256=sha(native), selected=refs,
         native_reference=str(reference),style_reference=str(prior),prompt=str(promptpath),outputs=[],limitations=['Four selected base designs only; other states and poses are not AI-redrawn.'])
(BASE/'_meta/players-gear-ai-batch-b.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({f:[(r['state_name'],r['cell_index'],r['visible_height']) for r in v['selected']] for f,v in report['families'].items()},indent=2))
