#!/usr/bin/env python3
"""Exercise the shared packaged save handshake against isolated file responders."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'mac-app/local_save.zsh'


def run_case(mode):
    with tempfile.TemporaryDirectory(prefix='dm-local-save-') as temporary:
        request = Path(temporary) / 'profile with spaces' / 'save-request'
        request.parent.mkdir()
        ack = Path(str(request) + '.ack')
        error = Path(str(request) + '.error')
        if mode.startswith('stale'):
            ack.write_text('previous-session\n')
            error.write_text('previous-session failure\n')
        command = ['source "$1"; dm_request_local_save "$2" "$3"',
                   'save-test', str(HELPER), str(request), '2']
        process = subprocess.Popen(['/bin/zsh', '-c', *command],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 5
        while not request.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.01)
        token = request.read_text().strip() if request.exists() else ''
        if mode in ('fresh_ack', 'stale_then_fresh'):
            ack.write_text(token + '\n')
        elif mode == 'late_matching_ack':
            ack.write_text('late-result-from-previous-request\n')
            time.sleep(.1)
            ack.write_text(token + '\n')
        elif mode == 'wrong_ack':
            ack.write_text('unrelated-request\n')
        elif mode == 'server_error':
            error.write_text('save flush failed\n')
        elif mode == 'empty_ack':
            ack.write_text('')
        stdout, stderr = process.communicate(timeout=6)
        expected = mode in ('fresh_ack', 'stale_then_fresh', 'late_matching_ack')
        return dict(case=mode, passed=bool(token) and (process.returncode == 0) == expected,
                    expected_success=expected, exit_code=process.returncode,
                    request_token=token, stdout=stdout, stderr=stderr)


def main():
    for script in (HELPER, ROOT/'mac-app/launch.zsh', ROOT.parent/'remastered/mac-app/launch.zsh'):
        subprocess.run(['/bin/zsh', '-n', str(script)], check=True)
    cases = ('fresh_ack', 'stale_then_fresh', 'stale_no_response', 'late_matching_ack',
             'wrong_ack', 'server_error', 'empty_ack', 'no_response')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run_case, cases))
    report = dict(passed=all(row['passed'] for row in results),
                  checked_utc=datetime.now(timezone.utc).isoformat(),
                  source_sha256=hashlib.sha256(HELPER.read_bytes()).hexdigest(),
                  scope='Actual shared zsh helper; isolated file responders, no game process or player saves.',
                  cases=results)
    out = ROOT/'reports/local-save-checks.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
