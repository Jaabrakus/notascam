# Human native voxel pilot

The eight `Human-yaw-*-64.png` exports are actual **64 × 64 RGBA** frames rendered directly from the existing editable `inflate2` voxel model. The baseline and enhanced versions use identical geometry, camera, rasterizer, outlines, and alpha masks.

The enhanced version changes the model's diffuse illumination before rendering and adds mild ambient occlusion computed from the voxel geometry. The existing feature mask preserves painted eyes and other facial details. No AI reference image, 2D relighting, or resized illustration is used as a game sprite.

`Human-comparison-6x-nearest.png` is a clearly labeled presentation preview enlarged 6× with nearest-neighbor interpolation. Its dimensions are not the native sprite dimensions.

`pilot-report.json` records settings, source and export hashes, occupied voxel count, alpha masks, frame bounds, and numerical checks. The independent review is stored at `../../_meta/native-voxel-pilot-review.json` when available.

This is one standing pose at yaw 0°, 45°, 90°, and 180°, with pitch 37°. It is **not a complete game atlas**. No source or runtime assets have been replaced, and matching the original flat 2D atlas registration, animation, equipment attachment, and remaining states is not claimed.

Reproduce from the project root:

```sh
python3 output/imagegen/BOTD-sprites-enhanced/_tools/native_voxel_pilot.py
```

The script writes only this pilot folder; the independent review file remains separate.

Unchanged runs reuse the cached files after checking the complete recipe, all 51 voxel Python source files, relevant DMI inputs, and all nine generated image hashes. Settings or source changes rebuild the pilot; a rebuilt report starts with visual review pending. Cached runs preserve existing files and review metadata. `cache-validation.json` records the cache and portability checks.

The delivered script locates the source repository using `_meta/manifest.json`'s `native_source_repository_root`, so moving the enhanced folder to Downloads works. If the original source repository moves, set its new location:

```sh
BOTD_PROJECT_ROOT=/path/to/Dungeon-Master-master python3 /path/to/BOTD-sprites-enhanced/_tools/native_voxel_pilot.py
```

Use `--cache-key-only` to inspect the current recipe key without writing or rendering. The renderer is reusable and requires the editable source repository plus NumPy and Pillow; this folder is not a standalone copy of that repository.
