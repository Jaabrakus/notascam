"""Describe the existing approved bodies without repainting or inventing poses.

All rectangles are source pixels. Direction order is South, North, East, West.
Variant rows are separate standing designs, never consecutive animation frames.
"""
from pathlib import Path
import hashlib
import json
import shutil
from functools import lru_cache

from PIL import Image

HERE = Path(__file__).resolve().parent
RACES = HERE.parent
GENERATED = Path('/Users/kiwimango/.codex/generated_images/01a188c3-defe-7953-82be-476bc059c649')
DIRECTIONS = ['South', 'North', 'East', 'West']
VARIANTS = ['Possessed1', 'Possessed2', 'Marked', 'Ashen', 'Hellblooded', 'Werewolf', 'Zombie']
BASES = {
    'Human': ('human', 'Human', 56),
    'HumanBlack': ('human-dark', 'Human · dark skin', 56),
    'Dwarves': ('dwarf', 'Dwarf', 46),
    'Elf': ('elf', 'Elf · blond', 59),
    'Night Elf': ('dark-elf', 'Dark Elf', 59),
    'Orc': ('orc', 'Orc', 57),
    'Goblins': ('goblin', 'Goblin', 43),
    'Kobold': ('kobold', 'Kobold', 45),
    'Vampire': ('vampire', 'Vampire', 56),
    'VampireFly': ('vampire-flying', 'Vampire · flying', 60),
    'Demon': ('demon', 'Demon', 57),
    'DemonFly': ('demon-flying', 'Demon · flying', 61),
    'Gargoyle': ('gargoyle', 'Gargoyle', 57),
    'GargoyleFly': ('gargoyle-flying', 'Gargoyle · flying', 61),
    'FrogMan': ('frogman', 'Frogman', 52),
    'LizardMan': ('lizardman', 'Lizardman', 56),
    'DevourerZombie': ('devourer-zombie', 'Devourer zombie', 56),
    'Skeleton': ('skeleton', 'Skeleton', 56),
}
# Explicit identity verified against the finished images before registration.
# These are exact copies of the native generated PNGs; no crop or alpha edit.
UPDATED_WALKS = {
    'Human': 'exec-a8059fa3-8674-4ab9-8554-20bbf64482dc.png',
    'Dwarves': 'exec-446794e5-2002-4237-821d-fba5ca1a5a4e.png',
    'Night Elf': 'exec-65943ae9-2e84-4730-ad8d-086bdbe52ac0.png',
    'Orc': 'exec-f63456da-577e-4927-bf13-ef5e65baf448.png',
    'Goblins': 'exec-35aa1f12-8f96-44eb-980f-0dec422c5fb6.png',
    'Elf': 'exec-938d4aad-b110-4992-9eb4-fcdcf4762287.png',
    'Kobold': 'exec-3996e062-0735-4a5a-bdb2-d9923b7a7322.png',
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserve_walks():
    directory = HERE / 'body-sources'
    directory.mkdir(exist_ok=True)
    provenance = []
    for race, filename in UPDATED_WALKS.items():
        original = GENERATED / filename
        target = directory / (race + '-walk.png')
        if not target.exists():
            shutil.copyfile(original, target)
        if sha256(original) != sha256(target):
            raise ValueError('Refusing to replace a different body source: ' + str(target))
        provenance.append(dict(race=race, original=str(original), saved=str(target),
                               sha256=sha256(target), operation='byte-for-byte copy'))
    (directory / 'provenance.json').write_text(json.dumps(provenance, indent=2))


def bounds_for(image, rect):
    x, y, width, height = rect
    if any(int(v) != v for v in rect):
        raise ValueError('Expected integral body cell boundaries: ' + str(rect))
    if x < 0 or y < 0 or x + width > image.width or y + height > image.height:
        raise ValueError('Body source rectangle exceeds image bounds.')
    alpha = image.crop((x, y, x + width, y + height)).getchannel('A')
    bounds = alpha.point(lambda value: 255 if value >= 128 else 0).getbbox()
    if not bounds:
        raise ValueError('Empty body source cell: ' + str(rect))
    return list(bounds)


def projection_bands(active, expected, label):
    """Keep narrow real row gaps: native sheets can have only two clear pixels."""
    bands, start = [], None
    for index, occupied in enumerate(active + [False]):
        if occupied and start is None:
            start = index
        if not occupied and start is not None:
            if index - start >= 4:
                bands.append([start, index])
            start = None
    if len(bands) != expected:
        raise ValueError(f'{label}: detected {len(bands)} sprite bands, expected {expected}; manual segmentation required')
    return bands


@lru_cache(maxsize=64)
def measured_grid(source, columns, rows):
    """Infer source cell separators from the artwork, never from prompt claims."""
    image = Image.open(source).convert('RGBA')
    alpha = image.getchannel('A')
    row_active = [sum(value >= 128 for value in alpha.crop((0, y, image.width, y + 1)).getdata()) > 5
                  for y in range(image.height)]
    bands = projection_bands(row_active, rows, str(source) + ' rows')
    row_cuts = [0] + [(bands[i][1] + bands[i + 1][0]) // 2 for i in range(rows - 1)] + [image.height]
    rectangles = []
    for row, (top, bottom) in enumerate(bands):
        col_active = [sum(value >= 128 for value in alpha.crop((x, top, x + 1, bottom)).getdata()) > 2
                      for x in range(image.width)]
        col_bands = projection_bands(col_active, columns, str(source) + f' row {row} columns')
        col_cuts = [0] + [(col_bands[i][1] + col_bands[i + 1][0]) // 2 for i in range(columns - 1)] + [image.width]
        rectangles.append([[col_cuts[view], row_cuts[row], col_cuts[view + 1] - col_cuts[view],
                            row_cuts[row + 1] - row_cuts[row]] for view in range(columns)])
    return rectangles, bands


def describe(race, source, *, variant='Base', columns=4, rows=3,
             row=0, frames=3, status='walk', base_id=None):
    source = Path(source).resolve()
    base, label, height = BASES[race]
    image = Image.open(source).convert('RGBA')
    grid, row_bands = measured_grid(str(source), columns, rows)
    rects = [grid[row + frame] for frame in range(frames)]
    bounds = [[bounds_for(image, rect) for rect in frame] for frame in rects]
    union = [[min(frame[view][0] for frame in bounds), min(frame[view][1] for frame in bounds),
              max(frame[view][2] for frame in bounds), max(frame[view][3] for frame in bounds)]
             for view in range(4)]
    if status == 'walk':
        animation = dict(kind='walk', sequence=[0, 1, 0, 2], delaysMs=[200, 200, 200, 200])
    elif status == 'flight':
        animation = dict(kind='flight', sequence=[0, 1], delaysMs=[200, 200])
    else:
        animation = dict(kind='standing', sequence=[0], delaysMs=[200])
    identifier = base if variant == 'Base' else base + '-' + variant.lower()
    edge_contacts = []
    for frame_index, frame in enumerate(rects):
        for view, rect in enumerate(frame):
            b = bounds[frame_index][view]
            if rect[0] + b[0] == 0 or rect[1] + b[1] == 0 or rect[0] + b[2] == image.width or rect[1] + b[3] == image.height:
                edge_contacts.append(dict(frame=frame_index, view=view))
    return dict(id=identifier, label=label if variant == 'Base' else label + ' · ' + variant,
                raceKey=race, baseId=base_id or base, variant=variant, status=status,
                source=str(source), sourceSha256=sha256(source), sourceSize=list(image.size),
                sourceRects=rects, frameBounds=bounds, unionBounds=union,
                targetHeight=height, layout=dict(columns=columns, rows=rows, row=row,
                frames=frames, directions=DIRECTIONS), animation=animation,
                segmentation=dict(method='alpha128 projection bands with separator cuts',
                                  rowBands=row_bands, equalCellsAssumed=False),
                normalization=dict(referenceHeight=max(b[3] - b[1] for frame in bounds for b in frame),
                                   centerX=32, footY=61),
                qualityFlags=['source edge contact; inspect original clipping'] if edge_contacts else [],
                sourceEdgeContacts=edge_contacts,
                artStatus='generated draft; body animation and gear fitting need visual review')



def refresh_human_sources(bodies):
    """Use the corrected canonical 64px atlases instead of historical snapshot sources."""
    result=[]
    for body in bodies:
        race=body['raceKey'];kind='base' if body['variant']=='Base' else body['variant']
        source=RACES/'hybrids/packed'/race/kind/'sprites.png'
        if race not in ['Human','HumanBlack'] or not source.exists():
            result.append(body);continue
        b=dict(body);im=Image.open(source).convert('RGBA')
        assert im.size==(256,192)
        rects=[[[v*64,r*64,64,64] for v in range(4)] for r in range(3)]
        bounds=[[bounds_for(im,rect) for rect in row] for row in rects]
        b.update(source=str(source.resolve()),sourceSha256=sha256(source),sourceSize=[256,192],sourceRects=rects,frameBounds=bounds,
                 unionBounds=[[min(f[v][0] for f in bounds),min(f[v][1] for f in bounds),max(f[v][2] for f in bounds),max(f[v][3] for f in bounds)] for v in range(4)],
                 status='walk',layout=dict(columns=4,rows=3,row=0,frames=3,directions=DIRECTIONS),animation=dict(kind='walk',sequence=[0,1,0,2],delaysMs=[200]*4),
                 normalization=dict(referenceHeight=max(x[3]-x[1] for f in bounds for x in f),centerX=32,footY=61),
                 segmentation=dict(method='canonical 64px cells',equalCellsAssumed=True),sourceEdgeContacts=[],qualityFlags=[],artStatus='Corrected male Human sheet; equipment fitting preview')
        result.append(b)
    return result


def build_bodies():
    preserve_walks()
    bodies = []
    remaining = {item['race']: Path(item['path']) / 'result.png' for item in
                 json.loads((RACES / 'sprite-engine/remaining-races-jobs.json').read_text())}
    for race in BASES:
        if race in UPDATED_WALKS:
            bodies.append(describe(race, HERE / 'body-sources' / (race + '-walk.png')))
        else:
            path = remaining[race]
            if not path.is_file():
                raise FileNotFoundError(path)
            flying = race.endswith('Fly')
            bodies.append(describe(race, path, rows=2 if flying else 3,
                                   frames=2 if flying else 3, status='flight' if flying else 'walk'))
    for race in ['Human', 'HumanBlack', 'Dwarves', 'Elf', 'Night Elf', 'Orc',
                 'Goblins', 'Kobold', 'FrogMan', 'LizardMan']:
        path = RACES / 'hybrids/sheets' / (race + '.png')
        for row, variant in enumerate(VARIANTS):
            bodies.append(describe(race, path, variant=variant, rows=7, row=row,
                                   frames=1, status='standing_only'))
    path = RACES / 'hybrids/sheets/Gargoyle-eyes.png'
    for row, (race, variant) in enumerate([
        ('Gargoyle', 'Amber'), ('Gargoyle', 'Ice'), ('Gargoyle', 'Red'),
        ('GargoyleFly', 'Amber'), ('GargoyleFly', 'Ice'), ('GargoyleFly', 'Red')]):
        bodies.append(describe(race, path, variant=variant, rows=6, row=row,
                               frames=1, status='standing_only'))
    if len({body['id'] for body in bodies}) != len(bodies):
        raise ValueError('Duplicate body registry identifier.')
    bodies=refresh_human_sources(bodies)
    return dict(version=1, coordinates='64-pixel fitting space; feet normally y=61',
                sourceCoordinates='sourceRects are absolute PNG pixels; bounds are cell-relative',
                directions=DIRECTIONS, bodies=bodies,
                summary=dict(total=len(bodies), walks=sum(b['status'] == 'walk' for b in bodies),
                             flights=sum(b['status'] == 'flight' for b in bodies),
                             standingOnly=sum(b['status'] == 'standing_only' for b in bodies)))


def main():
    value = build_bodies()
    (HERE / 'bodies.json').write_text(json.dumps(value, indent=2))
    print(json.dumps(value['summary']))


if __name__ == '__main__':
    main()
