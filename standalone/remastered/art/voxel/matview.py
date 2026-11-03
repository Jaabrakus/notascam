# Big sprite-vs-3D views for a few loadouts (front sprite, iso right, iso left).
import sys, build3d8, render3
from build3d7 import Loadout
from PIL import Image
OUT = sys.argv[1]
SETS = {'dragon': [Loadout.of('dragon', chest='plate', legs='plate', arms='plate', helmet='crested', shield='heater'),
                   Loadout.of('dragon', chest='scale', legs='scale', arms='plate', helmet='horned', shield='round')],
        'chitin': [Loadout.of('chitin', chest='plate', legs='plate', arms='plate', helmet='crested', shield='heater', weapon='arming sword'),
                   Loadout.of('chitin', chest='plate', legs='plate', arms='plate', helmet='great helm', shield='round', weapon='battle axe')]}
SETS['banded'] = [Loadout.of(t, chest='banded', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='longsword') for t in ('iron', 'gold')]
SETS['lamellar'] = [Loadout.of(t, chest='lamellar', legs='scale', arms='plate', helmet='crested' if t != 'iron' else 'nasal', shield='round', weapon='battle axe' if t != 'bone' else 'spear') for t in ('iron', 'hell')]
SETS['lamellar2'] = [Loadout.of(t, chest='lamellar', legs='scale', arms='plate', helmet='crested', shield='round') for t in ('dragon', 'chitin', 'bone')]
SETS['banded2'] = [Loadout.of(t, chest='banded', legs='plate', arms='plate', helmet='nasal', shield='heater', weapon='arming sword') for t in ('silver', 'diamond', 'hell')]
SETS['mail'] = [Loadout.of('iron', chest='mail', legs='mail', arms='mail', helmet='nasal', shield='heater', weapon='longsword'),
               Loadout.of('gold', chest='mail', legs='mail', arms='mail', helmet='crested', shield='kite', weapon='mace')]
SETS['scale'] = [Loadout.of(t, chest='scale', legs='scale', arms='mail' if t in ('iron', 'gold') else 'plate', helmet='horned', shield='round', weapon='battle axe') for t in ('iron', 'gold')]
SETS['scale2'] = [Loadout.of(t, chest='scale', legs='scale', arms='plate', helmet='horned' if t != 'chitin' else 'crested', shield='round') for t in ('dragon', 'chitin', 'bone')]
def robe(colour, tier='cloth', legs='boots'):
    lo = Loadout.of(tier); f = 'Gear64/Human/%s.dmi' % tier
    lo.chest = (f, 'chest.robe.' + colour); lo.legs = ('Gear64/Human/cloth.dmi', 'legs.' + legs); return lo
SETS['tabard'] = [Loadout.of(t, chest='tabard', legs='mail', arms='mail', helmet='great helm', shield='kite', weapon='mace') for t in ('iron', 'gold')]
SETS['robe'] = [robe('blue'), robe('red'), robe('gold', tier='gold')]
rows = [lo for k in sys.argv[2:] for lo in SETS[k]]
C = 440
img = Image.new('RGBA', (3 * C, len(rows) * C), (52, 56, 66, 255))
for i, lo in enumerate(rows):
    G, full = build3d8.build(lo)
    img.alpha_composite(full['S'].resize((384, 384), Image.NEAREST), (28, i * C + 28))
    for j, y in enumerate([45, 315]):
        img.alpha_composite(render3.render(G, y, 37, scale=5.6, size=C, stretch=1.2, foot=0.88, shadow=True), ((j + 1) * C, i * C))
img.save(OUT)
