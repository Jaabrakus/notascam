"""Verify delivered female standing atlases and DMI serialization."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pack import clean, STATES

HERE = Path(__file__).resolve().parent


def verify(require_complete=False):
    catalog = json.loads((HERE / 'all-catalog.json').read_text())
    coverage = json.loads((HERE / 'all-coverage.json').read_text())
    assert len(catalog) == 80 and len({j['id'] for j in catalog}) == 80
    assert len(coverage) == 80 and {j['id'] for j in catalog} == {j['id'] for j in coverage}
    packed = [j for j in coverage if j.get('image')]
    errors = []
    frames = 0
    for record in packed:
        try:
            image = Image.open(record['image']).convert('RGBA')
            dmi = Image.open(record['dmi'])
            assert image.size == (256, 448), 'Atlas dimensions'
            assert dmi.convert('RGBA').tobytes() == image.tobytes(), 'DMI pixels differ'
            description = dmi.info['Description']
            assert all(f'state = "{state}"' in description for state in STATES), 'Missing DMI state'
            assert description.count('dirs = 4') == 7 and description.count('frames = 1') == 7
            rgba = np.asarray(image)
            assert set(np.unique(rgba[..., 3])) <= {0, 255}, 'Partial alpha remains'
            assert not rgba[rgba[..., 3] == 0].any(), 'Hidden RGB remains'
            for row in range(7):
                for column in range(4):
                    cell = rgba[row*64:(row+1)*64, column*64:(column+1)*64]
                    assert (cell[..., 3] > 0).sum() > 80, 'Empty or tiny pose'
                    _, removed = clean(cell)
                    assert removed == 0, 'Disconnected fragment remains'
                    assert not cell[63, :, 3].any(), 'Pose reaches bottom clipping edge'
                    frames += 1
            assert record['sourceRGBPreserved'] is True
        except (AssertionError, KeyError, OSError, ValueError) as error:
            errors.append(dict(id=record['id'], error=str(error)))
    report = dict(appearancesExpected=80, packed=len(packed), frames=frames,
                  nativeSheets=sum(sum(j['nativeSheets'].values()) for j in coverage),
                  missing=[j['id'] for j in coverage if not j.get('image')],
                  poseReviewsPending=[j['id'] for j in packed if j['flags']], errors=errors,
                  scope='standing injury atlas structure, transparency, connectivity and DMI pixels; not gait approval')
    report['completeStandingSet'] = not report['missing'] and not report['poseReviewsPending'] and not errors
    (HERE / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    assert not errors, 'Export validation failed'
    if require_complete:
        assert report['completeStandingSet'], 'Full set or pose reviews remain incomplete'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-complete', action='store_true')
    verify(parser.parse_args().require_complete)
