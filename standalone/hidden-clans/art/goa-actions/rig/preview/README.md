# Approved GOA Human Male animation rig

User-approved visual state saved on 2026-10-31.

Open `preview/index.html` to view it. Read [README-CLAUDE.md](README-CLAUDE.md) before making changes.

## Final accepted rules

- North shield hold: supporting left arm visible over the shield back, behind the body.
- North sword: behind the right arm; right arm behind the body.
- North forearms: behind the upper arms.
- Front/back arms: separated wrist cuts, small elbow/shoulder backing and cleaned internal dark seams.
- East: right leg leads and draws in front.
- West: original pose/order retained; spiked thigh/shin artwork replaced without swapping the legs.
- Side feet: separate foot/shin ownership at the ankle, with correct source-frame pivots.
- Bow: East mirrors the West master; preserve the established recovery.

## Reproduce this saved state

```sh
python3 rebuild.py
python3 -m http.server 8881 --bind 127.0.0.1
```

Open http://127.0.0.1:8881/preview/. Rebuild uses `profiles/character.json`, `source/engine.js`, and the packaged PNGs. Do not rerun a generic cutter over this accepted profile or replace its source renderer with the unmodified Elf renderer.

## What is saved

- `profiles/character.json`: calibrated joints, source pivots, image references and pose targets.
- `source/`: current renderer, viewer and original clip data.
- `preview/assets/`: source and repaired character pieces plus gear.
- `arm-cut-review.json`: original references and applied arm corrections.
- `README-CLAUDE.md`: detailed cutting, layering and repair instructions.
- `accepted-state.json`: approval scope and build status.
- `manifest.json`: hashes of this saved package.

The user approved this current visual result. That is separate from an exhaustive check of every possible animation/body combination. This folder has no newly baked 97-clip Human export set, and does not change the live game. Other characters still need calibration and visual review.
