#!/bin/zsh
# The dragon scene (episode 4 of the golem series): the tribe makes camp beside a big red rock that turns out to be a
# sleeping fire dragon, and fights it. It plays in the real game (Banners of the Deep,
# 3D) from a temporary copy with a test player, so your saves are never touched. Double-click to watch; double-click
# again to replay. Close the game window to finish.
cd "$(dirname "$0")"
echo "Opening the dragon scene: the game window comes up in about a minute, then it plays (about 1.5 minutes)."
GS_EP=4 GS_WATCH=1 python3 tools/runlock.py --who dragon-scene -- caffeinate -d -i -u python3 tools/trailer/golem/golem_run.py 2>&1 | /usr/bin/grep -E --line-buffered "^(compiled|scene done|Traceback|AssertionError|SystemExit)|waiting|Error" 
echo "Done. You can close this window."
