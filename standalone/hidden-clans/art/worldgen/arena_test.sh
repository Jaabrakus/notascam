#!/bin/bash
# Export one hex region and load it into the arena, windowless (tests/worldgen_region_test.dm).
#   art/worldgen/arena_test.sh [seed [col row]]
set -e
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
OUT=$(python3 art/worldgen/export.py "$@" | head -1 | cut -d' ' -f1)
BASE="${OUT%.txt}"
EXTRA="$(mktemp -d)/worldgen_region_test.dm"
{ echo "#define WG_REGION \"$BASE\""; cat tests/worldgen_region_test.dm; } > "$EXTRA"
python3 tools/runlock.py --who worldgen --kind run -- python3 tools/check_breaking.py --entry WgRun --extra "$EXTRA" --report worldgen-region-checks.json
