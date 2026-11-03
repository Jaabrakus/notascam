#!/usr/bin/env python3
"""Check actual launcher cleanup and compiled exit decisions without launching a game."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = {'classic': ROOT/'mac-app', 'remastered': ROOT.parent/'remastered/mac-app'}
HEADER = ROOT/'mac-app/LauncherOutcome.h'

HARNESS = r'''
#import <Foundation/Foundation.h>
#import "LauncherOutcome.h"
int main(int argc, const char **argv) {
    @autoreleasepool {
        if (argc != 2) return 2;
        NSData *data=[NSData dataWithContentsOfFile:@(argv[1])];
        NSArray *cases=[NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
        NSMutableArray *results=[NSMutableArray array];
        for (NSDictionary *row in cases) {
            if ([row[@"kind"] isEqualToString:@"termination"]) {
                DMLaunchTermination decision=DMLaunchTerminationForRequest([row[@"finished"] boolValue],[row[@"requested_quit"] boolValue],[row[@"task_running"] boolValue]);
                [results addObject:@{@"name":row[@"name"],@"terminate_now":@(decision.terminateNow),@"signal_child":@(decision.signalChild)}];
                continue;
            }
            NSString *status=row[@"status"]==NSNull.null ? nil : row[@"status"];
            DMLaunchOutcome outcome=DMLaunchOutcomeForExit([row[@"exit_code"] intValue],[row[@"requested_quit"] boolValue],status);
            [results addObject:@{@"name":row[@"name"],@"show_alert":@(outcome.showAlert),@"result_code":@(outcome.resultCode)}];
        }
        NSData *output=[NSJSONSerialization dataWithJSONObject:results options:0 error:nil];
        fwrite(output.bytes,1,output.length,stdout);
        return 0;
    }
}
'''


def cleanup_case(base, label, source, save_result):
    # Exercise the production cleanup body. Only the save responder, process
    # signaling and delays are stubbed; all files belong to this temporary case.
    text = source.read_text()
    cleanup = text[text.index('cleanup() {'):text.index("trap 'cleanup' EXIT")]
    script = '''
set -u
data=$1
dm_test_save_result=$2
mkdir -p "$data/reports" "$data/launcher.lock"
ready="$data/ready"
reboot="$data/reboot"
lock="$data/launcher.lock"
status_file="$data/launch-status"
save_request="$data/reports/save-request"
supervisor_pid=123
client_pid=0
cleaned=0
save_failed=0
touch "$ready" "$lock/pid"
print -r -- playing > "$status_file"
dm_request_local_save() { return "$dm_test_save_result"; }
kill() { return 0; }
wait() { return 0; }
sleep() { return 0; }
''' + cleanup + '\ncleanup\nexit 0\n'
    profile = base/label
    process = subprocess.run(['/bin/zsh','-c',script,'launcher-cleanup-test',str(profile),str(save_result)],capture_output=True,text=True,timeout=5)
    return dict(name=label,exit_code=process.returncode,status=(profile/'launch-status').read_text().strip(),
                save_status=(profile/'reports/save-status').read_text().strip(),stderr=process.stderr,
                lock_removed=not (profile/'launcher.lock').exists(),ready_removed=not (profile/'ready').exists())


def main():
    paths = [HEADER] + [folder/name for folder in LAUNCHERS.values() for name in ('Launcher.m','launch.zsh')]
    before = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    checks = {}
    with tempfile.TemporaryDirectory(prefix='dm-launcher-outcomes-') as temporary:
        base = Path(temporary)
        cleanup_results = []
        for label,folder in LAUNCHERS.items():
            subprocess.run(['/bin/zsh','-n',str(folder/'launch.zsh')],check=True)
            for save_result in (0,1):
                row = cleanup_case(base,label+('-saved' if save_result==0 else '-save-failed'),folder/'launch.zsh',save_result)
                cleanup_results.append(row)
                checks[row['name']+'_cleanup_status'] = not row['stderr'] and row['lock_removed'] and row['ready_removed'] and (
                    row['exit_code']==0 and row['status']=='stopped' and row['save_status']=='saved' if save_result==0 else
                    row['exit_code']==1 and row['status'].startswith('error:') and 'may not have been saved' in row['status'] and row['save_status']=='save-failed')
        cases = [dict(name='normal_close',exit_code=0,requested_quit=False,status='stopped',expect_alert=False,expect_code=0),
                 dict(name='intentional_sigterm',exit_code=130,requested_quit=True,status='stopped',expect_alert=False,expect_code=0),
                 dict(name='startup_failure',exit_code=1,requested_quit=False,status='error:World failed to start',expect_alert=True,expect_code=1),
                 dict(name='unexpected_failure',exit_code=1,requested_quit=False,status=None,expect_alert=True,expect_code=1),
                 dict(name='explicit_error_even_if_child_returns_zero',exit_code=0,requested_quit=True,status='error:Final save failed',expect_alert=True,expect_code=1)]
        for row in cleanup_results:
            for requested in (False,True):
                cases.append(dict(name=row['name']+('-cmd-q' if requested else '-window-close'),exit_code=row['exit_code'],requested_quit=requested,
                                  status=row['status'],expect_alert=row['save_status']=='save-failed',expect_code=row['exit_code']))
        cases.extend([
            dict(name='first_quit_waits_and_signals_once',kind='termination',finished=False,requested_quit=False,task_running=True,expect_now=False,expect_signal=True),
            dict(name='repeated_quit_waits_for_save_without_second_signal',kind='termination',finished=False,requested_quit=True,task_running=True,expect_now=False,expect_signal=False),
            dict(name='stopped_child_waits_for_completion_callback',kind='termination',finished=False,requested_quit=True,task_running=False,expect_now=False,expect_signal=False),
            dict(name='completed_shutdown_can_terminate',kind='termination',finished=True,requested_quit=True,task_running=False,expect_now=True,expect_signal=False),
            dict(name='failed_child_launch_can_terminate',kind='termination',finished=True,requested_quit=False,task_running=False,expect_now=True,expect_signal=False)])
        source=base/'outcomes.m';source.write_text(HARNESS)
        binary=base/'outcomes';input_file=base/'cases.json';input_file.write_text(json.dumps(cases))
        subprocess.run(['/usr/bin/clang','-fobjc-arc','-framework','Foundation','-I',str(HEADER.parent),str(source),'-o',str(binary)],check=True,capture_output=True,text=True)
        actual=json.loads(subprocess.run([str(binary),str(input_file)],check=True,capture_output=True,text=True).stdout)
        expected={row['name']:row for row in cases}
        for row in actual:
            case=expected[row['name']]
            if case.get('kind') == 'termination':
                checks[row['name']+'_launcher_outcome']=row['terminate_now']==case['expect_now'] and row['signal_child']==case['expect_signal']
            else:
                checks[row['name']+'_launcher_outcome']=row['show_alert']==case['expect_alert'] and row['result_code']==case['expect_code']
        checks['all_compiled_outcome_cases_reported']=len(actual)==len(cases)
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    checks['source_stable']=before==after
    report=dict(scope=__doc__,checks=checks,cleanup_results=cleanup_results,outcomes=actual,source_sha256=after,passed=all(checks.values()))
    (ROOT/'reports/launcher-outcome-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
