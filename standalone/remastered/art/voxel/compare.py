# Side by side: the original sprite (front and side facing) next to the 3D model seen from the
# same direction with no camera tilt, at the same scale and place (4 screen pixels per sprite
# pixel), then the 3D at the game's two iso corners. Usage: python3 compare.py [set ...]
import sys, importlib, render3
from build3d7 import Loadout
from PIL import Image, ImageDraw, ImageFont
build = importlib.import_module('build3d8')
OUT = '/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/art/out/'
BG = (52, 56, 66, 255); K = 4; C = 64 * K
font = ImageFont.load_default(size=18); small = ImageFont.load_default(size=14)

def L(tier, **kw): return Loadout.of(tier, **kw)
SETS = {
    'knights': [('iron plate knight', L('iron', chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword')),
                ('gold scale, horned, battle axe', L('gold', chest='scale', legs='mail', arms='mail', helmet='horned', shield='round', weapon='battle axe')),
                ('iron tabard, great helm, mace', L('iron', chest='tabard', legs='mail', arms='mail', helmet='great helm', shield='kite', weapon='mace')),
                ('leather, kettle, round', L('leather', chest='leather', legs='leather', arms='leather', helmet='kettle', shield='round')),
                ('hell lamellar, winged, hammer', L('hell', chest='lamellar', legs='scale', arms='plate', helmet='winged', shield='tower', weapon='warhammer')),
                ('silver brigandine, crested, spear', L('silver', chest='brigandine', legs='plate', arms='mail', helmet='crested', shield='buckler', weapon='spear'))],
}
iron = dict(chest='plate', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword')
def var(**kw):
    d = dict(iron); d.update(kw); t = d.pop('tier', 'iron'); return L(t, **d)
SETS['helmets'] = [(h, var(helmet=h)) for h in ['kettle', 'nasal', 'horned', 'winged', 'great helm', 'crested']]
SETS['shields'] = [(s_, var(shield=s_)) for s_ in ['buckler', 'round', 'heater', 'kite', 'tower']]
SETS['weapons1'] = [(w, var(weapon=w)) for w in ['dagger', 'arming sword', 'longsword', 'scimitar', 'hand axe', 'battle axe']]
SETS['weapons2'] = [(w, var(weapon=w)) for w in ['warhammer', 'mace', 'morning star', 'spear', 'halberd', 'pickaxe']]
SETS['chests'] = [('chest ' + c_, var(chest=c_, shield=None, weapon=None)) for c_ in ['plate', 'banded', 'mail', 'scale', 'lamellar', 'brigandine', 'tabard']]
_robe = L('cloth'); _robe.chest = ('Gear64/Human/cloth.dmi', 'chest.robe.blue'); _robe.legs = ('Gear64/Human/cloth.dmi', 'legs.boots')
SETS['chests'] += [('leather', L('leather', chest='leather', legs='leather', arms='leather')), ('robe', _robe)]

TIERS = ['iron', 'silver', 'gold', 'diamond', 'adamantium', 'hell', 'dragon', 'chitin', 'bone', 'wood', 'leather']
def tier_set(tier):
    import dmi
    have = set(dmi.load('/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Icons/Remastered/Gear64/Human/' + tier + '.dmi'))
    PREF = dict(chest=['plate', 'scale', 'lamellar', 'leather'], legs=['plate', 'scale', 'leather'], arms=['plate', 'leather'],
                helmet=['nasal', 'crested', 'horned', 'kettle'], shield=['heater', 'kite', 'round', 'buckler'],
                weapon=['longsword', 'arming sword', 'battle axe', 'hand axe', 'spear'])
    pick = {}
    for slot, names in PREF.items():
        for nm in names:
            if '%s.%s.%s' % (slot, nm, tier) + ('.L' if slot == 'arms' else '') in have: pick[slot] = nm; break
    return (tier + ': ' + ', '.join(pick[k] for k in ('chest', 'helmet', 'shield', 'weapon') if k in pick), L(tier, **pick))
SETS['tiers1'] = [tier_set(t) for t in TIERS[:6]]
SETS['tiers2'] = [tier_set(t) for t in TIERS[6:]]

def legs_set(kind, tier='iron'):
    lo = L(tier, chest='plate', arms='plate', helmet={'dragon': 'crested', 'chitin': 'crested'}.get(tier, 'nasal'))
    lo.legs = ('Gear64/Human/cloth.dmi', 'legs.' + kind) if kind in ('cloth', 'boots') else \
              ('Gear64/Human/leather.dmi', 'legs.leather.leather') if kind == 'leather' else ('Gear64/Human/%s.dmi' % tier, 'legs.%s.%s' % (kind, tier))
    return ('legs ' + kind + ('' if tier == 'iron' else ' ' + tier), lo)
SETS['legs'] = [legs_set(k) for k in ('plate', 'mail', 'scale', 'leather', 'cloth', 'boots')]
SETS['legs2'] = [legs_set('plate', 'gold'), legs_set('scale', 'dragon'), legs_set('plate', 'chitin'), legs_set('mail', 'silver')]

def sheet(name, entries):
    heads = ['sprite front', '3D front', 'sprite side', '3D side', '3D iso right', '3D iso left']
    W = C * len(heads); rowh = C + 40
    img = Image.new('RGBA', (W, 30 + rowh * len(entries)), BG); d = ImageDraw.Draw(img)
    for j, h in enumerate(heads): d.text((j * C + 8, 6), h, fill=(200, 200, 210), font=small)
    for i, (label, lo) in enumerate(entries):
        G, full = build.build(lo)
        y0 = 30 + i * rowh
        d.text((8, y0 + 4), label, fill=(240, 220, 150), font=font)
        cells = [full['S'].resize((C, C), Image.NEAREST),
                 render3.render(G, 0, 0, scale=K, size=C, stretch=1.0, foot=1.0),
                 full['E'].resize((C, C), Image.NEAREST),
                 render3.render(G, 90, 0, scale=K, size=C, stretch=1.0, foot=1.0),
                 render3.render(G, 45, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True),
                 render3.render(G, 315, 37, scale=K * 0.9, size=C, stretch=1.2, foot=0.86, shadow=True)]
        for j, c in enumerate(cells):
            if j in (0, 2):
                bg = Image.new('RGBA', (C, C), (60, 64, 76, 255)); bg.alpha_composite(c); c = bg
            img.alpha_composite(c, (j * C, y0 + 32))
        print(label, flush=True)
    img.save(OUT + 'compare-' + name + '.png')

for name in (sys.argv[1:] or list(SETS)):
    sheet(name, SETS[name])
