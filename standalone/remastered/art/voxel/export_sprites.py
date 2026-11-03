# Export the game's unit sprites as labelled PNG sheets (python3 export_sprites.py OUTDIR): one
# sheet per .dmi - a row per state, its four facings (S, N, E, W) and animation frames, shown 3x
# with the state names - in the same folder layout as game/Icons/Remastered.
import os, sys
import dmi
from PIL import Image, ImageDraw
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'game', 'Icons', 'Remastered')
FOLDERS = ['Races64', 'Gear64', 'Limbs64', 'Rope64', 'Gear', 'Items']
out = sys.argv[1]; Z = 3
n_files = 0
for top in FOLDERS:
    for root, _, files in os.walk(os.path.join(SRC, top)):
        for fn in sorted(files):
            if not fn.endswith('.dmi'): continue
            try: sts = dmi.load(os.path.join(root, fn))
            except Exception as e: print('skip', fn, e); continue
            if not sts: continue
            w, h = next(iter(sts.values()))['icons'][0].size
            ncol = max(st['dirs'] * min(st['frames'], 8) for st in sts.values())
            LW = 150; CW, CH = w * Z + 6, h * Z + 6
            sheet = Image.new('RGBA', (LW + CW * ncol, 22 + CH * len(sts)), (52, 56, 66, 255)); d = ImageDraw.Draw(sheet)
            d.text((6, 4), os.path.relpath(os.path.join(root, fn), SRC), fill=(255, 255, 255, 255))
            for i, (name, st) in enumerate(sts.items()):
                y = 22 + i * CH
                d.text((6, y + CH // 2 - 6), (name or '(blank)')[:22], fill=(240, 236, 220, 255))
                k = 0
                for f in range(min(st['frames'], 8)):
                    for di in range(st['dirs']):
                        ic = st['icons'][f * st['dirs'] + di].resize((w * Z, h * Z), Image.NEAREST)
                        sheet.alpha_composite(ic, (LW + k * CW + 3, y + 3)); k += 1
            rel = os.path.relpath(root, SRC)
            os.makedirs(os.path.join(out, rel), exist_ok=True)
            sheet.save(os.path.join(out, rel, fn[:-4] + '.png')); n_files += 1
    print(top, 'done', flush=True)
print('sheets:', n_files)
