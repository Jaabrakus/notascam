#!/usr/bin/env python3
"""Resume a selected local pass; never writes source or shared manifests.

This is a local RGB enhancement, distinct from generated redraw artwork.
Every native cell is retained at its original size and location. The engine
checks exact decoded alpha, transparent RGB, padding, and Description text.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import traceback


BASE = Path(__file__).resolve().parents[1]
QUEUE_PATH = BASE / '_meta/local-batch-queue.json'
REPORT_PATH = BASE / '_meta/local-batch-report.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)


def process(entry, root):
    from enhance_native_local import enhance_file
    started = time.monotonic()
    source = root / entry['source_relative_path']
    output = BASE / entry['output_relative_path']
    result = dict(entry)
    try:
        if sha256(source) != entry['source_sha256']:
            raise ValueError('Source no longer matches queued original hash')
        engine = enhance_file(source, output)
        result['engine'] = engine
        result['source_unchanged'] = sha256(source) == entry['source_sha256']
        result['output_sha256'] = sha256(output) if output.exists() else None
        passed = engine.get('passed', False) and result['source_unchanged']
        empty = engine.get('source_visible_pixels') == 0
        if not passed:
            result['status'] = 'failed'
        elif empty:
            result['status'] = 'empty_preserved'
        elif not engine.get('visible_rgb_changed', 0):
            result['status'] = 'failed'
            result['error'] = 'No visible RGB changed; not counted as enhanced'
        else:
            result['status'] = 'enhanced'
    except Exception as exc:
        result.update(status='failed', error=str(exc), traceback=traceback.format_exc())
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    result['finished_at'] = stamp()
    return result


def aggregate(report):
    entries = report['files']
    report['counts'] = {
        status: sum(item.get('status') == status for item in entries)
        for status in ('queued', 'running', 'enhanced', 'empty_preserved', 'failed')
    }
    report['completed_count'] = report['counts']['enhanced'] + report['counts']['empty_preserved']
    report['used_cells'] = sum(item.get('engine', {}).get('used_cells', 0) for item in entries)
    report['visible_rgb_changed'] = sum(item.get('engine', {}).get('visible_rgb_changed', 0) for item in entries)
    report['updated_at'] = stamp()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--queue', type=Path, default=QUEUE_PATH)
    parser.add_argument('--report', type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text())
    root = Path(queue['source_root'])
    previous = json.loads(args.report.read_text()) if args.report.exists() else {}
    previous_by_source = {e['source_relative_path']: e for e in previous.get('files', [])}
    entries = []
    for item in queue['files']:
        old = previous_by_source.get(item['source_relative_path'])
        if old and old.get('source_sha256') == item['source_sha256']:
            entries.append(old)
        else:
            entries.append(dict(item, status='queued'))
    report = {
        'schema_version': 1, 'method': queue['method'], 'status': 'running',
        'scope': queue.get('scope', 'Remaining native DMI sheets; checked AI stonelimb excluded'),
        'limitations': ['Local RGB enhancement is distinct from AI redraw artwork.',
                        'Preservation validation does not establish artistic quality or runtime integration.'],
        'source_root': str(root), 'output_root': queue.get('output_root', str(BASE / 'local-enhanced')),
        'queue_count': len(entries), 'excluded': queue['excluded'],
        'started_at': previous.get('started_at', stamp()), 'files': entries,
    }
    if 'selection' in queue:
        report['selection'] = queue['selection']
        report['scope'] = queue.get('scope', 'Selected player races, weapons, and armor')
    pending = []
    engine_hash = sha256(Path(__file__).with_name('enhance_native_local.py'))
    for index, item in enumerate(entries):
        if item.get('status') in ('enhanced', 'empty_preserved'):
            output = BASE / item['output_relative_path']
            if (item.get('engine', {}).get('engine_sha256') == engine_hash
                    and output.exists() and sha256(output) == item.get('output_sha256')
                    and sha256(root / item['source_relative_path']) == item['source_sha256']):
                continue
        elif item.get('status') == 'failed' and not args.retry_failed:
            continue
        pending.append(index)
    aggregate(report)
    atomic_json(args.report, report)
    print(json.dumps({'event': 'start', 'queued': len(pending), 'workers': args.workers}), flush=True)
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(process, entries[i], root): i for i in pending}
        for future in as_completed(futures):
            index = futures[future]
            entries[index] = future.result()
            aggregate(report)
            atomic_json(args.report, report)
            if report['completed_count'] % 20 == 0 or entries[index]['status'] == 'failed':
                print(json.dumps({'event': 'progress', 'counts': report['counts'],
                                  'last': entries[index]['source_relative_path'],
                                  'error': entries[index].get('error')}), flush=True)
    unchanged = all(sha256(root / e['source_relative_path']) == e['source_sha256'] for e in entries)
    report['all_sources_unchanged'] = unchanged
    report['status'] = 'complete' if report['completed_count'] == len(entries) and unchanged else 'incomplete'
    report['finished_at'] = stamp()
    aggregate(report)
    atomic_json(args.report, report)
    print(json.dumps({'event': 'finished', 'status': report['status'], 'counts': report['counts'],
                      'used_cells': report['used_cells'], 'all_sources_unchanged': unchanged}), flush=True)
    return 0 if report['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
