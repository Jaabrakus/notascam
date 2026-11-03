#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
exec "./Dungeon Master.app/Contents/MacOS/DungeonMaster" "$@"
