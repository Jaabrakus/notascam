> Retained experiment: the latest request is enhanced AI artwork as 64x64 frames first, with 3D conversion later. This pilot is not the current production target.

# Native-size voxel renderer

This is the new production direction: enhance the editable voxel models behind the original eight-angle views, then export sprites at the original per-file frame size. The source pack uses 64×64 cells for 646 sheets and 32×32 cells for 23 sheets.

## Human pilot

`pilot/` contains four baseline/enhanced pairs at yaw 0°, 45°, 90°, 180°, with pitch 37°. Every individual sprite PNG is **64×64 RGBA**, rendered directly at that size. `Human-comparison-6x-nearest.png` is enlarged only for inspection.

The enhanced version changes per-voxel illumination and restrained crease shadowing before rendering. Model geometry, feature colors, camera, scale, horizontal center and ground anchor match the baseline. Independent checks passed: identical paired alpha masks, readable eyes, no frame-edge contact, finite rendering calculations and matching output hashes.

This is **one standing pose at four angles**, not a complete game atlas. Matching the voxel baseline alpha does not establish compatibility with the original flat DMI silhouette or equipment layers. Full animation/state/direction export and runtime alignment remain pending. No runtime assets have been replaced.

## Reuse and caching

Run the delivered prototype with:

```sh
python3 /Users/kiwimango/Downloads/BOTD-sprites-enhanced/_tools/native_voxel_pilot.py
```

It locates the source repository through `_meta/manifest.json`; `BOTD_PROJECT_ROOT` can override that location. An unchanged run reuses existing files after checking the recipe and all output hashes. Changes to source voxel code, model DMI inputs, rendering settings, dependencies or output files invalidate the cache. The unchanged-run and relocated-folder checks passed with zero new renders.

The prototype currently handles the Human pilot only. The full production renderer must extend this method across every source state, frame, race and equipment family while retaining native metadata and verifying alignment. The game should load exported sprites; rendering belongs in the asset-building step.

Settings, inputs and checks: `pilot/pilot-report.json`. Independent review: `../_meta/native-voxel-pilot-review.json`.
