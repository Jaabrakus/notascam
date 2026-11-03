#!/bin/zsh
# One release: build N, then its checks (the coordinator's release script, kept here for the next developer, 2026-10-26).
#   zsh tools/release.sh 57
# The build holds the run lock only to compile and package (a short exclusive hold); check_app and the launch check then
# run as an ordinary input run beside other runs. Logs go to reports/coordinator/release-logs/.
# The display must be awake: asleep, the real window never starts 3D and the launch check fails got_3d. So it wakes the
# display first and holds it awake (caffeinate) while the checks run.
N=$1
[ -n "$N" ] || { echo "usage: zsh tools/release.sh <build number>"; exit 2; }
R=$(cd "$(dirname "$0")/.." && pwd)
L=$R/reports/coordinator/release-logs
mkdir -p $L
cd $R
cat > $L/b$N.sh <<EOB
cd $R
BOTD_BUILD=$N python3 tools/build_app.py > $L/build$N.log 2>&1; rc=\$?; echo BUILD_EXIT \$rc; [ \$rc -eq 0 ] || exit \$rc
find "Banners of the Deep.app" -name OpenDreamRuntime.dll -exec shasum -a 256 {} \; | cut -c1-20
EOB
cat > $L/c$N.sh <<EOC
cd $R
python3 tools/check_app.py --race Elf --label app$N > $L/check_app$N.log 2>&1; echo CHECK_EXIT \$?
python3 reports/coordinator/post_build_check.py > $L/postbuild$N.json 2>&1; echo POST_EXIT \$?
EOC
caffeinate -d python3 tools/runlock.py --who coordinator --kind build -- zsh $L/b$N.sh || { echo RELEASE_STOP; exit 1; }
caffeinate -u -t 3
# SKIP_WINDOW_CHECK=1 (owner 10-27: "I'm playing; skip build 83's launch check"): build only; check_app and the launch check
# open a real window and wait for the owner's game to close, so they are skipped while the owner plays.
if [ -n "$SKIP_WINDOW_CHECK" ]; then echo WINDOW_CHECK_SKIPPED; else
caffeinate -d -u python3 tools/runlock.py --who coordinator --kind input -- zsh $L/c$N.sh
fi
echo RELEASE_DONE $N
