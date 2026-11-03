"""Lethal / Non-lethal, knock-outs and capturing (Subdue.dm): runs tests/subdue_test.dm in the obey
arena (check_breaking.py's runner) and writes tests/subdue-checks.json."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.exit(subprocess.run([sys.executable, str(ROOT/'tools/check_breaking.py'), '--entry', 'SuRun',
                         '--extra', str(ROOT/'tests/subdue_test.dm'), '--report', 'subdue-checks.json']).returncode)
