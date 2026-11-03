# Drawing progress

Requested scope: all 97 library entries across 29 inventoried base appearance families (2,813 coverage entries). Some entries are composite sequences and can reuse constituent frames; these are not all separate drawing jobs. Hybrid variants still need parent-body matching.

Completed drawing draft: Male Orc slash, 16 poses across four directions. First generation was rejected for missing row and duplicate swords; the corrected version is saved as Male/Orc/sword-swing-drawn-v1.png.

Status: visual design draft, not production-ready. The generated image is 1254 by 1254 with transparency; poses need native-scale conversion, individual registration and playback review before game use. No existing game assets were overwritten. The full library remains pending.

Prompts and correction are preserved in prompts/. Built-in imagegen was used. work-queue.json records every requested coverage entry and sequence dependencies.

## Updated art requirements

The user rejected the weapon-bearing generated drawing. Draw body poses only, including weapon-gripping hands and shield holds/blocks/bash/recovery, while keeping equipment separate. Copy original source pixels to preserve identity between frames. Do not smooth, beautify or regenerate complete characters per action.

29 original base appearance sheets are frozen byte-for-byte in source-masters/. source-lock.json records exact hashes and palettes. The body-only generation already running when the pixel-copy request arrived is preserved as a rejected draft: it is not pixel-matched or registered at native scale. No production-ready new animation sheets exist yet.

## Reusable appearance layer proof

Ashen horns/body markings and Hellblooded horns/tail now use copied source pixels across all 16 Orc draft poses. The reusable JSON-driven pipeline is standalone/goa-races/character-retarget/appearance_layers.py; its guide is APPEARANCE-LAYERS.md beside it. The current saved batch uses pipelines/orc-appearance-layers-v3.json and writes Male/Orc/appearance-layer-test-v3/.

30 feature layers, 120 placements; donor RGBA preservation, unchanged body pixels outside overlays, frame containment and repeat-run caching passed. Only Orc placement is calibrated; other races require their own source features, body masks and attachment records. The underlying body sheet remains a generated draft, not production game art.
