#!/usr/bin/env python3
"""Check that rejected immediate unloading does not disturb work or defense."""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
import check_combat as c


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='delivery-commit')
    parser.add_argument('--port', type=int, default=12196)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label):
        parser.error('Use a simple label')
    if not 1024 <= args.port <= 52035:
        parser.error('port must be 1024..52035')
    root = c.ROOT
    sources = {str(p.relative_to(root/'game')): sha(p) for p in sorted((root/'game').rglob('*.dm'))}
    runtime = c.RUNTIME/'server/Resources/Assemblies/OpenDreamRuntime.dll'
    runtime_before = sha(runtime)
    fixture_source = root/'tests/delivery_commit_test.dm'
    fixture_before = sha(fixture_source)
    with tempfile.TemporaryDirectory(prefix='dm-delivery-commit-') as work:
        arena = Path(work)/'world'
        shutil.copytree(root/'game', arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'units', 'saves', 'ErrorLog.txt'))
        world = arena/'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()'); end = source.index('\nvar/Season', start)
        world.write_text(source[:start]+'\tNew()\n\t\tspawn(0) DeliveryCommitRun()\n'+source[end:], encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
        shutil.copy2(fixture_source, arena/'delivery_commit_test.dm')
        fixture = arena/'delivery_commit.dme'
        fixture.write_text(dme+'\n#include "delivery_commit_test.dm"\n', encoding='latin-1')
        passed = c.run_world(arena, fixture, args.label, 120, prefix='DEFENSE', port=args.port)
        report = root/f'tests/{args.label}-checks.json'
        result = json.loads(report.read_text())
        result.update(source_sha256=sources, runtime_before=runtime_before,
            fixture_sha256=fixture_before,
            source_stable=all(sha(root/'game'/name)==digest for name,digest in sources.items()),
            runtime_stable=runtime_before==sha(runtime), fixture_stable=fixture_before==sha(fixture_source),
            scope='Real Human/Orc constructors, original movement, inventory, queues, defense and delivery procedures. Private grass map, no normal saves or native input.')
        result['passed'] = passed and result['source_stable'] and result['runtime_stable'] and result['fixture_stable']
        report.write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
