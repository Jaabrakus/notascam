#!/usr/bin/env python3
"""Restart a local world only after an explicit runtime Reboot request.

A normal exit, crash or operator stop never causes an unsolicited restart.
The ready token changes only when the new server actually reaches Ready.
"""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import uuid


def supervise(command, env, ready_file=None):
    child=None; stopping=False
    def stop(signum, frame):
        nonlocal stopping
        stopping=True
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)
    old={s:signal.signal(s,stop) for s in (signal.SIGINT,signal.SIGTERM)}
    if ready_file: ready_file.unlink(missing_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='dm-reboot-') as work:
            request=Path(work)/'request'
            session_env=dict(env, DM_REBOOT_REQUEST=str(request))
            while not stopping:
                request.unlink(missing_ok=True)
                child=subprocess.Popen([str(x) for x in command],env=session_env,
                                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                       text=True,errors='replace',start_new_session=True)
                try:
                    for line in child.stdout:
                        print(line,end='',flush=True)
                        if ready_file and ' -> Ready' in line:
                            temp=ready_file.with_suffix('.pending')
                            temp.write_text(str(uuid.uuid4()))
                            temp.replace(ready_file)
                    result=child.wait()
                finally:
                    if child.poll() is None:
                        child.terminate()
                        try:child.wait(timeout=10)
                        except subprocess.TimeoutExpired:child.kill();child.wait()
                if ready_file: ready_file.unlink(missing_ok=True)
                if stopping or not request.exists(): return result
                print('[INFO] dm.supervisor: explicit world reboot; starting a fresh server',flush=True)
            return 0
    finally:
        if ready_file:ready_file.unlink(missing_ok=True)
        for s,handler in old.items():signal.signal(s,handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready-file',type=Path)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command
    if command and command[0]=='--':command=command[1:]
    if not command:parser.error('Expected server command after --')
    raise SystemExit(supervise(command,os.environ,args.ready_file))

if __name__=='__main__':main()
