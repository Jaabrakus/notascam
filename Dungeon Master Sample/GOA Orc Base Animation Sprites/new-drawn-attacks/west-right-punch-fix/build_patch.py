"""Copy the newly drawn arm region into the accepted impact frame."""
from pathlib import Path
import importlib.util
import json
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('curate', ROOT / 'standalone/goa-races/character-retarget/curate_orc_attacks.py')
curate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curate)
old = Image.open(HERE / 'before/punch_right-west-2.png').convert('RGBA')
raw = Image.open(HERE / 'generated-draft.png').convert('RGBA')
a = np.asarray(raw)
y, x = np.where(a[:, :, 3] >= 128)
raw = raw.crop((int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1))
height = Image.open(curate.OUT / 'selected-source-poses/punch_right-west-2.png').height
raw = raw.resize((round(raw.width * height / raw.height), height), Image.Resampling.NEAREST)
new = curate.register(raw, curate.palette_from_original())

def eye_position(image):
    a = np.asarray(image).astype(int)
    y, x = np.where((a[:, :, 0] > 120) & (a[:, :, 1] < 40) & (a[:, :, 3] > 128))
    return np.array([x.mean(), y.mean()])

offset = np.rint(eye_position(old) - eye_position(new)).astype(int)
aligned = Image.new('RGBA', old.size)
aligned.paste(new, tuple(offset))
mask = Image.new('L', old.size)
draw = ImageDraw.Draw(mask)
draw.rectangle((0, 40, 79, 58), fill=255)
# Keep the approved head, including its face and outline, pixel-for-pixel.
draw.polygon([(34, 20), (65, 20), (65, 32), (47, 45), (38, 45), (32, 39), (32, 29)], fill=0)
fixed = Image.composite(aligned, old, mask)
fixed.save(HERE / 'impact-native.png')
mask.save(HERE / 'arm-edit-mask.png')
outside = np.asarray(mask) == 0
assert np.array_equal(np.asarray(old)[outside], np.asarray(fixed)[outside])
preview = Image.new('RGBA', (800, 400))
preview.paste(old.resize((400, 400), Image.Resampling.NEAREST), (0, 0))
preview.paste(fixed.resize((400, 400), Image.Resampling.NEAREST), (400, 0))
preview.save(HERE / 'before-after.png')
(HERE / 'patch.json').write_text(json.dumps({'frame': 'punch_right-west-2', 'offset': offset.tolist(),
    'changedPixels': int(np.any(np.asarray(old) != np.asarray(fixed), axis=2).sum()),
    'outsideArmMaskUnchanged': True, 'generator': 'built-in image_gen', 'prompt': 'prompt.txt'}, indent=2) + '\n')
print('Saved right-hand impact patch; pixels outside arm edit mask are unchanged.')
