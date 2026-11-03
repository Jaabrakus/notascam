"""Pack the drawn side/rear kick and copy exact reflected counterparts."""
from pathlib import Path
import importlib.util
import json
import numpy as np
from PIL import Image, ImageOps

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
spec = importlib.util.spec_from_file_location('curate', ROOT / 'standalone/goa-races/character-retarget/curate_orc_attacks.py')
curate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curate)
image = Image.open(OUT / 'generated-draft.png').convert('RGBA')
palette = curate.palette_from_original()
frames = []
for row in range(2):
    # Select the left column of the generated drawing. The counterpart is copied,
    # not separately regenerated. Crop to pixels with solid alpha.
    crop = image.crop((0, row * image.height // 2, image.width // 2, (row + 1) * image.height // 2))
    mask = np.asarray(crop)[:, :, 3] >= 128
    y, x = np.where(mask)
    crop = crop.crop((int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1))
    if row == 0:
        curate.SCALE = 46 / crop.height
    frame = curate.register(crop, palette)
    mirrored = ImageOps.mirror(frame)
    frames.extend([frame, mirrored])
names = ['side-east', 'side-west', 'rear-kick-right', 'rear-kick-left']
atlas = Image.new('RGBA', (160, 160))
for i, (name, frame) in enumerate(zip(names, frames)):
    frame.save(OUT / (name + '.png'))
    atlas.paste(frame, ((i % 2) * 80, (i // 2) * 80))
atlas.save(OUT / 'short-kick-turnaround.png')
atlas.resize((800, 800), Image.Resampling.NEAREST).save(OUT / 'pixel-preview.png')
assert frames[1].tobytes() == ImageOps.mirror(frames[0]).tobytes()
assert frames[3].tobytes() == ImageOps.mirror(frames[2]).tobytes()
for frame in frames:
    a = np.asarray(frame)
    assert set(np.unique(a[:, :, 3])) <= {0, 255}
    assert not (a[0, :, 3].any() or a[-1, :, 3].any() or a[:, 0, 3].any() or a[:, -1, 3].any())
(OUT / 'manifest.json').write_text(json.dumps({
    'status': 'drawn_pose_review_not_integrated', 'generator': 'built-in image_gen',
    'prompt': 'prompt.txt', 'rawDrawing': 'generated-draft.png', 'cellSize': 80,
    'atlas': 'short-kick-turnaround.png', 'poses': names,
    'rearView': 'newly drawn back view of a sideways kick, not a northward attack',
    'mirroredPairsPixelExact': True, 'filter': 'nearest', 'palette': palette.tolist(),
    'scale': curate.SCALE, 'alpha': 'binary'
}, indent=2) + '\n')
print('Saved four pose cells with pixel-exact mirrored pairs.')
