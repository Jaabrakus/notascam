#!/usr/bin/env python3
"""Independent read-only local batch review; writes a JSON report only."""
import collections
import datetime
import hashlib
import json
from pathlib import Path

from validate_dmi import load_asset, validate_paths

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    queue = json.loads((BASE / '_meta/local-batch-queue.json').read_text())
    manifest = json.loads((BASE / '_meta/manifest.json').read_text())
    report = {
        'schema_version': 1,
        'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': 'independent_sol_fullpack_qa',
        'method': 'local_native_rgb_enhancement_not_AI_redraw',
        'validator': '_tools/validate_dmi.py',
        'validator_tests_passed': 23,
        'require_enhanced': True,
        'runtime_installed': False,
        'runtime_tested': False,
        'files': [],
        'source_hash_failures': [],
        'preview_hash_failures': [],
        'categories': {},
        'limitations': ['Local color/shading enhancement is different from the earlier AI redraw style.',
                        'Structural checks cannot establish artistic quality or runtime behavior.',
                        'Visual review samples selected cells, not every animation cell.'],
    }
    for entry in manifest['files']:
        p = Path(manifest['source_root']) / entry['source_path']
        if not p.exists() or sha(p) != entry['source_sha256']:
            report['preview_hash_failures'].append(entry['source_path'])
    cells = states = visible = changed = padding = 0
    for index, entry in enumerate(queue['files']):
        src = ROOT / entry['source_relative_path']
        dst = BASE / entry['output_relative_path']
        if sha(src) != entry['source_sha256']:
            report['source_hash_failures'].append(entry['source_relative_path'])
        result = validate_paths(src, dst, require_enhanced=True)
        summary = {'source': entry['source_relative_path'], 'output': entry['output_relative_path'],
                   'passed': result['passed'], 'failures': result['failures'], 'warnings': result['warnings']}
        if 'pixels' in result:
            md = result['source']['metadata']
            ordered_cells = [f['sheet_cell_index'] for f in result['frames']]
            coverage = ordered_cells == list(range(md['used_cells']))
            if not coverage:
                summary['passed'] = False
                summary['failures'].append('Full ordered state-cell coverage differs')
            summary.update({'source_sha256': result['source']['file_sha256'],
                            'output_sha256': result['candidate']['file_sha256'],
                            'frame_size': md['frame_size'], 'ordered_state_count': len(md['ordered_states']),
                            'duplicate_state_names': md['duplicate_state_names'],
                            'frame_cells': len(result['frames']), 'complete_ordered_coverage': coverage,
                            'pixels': result['pixels'], 'padding': result['padding']})
            cells += len(result['frames']); states += len(md['ordered_states'])
            visible += result['pixels']['source_visible_pixels']; changed += result['pixels']['visible_rgb_changed']
            padding += result['padding']['unused_cells']
        category = Path(entry['output_relative_path']).parts[1]
        counts = report['categories'].setdefault(category, {'files': 0, 'passed': 0})
        counts['files'] += 1; counts['passed'] += int(summary['passed'])
        report['files'].append(summary)
        if (index + 1) % 100 == 0:
            print('Independent QA:', index + 1, 'checked', flush=True)
    stone_src = ROOT / manifest['native_source_root_relative_path'] / 'Items/stonelimb.dmi'
    stone_out = BASE / 'enhanced-height/Items/stonelimb.dmi'
    stone_baseline = json.loads((BASE / '_meta/stonelimb-height-package.json').read_text())
    if sha(stone_src) != stone_baseline['native_sha256']:
        report['source_hash_failures'].append(str(stone_src.relative_to(ROOT)))
    old = load_asset(stone_src.read_bytes(), str(stone_src))
    new = load_asset(stone_out.read_bytes(), str(stone_out))
    oldbox = old.image.getchannel('A').getbbox(); newbox = new.image.getchannel('A').getbbox()
    stone = {'method': 'existing_AI_art_mechanically_resized_and_packed',
             'source_sha256': sha(stone_src), 'output_sha256': sha(stone_out),
             'reviewed_output_hash_unchanged': sha(stone_out) == stone_baseline['sha256'],
             'exact_description': old.description == new.description,
             'frame_size_equal': old.metadata.width == new.metadata.width and old.metadata.height == new.metadata.height,
             'source_visible_height': oldbox[3] - oldbox[1], 'output_visible_height': newbox[3] - newbox[1],
             'frame_cells': old.metadata.used_cells, 'runtime_tested': False}
    stone['passed'] = stone['exact_description'] and stone['frame_size_equal'] and stone['reviewed_output_hash_unchanged'] and stone['source_visible_height'] == stone['output_visible_height'] == 4 and old.metadata.used_cells == new.metadata.used_cells == 1
    report['existing_AI_stonelimb'] = stone
    report['counts'] = {'local_files': len(report['files']), 'local_passed': sum(f['passed'] for f in report['files']),
                        'local_failed': sum(not f['passed'] for f in report['files']), 'local_ordered_states': states,
                        'local_frame_cells': cells, 'local_unused_padding_cells': padding,
                        'local_source_visible_pixels': visible, 'local_visible_rgb_changed': changed,
                        'source_previews_hashed': len(manifest['files']), 'native_sources_hashed': len(queue['files']) + 1,
                        'combined_complete_sources': sum(f['passed'] for f in report['files']) + int(stone['passed']),
                        'combined_frame_cells': cells + stone['frame_cells']}
    report['passed'] = report['counts']['local_passed'] == 668 and stone['passed'] and not report['source_hash_failures'] and not report['preview_hash_failures']
    out = BASE / '_meta/local-fullpack-independent-review.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'counts': report['counts'], 'report': str(out)}, indent=2))

if __name__ == '__main__':
    main()
