"""While you were away (Away.dm): runs tests/away_test.dm in the obey arena (check_breaking.py's
runner) and writes tests/away-checks.json."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.exit(subprocess.run([sys.executable, str(ROOT/'tools/check_breaking.py'), '--entry', 'AwRun',
                         '--extra', str(ROOT/'tests/away_test.dm'), '--report', 'away-checks.json']).returncode)
