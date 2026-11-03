# GOA reusable animation rig — Human male profile

**Review:** [Why the Human does not yet match the approved Elf, and the correction plan](README-REVIEW.md).

Second character on the rig from `GOA Reusable Animation Rig v1` (rig-package-16), made 2026-10-30 to test the
README's "adapt another character" recipe. The renderer, clips, gear and timing are the Elf package's, unchanged
(`source/`, `rebuild.py`). Only the character changed: `profiles/human-male.json` and the `human-male-*` PNGs in
`preview/assets`.

Start with `preview/index.html` (self-contained, opens from disk). Or serve the folder:

```
python3 rebuild.py profiles/human-male.json
python3 -m http.server 8881 --bind 127.0.0.1
```

## Where the Human came from

- Body: the approved male Human sheet, `Dungeon Master Sample/Approved Sprites/Male/Human/base/sprites.png`
  (256x192, columns S/N/E/W, rows idle / walk A / walk B). A copy is in `inputs/sprites.png`.
- Part boundaries: the game team's fine zones for that sheet (`inputs/fine.png` + `fine.json`, one body part per
  pixel: skull, face, ears, neck, chest, belly, hips, shoulder/upper arm/forearm/hand per side, thigh/shin/foot per
  side) and the joints where those zones meet (`inputs/Human.json`).
- Cutting: `tools/cut_from_finezones.py Human human-male "GOA Human male"`. It reads the three inputs, writes the
  15 parts per facing, the three drawn walk bodies and heads per facing, and the profile. Nothing was hand-drawn.

## What the cutter does (so you can judge it)

1. **Parts.** head = skull + face + ears (+ hair/horns when a race has them); torso = neck + chest + belly;
   pelvis = hips (the shorts' waistband on this sheet; the shorts legs ride on the thighs). Arm pixels are split
   between upper arm and forearm by which bone they lie nearest; the hand zone is the hand. Legs the same way
   around the knee; the foot zone is the foot.
2. **Joints.** Shoulder, elbow, wrist, hip, knee, ankle, neck and waist from `inputs/Human.json` (idle frame), rounded
   to whole pixels like the Elf profile. Same four-view order and part names as `profiles/elf-male.json`.
3. **Hidden anatomy.** Every upper arm, forearm, thigh and shin gets a rounded filler at the joint it shares with its
   neighbour (the segment's own main colour, no outline, like the Elf's joint caps). Thighs are under the shorts on
   this sheet, so they are skin-coloured fillers the width of the shin, hidden by the pelvis at rest. Where an arm
   or fist covered the torso or shorts, the body colour of that row is put back and the body edge outlined.
4. **Side views.** The idle East/West cells draw only the near arm. The far arm is the near arm's parts copied
   7 px behind the shoulder and darkened 18 %, the same offset the Elf profile uses. It only shows when a clip
   reaches with the far arm (two-handed grips, bow).
5. **Grips.** Guard-hand positions are the Elf's offsets from the shoulder, applied to the Human's shoulders and
   clamped to the arm's reach.
6. **Joint colours.** Sampled from the sheet at each elbow, wrist, knee and ankle.

## What to check

- `review/keyframes.png`: 12 clips at their hit, release or mid time, four views, 1x.
- `review/zoom.png`: six of those frames at 3x.
- `review/parts-<View>.png`: every part per facing at 6x with its joints marked (green). The red boxes are the
  part bounds.
- In the viewer, scrub slash, thrust, throw, bow_shot and walk_armed at 4x with Joints on.

## Known approximations

- The bow and throw targets in `source/engine.js` are still the Elf's coordinates; they were not retuned for the
  Human's shorter arms and bigger fists. South bow draw sits on the chest.
- Fillers are flat colour. A limb swung far from rest shows a flat cap, not drawn shading.
- The far side-view arm is a copy, not drawn art.
- The chest's top corner under the shoulder is given to the arm by the zones, so a raised arm leaves a small notch
  at the shoulder.
- Verified only by eye at the frames above; no baked `exports/` sheets, no verification reports.

## Doing the next race

Any sheet with fine zones works the same way: copy its `sprites.png`, `fine.png`, `fine.json` and `<Race>.json`
into `inputs/` (or let the tool find them in the Dungeon-Master-master repository) and run the cutter with the
race name and a new slug. Races with tails, wings or hair need those zones mapped (hair → head, tail → pelvis).
