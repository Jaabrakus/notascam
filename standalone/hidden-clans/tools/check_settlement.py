#!/usr/bin/env python3
"""Check worker hauling, production, ownership, blocked orders and saved settings."""
from pathlib import Path
import re
import shutil
import tempfile

from check_combat import ROOT, run_world


def main():
    with tempfile.TemporaryDirectory(prefix='dm-settlement-') as temp:
        arena = Path(temp) / 'world'
        shutil.copytree(ROOT / 'game', arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.dmm', '*.sav', 'ErrorLog.txt', 'units'))
        dme = (arena / 'Cave Crawlers.dme').read_text(encoding='latin-1')
        dme = re.sub(r'^#include .*\.dmm"\s*$', '', dme, flags=re.M)
        for module in ('Settlement', 'Orders', 'HUD'):
            if f'Remastered\\{module}.dm' not in dme and (arena / f'Code/Remastered/{module}.dm').exists():
                dme += f'\n#include "Code\\Remastered\\{module}.dm"\n'
        fixture = arena / 'settlement.dme'
        fixture.write_text(dme + '\n#include "settlement_test.dm"\n', encoding='latin-1')
        source = arena / 'Code/World.dm'
        text = source.read_text(encoding='latin-1')
        start = text.index('\tNew()')
        end = text.index('\nvar/Season', start)
        source.write_text(text[:start] + '\tNew()\n\t\tspawn(0) SettlementRun()\n' + text[end:], encoding='latin-1')
        shutil.copy2(ROOT / 'tests/settlement_test.dm', arena / 'settlement_test.dm')
        passed = run_world(arena, fixture, 'settlement', 120, prefix='SETTLEMENT', port=12162)
        raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
