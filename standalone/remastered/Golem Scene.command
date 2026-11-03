#!/bin/zsh
# The golem scene: a tribe of orcs and goblins meets a stone golem, climbs it, gets shaken off and launched, carries
# its wounded back to camp for the Doctor, then sends in its champion. It plays in the real game (Banners of the Deep,
# 3D) from a temporary copy with a test player, so your saves are never touched. Double-click to watch; double-click
# again to replay. Close the game window to finish.
cd "$(dirname "$0")"
echo "Opening the golem scene: the game window comes up in about a minute, then three episodes play (about 4 minutes)."
GS_WATCH=1 python3 tools/runlock.py --who golem-scene -- caffeinate -d -i -u python3 tools/trailer/golem/golem_run.py 2>&1 | /usr/bin/grep -E --line-buffered "^(compiled|scene done|Traceback|AssertionError|SystemExit)|waiting|Error" 
echo "Done. You can close this window."
