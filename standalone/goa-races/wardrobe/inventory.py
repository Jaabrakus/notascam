"""Inventory every original GOA wearable overlay and available color artwork.

Reads source definitions and PNG/DMI metadata only; never edits GOA source files.
"""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re

from PIL import Image

HERE = Path(__file__).resolve().parent
GOA = Path('/Users/kiwimango/Downloads/GOA Source')
SHARED = GOA / 'code/_shared/items.dm'
ITEMS = GOA / 'code/game/Items.dm'
NEW = GOA / 'code/game/items_new.dm'
FACTION = GOA / 'code/game/faction_chuunin_items.dm'


def uncomment(text):
    text = re.sub(r'/\*.*?\*/', lambda match: '\n' * match[0].count('\n'), text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def nodes(path):
    """Read simple object declarations/fields, skipping procedure bodies."""
    stack, output, skip = [], {}, None
    for line_number, line in enumerate(uncomment(path.read_text()).splitlines(), 1):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip('\t'))
        stripped = line.strip()
        if skip is not None:
            if indent > skip:
                continue
            skip = None
        if '(' in stripped and re.match(r'^(?:proc/|verb/)?\w+(?:/\w+)*\(', stripped):
            skip = indent
            continue
        declaration = re.fullmatch(r'/?[A-Za-z_]\w*(?:/[A-Za-z_]\w*)*', stripped)
        if declaration:
            while stack and stack[-1][0] >= indent:
                stack.pop()
            name = stripped.strip('/')
            key = '/' + name if not stack else stack[-1][1] + '/' + name
            stack.append((indent, key))
            output.setdefault(key, dict(type=key, file=str(path), line=line_number))
            continue
        if not stack:
            continue
        match = re.match(r'^(icon|icon_state|itm|cat|armor|overlay_type|code)\s*=\s*(.*)$', stripped)
        if match:
            value = match[2].strip()
            output[stack[-1][1]][match[1]] = value.strip("'\"")
    return output


def metadata(path):
    with Image.open(path) as image:
        desc = image.info.get('Description', '')
        def number(text, key, default):
            match = re.search(r'^\s*' + key + r'\s*=\s*(\d+)', text, re.M)
            return int(match[1]) if match else default
        width, height = number(desc, 'width', 32), number(desc, 'height', 32)
        states, offset = [], 0
        for block in re.split(r'(?=^state\s*=)', desc, flags=re.M)[1:]:
            state = dict(name=re.search(r'^state\s*=\s*"(.*?)"', block, re.M)[1],
                         offset=offset, dirs=number(block, 'dirs', 1),
                         frames=number(block, 'frames', 1), movement=number(block, 'movement', 0))
            states.append(state)
            offset += state['dirs'] * state['frames']
        blank = [state for state in states if state['name'] == '' and state['dirs'] >= 4]
        selected = next((state for state in blank if state['movement'] == 0), blank[0] if blank else None)
        if selected is None:
            selected = next((state for state in states if state['dirs'] >= 4), None)
        return dict(width=width, height=height, columns=image.width // width,
                    states=states, standing=selected, animated=any(s['frames'] > 1 and s['dirs'] >= 4 for s in states))


def category(path):
    rel = path.relative_to(GOA).as_posix()
    name = path.stem.lower()
    if rel.startswith('armor/'):
        return 'Armor sets'
    if rel.startswith('trench/'):
        return 'Trench coats'
    if rel.startswith('cloak/'):
        return 'Cloaks'
    if rel.startswith('jacket/'):
        return 'Jackets'
    if rel.startswith('members/'):
        return 'Member outfits' if 'mask' not in name else 'Masks'
    if 'shirt_sleeves' in rel:
        return 'Long-sleeved shirts'
    if name.startswith('shirt'):
        return 'Shirts'
    if name.startswith('pants'):
        return 'Pants'
    if 'headband' in name:
        return 'Headbands'
    if 'mask' in name:
        return 'Masks'
    if 'chuunin' in name:
        return 'Vests'
    if name.startswith('hokage_armor'):
        return 'Hokage armor'
    if name == 'anbu':
        return 'Armor'
    if name == 'sasuke_cloth':
        return 'Full outfits'
    if name == 'fishnet':
        return 'Undershirts'
    return 'Accessories'


