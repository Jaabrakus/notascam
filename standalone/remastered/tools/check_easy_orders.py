#!/usr/bin/env python3
"""Run finite-order and delivery regressions in a private, mapless game copy."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from check_combat import ROOT, run_world


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='easy-orders')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--port', type=int, default=12164)
    parser.add_argument('--state-only', action='store_true', help='Run only save/load and death follow-up checks.')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.label):
        parser.error('label must contain only letters, digits, underscores and hyphens')
    if not 1024 <= args.port <= 52035 or args.timeout <= 0:
        parser.error('port must be 1024..52035 and timeout must be positive')
    (ROOT / 'tests').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dm-easy-orders-') as temp:
        arena = Path(temp) / 'world'
        shutil.copytree(ROOT / 'game', arena, ignore=shutil.ignore_patterns(
            'Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units', 'saves'))
        dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        for module in ('Settlement', 'Orders', 'Delivery', 'HUD'):
            if f'Remastered\\{module}.dm' not in dme and (arena / f'Code/Remastered/{module}.dm').exists():
                dme += f'\n#include "Code\\Remastered\\{module}.dm"\n'
        world = arena / 'Code/World.dm'
        source = world.read_text(encoding='latin-1')
        start = source.index('\tNew()')
        end = source.index('\nvar/Season', start)
        entry = 'EasyStateRun' if args.state_only else 'EasyOrdersRun'
        world.write_text(source[:start] + f'\tNew()\n\t\tspawn(0) {entry}()\n' + source[end:], encoding='latin-1')
        shutil.copy2(ROOT / 'tests/easy_orders_test.dm', arena / 'easy_orders_test.dm')
        fixture = arena / 'easy_orders.dme'
        fixture.write_text(dme + '\n#include "easy_orders_test.dm"\n', encoding='latin-1')
        hashes = {str(p.relative_to(arena)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted((arena / 'Code/Remastered').glob('*')) if p.is_file()}
        hashes['easy_orders_test.dm'] = hashlib.sha256((arena / 'easy_orders_test.dm').read_bytes()).hexdigest()
        (ROOT / f'tests/{args.label}-sources.json').write_text(json.dumps(hashes, indent=2) + '\n')
        try:
            passed = run_world(arena, fixture, args.label, args.timeout, prefix='EASY_ORDERS', port=args.port)
        except subprocess.CalledProcessError as error:
            result = {'passed': False, 'phase': 'compile', 'exit_code': error.returncode,
                      'log': str(ROOT / f'tests/{args.label}-compile.log')}
            (ROOT / f'tests/{args.label}-checks.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result, indent=2), flush=True)
            passed = False
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
