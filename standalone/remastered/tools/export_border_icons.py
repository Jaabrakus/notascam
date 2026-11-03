#!/usr/bin/env python3
"""Consume sprite atlases to export original border-control glyphs for the HUD."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from PIL import Image

BASE = Path(__file__).resolve().parents[1]
PIPELINE = 'dungeon-master-border-icons-v1'
VARIANTS = [dict(id='daynight-sun', source='Icons/HUD.dmi', icon_state='Sun'),
            dict(id='daynight-moon', source='Icons/HUD.dmi', icon_state='Moon')]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def under(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path escapes its source root: ' + relative)
    return path


def read_controls(path):
    value = read_json(path)
    rows = value if isinstance(value, list) else value.get('controls') if isinstance(value, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError('Control catalog must contain a nonempty controls array')
    result, ids = [], set()
    for row in [*rows, *VARIANTS]:
        if not isinstance(row, dict):
            raise ValueError('Control entries must be objects')
        entry = {key: row.get(key) for key in ('id', 'source', 'icon_state')}
        if not isinstance(entry['id'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', entry['id']):
            raise ValueError('Unsafe or missing control id: ' + repr(entry['id']))
        if entry['id'] in ids:
            raise ValueError('Duplicate or reserved control id: ' + entry['id'])
        if not all(isinstance(entry[key], str) for key in ('source', 'icon_state')):
            raise ValueError('Control source and icon_state must be strings: ' + entry['id'])
        ids.add(entry['id'])
        result.append(entry)
    return result


def original_frame(path, state_name):
    """Independent source-DMI walk; do not trust atlas source_rect coordinates."""
    with Image.open(path) as image:
        w, h, states, current = 32, 32, [], None
        for line in image.info.get('Description', '').splitlines():
            match = re.match(r'\s*(\w+)\s*=\s*(.*)', line)
            if not match:
                continue
            key, value = match.groups()
            if key == 'state':
                current = dict(name=json.loads(value), movement=0, dirs=1, frames=1)
                states.append(current)
            elif current is None:
                if key == 'width': w = int(value)
                if key == 'height': h = int(value)
            elif key in ('movement', 'dirs', 'frames'):
                current[key] = int(value)
        matches = [s for s in states if s['name'] == state_name and s['movement'] == 0]
        if len(matches) != 1:
            raise ValueError(f'Source state must be unambiguous: {path.name}:{state_name!r} ({len(matches)} matches)')
        offset = 0
        for state in states:
            if state is matches[0]:
                break
            offset += state['dirs'] * state['frames']
        if w <= 0 or h <= 0 or image.width % w or image.height % h:
            raise ValueError('Invalid native dimensions: ' + str(path))
        cols = image.width // w
        rect = [offset % cols * w, offset // cols * h, w, h]
        x, y, _, _ = rect
        if y + h > image.height:
            raise ValueError('Source frame outside image: ' + str(path))
        return image.convert('RGBA').crop((x, y, x + w, y + h)), rect


def resolve(manifest, row):
    assets = [a for a in manifest['assets'] if a['source'] == row['source'] and a['status'] == 'exported']
    if len(assets) != 1:
        raise ValueError(f'Missing or ambiguous asset: {row["source"]!r}')
    asset = assets[0]
    states = [s for s in asset['states'] if s['name'] == row['icon_state'] and s['movement'] == 0]
    if len(states) != 1 or states[0]['occurrence'] != 0:
        raise ValueError(f'Missing or ambiguous state: {row["source"]}:{row["icon_state"]!r}')
    state = states[0]
    cells = [c for c in state['cells'] if c['direction'] == 'south' and c['frame'] == 0]
    if len(cells) != 1:
        raise ValueError('Missing or ambiguous SOUTH frame 0: ' + row['id'])
    return asset, state, cells[0]


def export(config, manifest_path, source_root, output, report_path):
    rows = read_controls(config)
    manifest = read_json(manifest_path)
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported sprite manifest version')
    output, report_path = output.resolve(), report_path.resolve()
    if output == source_root.resolve() or source_root.resolve().is_relative_to(output):
        raise ValueError('Output must not contain the source root')
    if report_path.is_relative_to(output):
        raise ValueError('Provenance report must live outside generated image directory')
    if output.exists() and any(output.iterdir()):
        if not report_path.is_file() or read_json(report_path).get('pipeline') != PIPELINE:
            raise ValueError('Refusing to replace a non-pipeline image directory')
        if any(p.suffix != '.png' or not p.is_file() for p in output.iterdir()):
            raise ValueError('Unexpected files in generated image directory')
    pages, sources, records = {}, {}, []
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.border-icons-', dir=output.parent) as temp:
        stage = Path(temp) / 'images'
        stage.mkdir()
        for row in rows:
            asset, state, cell = resolve(manifest, row)
            source = under(source_root, asset['source'])
            if source not in sources:
                sources[source] = sha(source.read_bytes())
            if sources[source] != asset['source_sha256']:
                raise ValueError('Atlas is stale for original sprite: ' + row['source'])
            page_index = cell['page']
            if page_index not in pages:
                page_entry = next(p for p in manifest['pages'] if p['id'] == page_index)
                page_path = under(manifest_path.parent, page_entry['file'])
                if sha(page_path.read_bytes()) != page_entry['sha256']:
                    raise ValueError('Atlas page hash mismatch: ' + page_entry['file'])
                with Image.open(page_path) as page:
                    pages[page_index] = page.convert('RGBA')
            x, y, w, h = cell['rect']
            page = pages[page_index]
            if min(x, y) < 0 or w <= 0 or h <= 0 or x + w > page.width or y + h > page.height:
                raise ValueError('Frame rectangle outside atlas: ' + row['id'])
            pixels = page.crop((x, y, x + w, y + h))
            crop_hash = sha(pixels.tobytes())
            if crop_hash != cell['rgba_sha256']:
                raise ValueError('Atlas frame hash mismatch: ' + row['id'])
            original, source_rect = original_frame(source, row['icon_state'])
            if original.size != pixels.size or original.tobytes() != pixels.tobytes():
                raise ValueError('Atlas crop differs from original DMI: ' + row['id'])
            if list(pixels.size) != asset['native_size'] or source_rect != cell['source_rect']:
                raise ValueError('Native size or source coordinates differ: ' + row['id'])
            name = row['id'] + '.png'
            target = stage / name
            pixels.save(target, format='PNG', optimize=False, compress_level=9)
            with Image.open(target) as saved:
                if saved.mode != 'RGBA' or saved.size != pixels.size or saved.tobytes() != original.tobytes():
                    raise ValueError('Saved output differs from original pixels: ' + name)
            records.append(dict(**row, file=name, browser_resource='remaster-border-' + name,
                                source_sha256=sources[source], asset_id=asset['id'], state_id=state['id'],
                                movement=0, occurrence=0, direction='south', frame=0,
                                native_size=list(pixels.size), source_rect=source_rect, atlas_page=page_index,
                                atlas_rect=cell['rect'], rgba_sha256=crop_hash, png_sha256=sha(target.read_bytes()),
                                matches_original=True))
        if any(sha(source.read_bytes()) != previous for source, previous in sources.items()):
            raise ValueError('Original sprite changed during export')
        report = dict(pipeline=PIPELINE, passed=True, controls=len(rows) - len(VARIANTS), variants=len(VARIANTS),
                      images=len(records), config_sha256=sha(config.read_bytes()),
                      sprite_manifest_sha256=sha(manifest_path.read_bytes()),
                      exporter_sha256=sha(Path(__file__).read_bytes()), original_sprites_unchanged=True,
                      source_files=[dict(source=str(p.relative_to(source_root.resolve())), sha256=sources[p])
                                    for p in sorted(sources)], outputs=records)
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(stage), output)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=BASE / 'game/Interface/border-controls.json')
    parser.add_argument('--manifest', type=Path, default=BASE / 'assets/sprites/manifest.json')
    parser.add_argument('--source', type=Path, default=BASE / 'game')
    parser.add_argument('--output', type=Path, default=BASE / 'game/Interface/border-icons')
    parser.add_argument('--report', type=Path, default=BASE / 'assets/border-icons-provenance.json')
    args = parser.parse_args()
    try:
        report = export(args.config, args.manifest, args.source, args.output, args.report)
    except (ValueError, OSError, KeyError, StopIteration) as error:
        parser.exit(1, 'Border icon export failed: ' + str(error) + '\n')
    print(json.dumps({k: report[k] for k in ('passed', 'controls', 'variants', 'images', 'original_sprites_unchanged')}, indent=2))


if __name__ == '__main__':
    main()