def label(path):
    rel = path.relative_to(GOA).as_posix()
    stem = path.stem
    special = {'anbu': 'ANBU armor', 'sasuke_cloth': 'Sasuke clothes',
               'FaceBandage1': 'Face bandage', 'Kunai_Holster': 'Kunai holster',
               'arm_guards': 'Arm guards', 'fishnet': 'Fishnet undershirt',
               'armtape_left': 'Arm tape · left', 'armtape_right': 'Arm tape · right',
               'Dans_Cloak': "Dan's / Fourth cloak", 'Konoha Cloak': 'Konoha / Naruto cloak',
               'Hebi Cloak': 'Hebi cloak', 'Neji_Shippuden': 'Neji Shippuden outfit',
               'tobi_mask': 'Tobi mask', 'chuunin-vest': 'Chuunin vest · Leaf',
               'chuunin-vest_sand': 'Chuunin vest · Sand', 'chuunin-vest_mist': 'Chuunin vest · Mist',
               'ourico-ame-chuunin': 'Chuunin vest · Ourico Ame',
               'mange-sound-chuunin': 'Chuunin vest · Mange Sound'}
    if stem in special:
        return special[stem]
    families = [('armor_body', 'Armor body + shoulders'), ('shirt_sleeves', 'Long-sleeved shirt'),
                ('hokage_armor', 'Hokage armor'), ('trench', 'Trench coat'), ('jacket', 'Jacket'),
                ('cloak', 'Cloak'), ('pants', 'Pants'), ('shirt', 'Shirt'), ('kmask', 'Kakashi mask')]
    colors = {'': 'Black', 'dred': 'Dark red', 'dblue': 'Dark blue', 'dgreen': 'Dark green',
              'darkblue': 'Dark blue', 'darkred': 'Dark red', 'darkorange': 'Dark orange',
              'darkgreen': 'Dark green', 'lightblue': 'Light blue', 'lightred': 'Light red',
              'lightorange': 'Light orange', 'lightgrey': 'Light grey', 'lightbrown': 'Light brown'}
    for prefix, family in families:
        if stem.startswith(prefix):
            value = stem[len(prefix):].strip('_')
            return family + ' · ' + colors.get(value, value.replace('_', ' ').title())
    return stem.replace('_', ' ').replace('-', ' ').title()


