#!/bin/sh
# Rebuild every prototype sprite from scratch: render -> .dmi -> comparison sheet.
# Usage: standalone/remastered/art/run_pipeline.sh   (from any directory)
set -e
ART="$(cd "$(dirname "$0")" && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
rm -rf "$ART/build/renders"
"$BLENDER" --background --factory-startup --python "$ART/pipeline/render_sprites.py"
python3 "$ART/pipeline/build_dmi.py" --sizes 32 64
python3 "$ART/pipeline/make_comparison.py"
