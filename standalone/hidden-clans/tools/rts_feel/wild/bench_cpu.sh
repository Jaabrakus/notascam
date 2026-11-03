#!/bin/zsh
# An arena test with the server's own CPU time sampled per phase (tools/rts_feel/wild/cpu_marks.py), through the run lock:
#   zsh tools/rts_feel/wild/bench_cpu.sh GAME TEST ENTRY REPORT PORT OUTDIR [more check_arena args]
# Writes OUTDIR/<report stem>.out (check_arena's output) and OUTDIR/<report stem>-cpu.txt (CPU ms a second per phase).
cd "$(dirname "$0")/../../.."
G=$1 T=$2 E=$3 R=$4 P=$5 O=$6; shift 6
stem=${R%.json}
mkdir -p $O
nice -n 5 python3 tools/runlock.py --who rts-feel --kind run -- zsh -c "rm -f tests/$stem-server.log; python3 tools/rts_feel/wild/cpu_marks.py --port $P --log tests/$stem-server.log --out $O/$stem-marks.json > $O/$stem-cpu.txt 2>&1 & python3 tools/check_arena.py --game $G --test $T --entry $E --report $R --port $P --timeout 900 $* > $O/$stem.out 2>&1; wait"
cat $O/$stem-cpu.txt
/usr/bin/grep "CK|time" tests/$stem-server.log | sed 's/.*CK|time|//'
echo "exceptions: $(/usr/bin/grep -c 'Exception occurred' tests/$stem-server.log)"