def build_inventory():
    shared, old_items, new_items, faction = nodes(SHARED), nodes(ITEMS), nodes(NEW), nodes(FACTION)
    overlays = {key: value for key, value in shared.items() if value.get('icon') and key != '/obj/member'}
    overlays.update({key: value for key, value in faction.items() if key.startswith('/obj/faction_chuunin/') and value.get('icon')})
    active_by_source, active_by_overlay = defaultdict(list), defaultdict(list)
    for node in old_items.values():
        if node['type'].startswith('/obj/items/equipable/') and node.get('icon'):
            active_by_source[node['icon']].append(node['type'])
    for node in new_items.values():
        if node['type'].startswith('/obj/items/equipable/newsys/') and node.get('itm'):
            active_by_overlay[node['itm']].append(node['type'])
    for node in faction.values():
        if node['type'].startswith('/obj/items/equipable/') and node.get('overlay_type'):
            active_by_overlay[node['overlay_type']].append(node['type'])
    for color in ['blue', 'red', 'black']:
        active_by_overlay['/obj/headband/' + color].append('/obj/items/equipable/Headband/' + color.title())
    by_source = defaultdict(list)
    for key, node in overlays.items():
        path = GOA / node['icon']
        if path.exists():
            by_source[path.resolve()].append(node)
    # All files in wardrobe families are included, even if not offered by an active item.
    candidates = set(by_source)
    for folder in ['armor', 'cloak', 'jacket', 'trench', 'members', 'icons/shirt_sleeves']:
        candidates.update(path.resolve() for path in (GOA / folder).glob('*.dmi'))
    prefixes = ['shirt', 'pants', 'kmask', 'anbumask', 'hokage_armor', 'chuunin-vest']
    for path in (GOA / 'icons').glob('*.dmi'):
        if any(path.stem.startswith(prefix) for prefix in prefixes) or path.name in {
            'blueheadband.dmi', 'redheadband.dmi', 'blackheadband.dmi', 'FaceBandage1.dmi',
            'Kunai_Holster.dmi', 'arm_guards.dmi', 'fishnet.dmi', 'armtape_left.dmi',
            'armtape_right.dmi', 'anbu.dmi', 'sasuke_cloth.dmi'}:
            candidates.add(path.resolve())
    entries, consumed, missing = [], set(), []
    for path in sorted(candidates):
        if path in consumed or path.stem.startswith('armor_sholders'):
            continue
        sources = [path]
        if path.parent.name == 'armor' and path.stem.startswith('armor_body'):
            shoulder = path.with_name(path.name.replace('armor_body', 'armor_sholders'))
            if shoulder.exists():
                sources.append(shoulder)
        consumed.update(sources)
        descriptors = [metadata(source) for source in sources]
        if any(desc['standing'] is None for desc in descriptors):
            missing.append(dict(source=str(path), reason='No directional on-body state found.'))
            continue
        refs = [node for source in sources for node in by_source.get(source, [])]
        gameplay = sorted(set(item for source in sources for item in active_by_source[source.relative_to(GOA).as_posix()]) |
                          set(item for node in refs for item in active_by_overlay[node['type']]))
        notes = []
        if len(sources) == 2:
            notes.append('Body and matching shoulder overlay composed together; game equips them separately.')
        if path.stem.startswith('hokage_armor'):
            notes.append('Overlay object and artwork exist; old item definitions are inside a commented-out block.')
        if not gameplay:
            notes.append('Available wardrobe artwork/overlay; no active equipable item reference established.')
        slug = re.sub(r'[^a-z0-9]+', '-', path.relative_to(GOA).with_suffix('').as_posix().lower()).strip('-')
        entry = dict(id=slug, label=label(path), category=category(path), sources=[str(source) for source in sources],
                     state=descriptors[0]['standing']['name'], movement=descriptors[0]['standing']['movement'],
                     gameplayItem=gameplay, overlayTypes=[node['type'] for node in refs],
                     availability='gameplay' if gameplay else 'asset-only', notes=notes,
                     animated=all(desc['animated'] for desc in descriptors),
                     sourceMetadata=[dict(width=desc['width'], height=desc['height'], columns=desc['columns'],
                                          standing=desc['standing'], states=desc['states']) for desc in descriptors])
        entries.append(entry)
    counts = Counter(entry['category'] for entry in entries)
    return dict(version=1, sourceRoot=str(GOA), entries=entries,
                summary=dict(entries=len(entries), sourceFiles=sum(len(entry['sources']) for entry in entries),
                             gameplayEntries=sum(entry['availability'] == 'gameplay' for entry in entries),
                             assetOnlyEntries=sum(entry['availability'] == 'asset-only' for entry in entries),
                             categories=dict(sorted(counts.items()))),
                exclusions=[dict(reason='Character bodies, hair and eye palettes are not clothing.', examples=['icons/base_m1.dmi', 'icons/hair1.dmi', 'icons/eye colors.dmi']),
                            dict(reason='Held weapons and combat effects are outside a wardrobe inventory.', examples=['sword1/swordover.dmi', 'icons/sandarmor.dmi', 'icons/shield.dmi']),
                            dict(reason='GUI equipped markers, map pins, NPC sprites and scenery are not wearable overlays.', examples=['icons/Equipped.dmi', 'icons/pins.dmi', 'icons/Haku.dmi', 'icons/Gaara.dmi', 'icons/black.dmi'])],
                unresolved=missing,
                definitions=[str(path) for path in [SHARED, ITEMS, NEW, FACTION, GOA / 'code/game/itemsystem.dm']])


def main():
    data = build_inventory()
    (HERE / 'inventory.json').write_text(json.dumps(data, indent=2))
    print(json.dumps(data['summary']))
    if data['unresolved']:
        print('Unresolved: ' + json.dumps(data['unresolved']))


if __name__ == '__main__':
    main()
