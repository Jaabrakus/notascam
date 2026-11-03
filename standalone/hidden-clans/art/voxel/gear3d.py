# Sheets of the 3D human in each kind of gear (build3d7), at the game's iso camera.
import sys, importlib, render3
from build3d7 import Loadout
build3d7 = importlib.import_module('build3d8')
build3d7.GEAR = 'Gear64/Human/'
from PIL import Image, ImageDraw, ImageFont
OUT = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/'
BG = (52, 56, 66, 255)
try: font = ImageFont.load_default(size=16)
except TypeError: font = ImageFont.load_default()

def sheet(entries, name, views=(315,), cols=6, cell=300, scale=3.6):
    w = cell * len(views)
    rows = (len(entries) + cols - 1) // cols
    img = Image.new('RGBA', (cols * w, rows * (cell + 24)), BG); d = ImageDraw.Draw(img)
    for i, (label, lo) in enumerate(entries):
        G, _ = build3d7.build(lo)
        x0, y0 = (i % cols) * w, (i // cols) * (cell + 24)
        for j, yaw in enumerate(views):
            img.alpha_composite(render3.render(G, yaw, 37, scale=scale, size=cell, stretch=1.2, foot=0.8, shadow=True), (x0 + j * cell, y0 + 24))
        d.text((x0 + 10, y0 + 4), label, fill=(240, 220, 150), font=font)
        print(label, flush=True)
    img.save(OUT + name)

def knight(**kw):
    base = dict(chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword')
    base.update(kw); tier = base.pop('tier', 'iron')
    return Loadout.of(tier, **base)

which = sys.argv[1:] or ['helmets', 'shields', 'weapons', 'body']
if 'helmets' in which:
    sheet([(h, knight(helmet=h)) for h in ['kettle', 'nasal', 'horned', 'winged', 'great helm', 'crested']], 'gear3d-helmets.png', cols=6)
if 'shields' in which:
    sheet([(s, knight(shield=s)) for s in ['buckler', 'round', 'heater', 'kite', 'tower']], 'gear3d-shields.png', cols=5)
if 'weapons' in which:
    sheet([(w, knight(weapon=w)) for w in ['dagger', 'arming sword', 'longsword', 'scimitar', 'hand axe', 'battle axe',
                                            'warhammer', 'mace', 'morning star', 'spear', 'halberd', 'pickaxe']],
          'gear3d-weapons.png', views=(45, 315), cols=4)
if 'body' in which:
    nb = dict(shield=None, weapon=None)
    e = [('chest ' + c, knight(chest=c, **nb)) for c in ['plate', 'banded', 'mail', 'scale', 'lamellar', 'brigandine', 'tabard']]
    e += [('legs ' + l, knight(legs=l, **nb)) for l in ['mail', 'scale']] + [('arms mail', knight(arms='mail', **nb))]
    e += [('leather', Loadout.of('leather', chest='leather', legs='leather', arms='leather', helmet='kettle', shield='round', weapon=None))]
    lo = Loadout.of('cloth'); lo.chest = (build3d7.GEAR + 'cloth.dmi', 'chest.robe.blue'); lo.legs = (build3d7.GEAR + 'cloth.dmi', 'legs.boots')
    e += [('robe + boots', lo)]
    lo = Loadout.of('cloth'); lo.legs = (build3d7.GEAR + 'cloth.dmi', 'legs.cloth')
    e += [('bare + cloth legs', lo)]
    sheet(e, 'gear3d-body.png', views=(45, 315), cols=5)
if 'tiers' in which:
    import dmi
    R = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Icons/Remastered/' + build3d7.GEAR
    PREF = dict(chest=['plate', 'lamellar', 'leather'], legs=['plate', 'leather'], arms=['plate', 'leather'],
                helmet=['crested', 'horned', 'nasal', 'kettle'], shield=['kite', 'heater', 'round', 'buckler'],
                weapon=['longsword', 'arming sword', 'battle axe', 'hand axe', 'spear'])
    e = []
    for tier in ['iron', 'silver', 'gold', 'diamond', 'adamantium', 'hell', 'dragon', 'chitin', 'bone', 'wood', 'leather']:
        have = set(dmi.load(R + tier + '.dmi'))
        pick = {}
        for slot, names in PREF.items():
            for nm in names:
                st = '%s.%s.%s' % (slot, nm, tier) + ('.L' if slot == 'arms' else '')
                if st in have: pick[slot] = nm; break
        e.append((tier, Loadout.of(tier, **pick)))
    sheet(e, 'gear3d-tiers.png', views=(315,), cols=6)
