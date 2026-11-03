# Orc rig — notes for the next AI (ChatGPT, Claude or anyone)

## The sprites are original art

Every body pixel on this sheet is original GOA art made for this game: the pack Orc,
`Dungeon Master Sample/Sprites/Male/Orc/base/sprites.png` (its atlas calls it a "generated walk draft"; that label
is old, the owner confirmed on 2026-10-31 these are all original). The same holds for the Elf, the Human and the
other race sheets.

So: do not redraw, repaint or recolour body pixels. Cut the art apart and put it back together. Where a moving
piece uncovers a surface the idle cell never shows, take it from another frame of the same facing. The only
pixels this package adds are outline-coloured closures on piece ends that another piece covers at rest (see
below); that is what the approved Elf's "rounded complete limb ends" are too.

## Joints: the staged skeleton, matched to this body

Every race already has a skeleton: `inputs/Orc.json` is
`standalone/remastered/reports/goa-sprite-test/staged/rig/Orc.json` (the same file the Orc sword-and-shield draft
was built from). Per cell it gives neck, waist, shoulder / elbow / wrist / hand and hip / knee / ankle / toe, in
the zone image's rows, two rows below this sheet (`zoneRowShift` -2). The owner's rule (2026-10-31): the
skeletons exist, match them to each unique body. Chains (`tools/recut_by_zones.py`):

| Chain | Joints |
| --- | --- |
| arm, front/back | skeleton shoulder, elbow; grip = halfway from the skeleton wrist into the fist |
| arm, side | **matched**: the staged side zones call the top third of the arm "chest", so the skeleton's side shoulder sits a third of the way down the arm (y 35.6) and the whole arm swung from mid-chest. The shoulder is put where the Elf and the Human have it and where the Orc's own walk frames swing the arm from: a quarter of the way from the neck to the waist (y 29), at the centre of the arm in that row. Elbow and wrist are the skeleton's. |
| leg, front/back | skeleton hip, knee, ankle; the chain's knee sits on the hip-ankle line (pieces are still cut at the drawn knee) |
| leg, side | skeleton hip, knee, ankle |
| far arm, side | hidden: the near arm's joints moved past the body's centre line, one row lower |

With these joints the renderer's two-bone IK lands on the draft's hold pose, so the draft's guard grips are used
unchanged.

## Pieces: the zone pixels, cut along the lines the artist drew

`inputs/fine.png` + `fine.json` (staged fine zones, with the side-view fix in `zone-fix.json`; the untouched
original is `inputs/fine-staged-original.png`).

- **Head = the whole head.** Head zones, the "neck" rows (inside the face on this body), the tusks, and the chin
  down to the jaw outline. The zones end the head four or five rows above the jaw, so earlier builds left the chin
  and the jaw line on the torso: when the head moved, the jaw stayed behind (the "mouth doesn't move with the
  head" fault, and the "frankenstein turn" in the side bow). The chin is cut along the jaw outline the artist drew
  (`jaw_chin`): the longest dark run 2-6 rows under the head zones is the jaw's bottom line; a crease runs from its
  back end(s) up to the head's bottom row. South has a crease on each side, East and West one, North none.
- **Torso backing under the head.** The chin and the head's bottom two rows get torso pixels copied from the first
  skin pixel below (outline colour on the silhouette), so a tilting head never opens a gap at the neck.
- **Side torso and the seat of the shorts.** The near arm hangs over the back of the body, so the back and the seat
  of the shorts behind the fist are never drawn in the idle cell. Both come from the walk frame in which the near
  arm swings forward (that frame's own arm zones, widened by a pixel, left out), lined up on the visible torso, with
  that frame's own outline. The back runs from the drawn shoulder down to the seat's back edge; anything no frame
  shows is copied from the nearest solid torso skin of the row and closed with the outline colour. The seat goes on
  the pelvis (it stays put while the thighs swing) and under the drawn idle and walk frames. An earlier build drew
  an invented back curving in to the shorts edge visible in the idle cell; when the arm lifted, the body caved in
  behind the hips and only the front half of the shorts was left.
- **Side arm.** The arm from the shoulder joint's row down, plus a round end of the arm's width about the joint.
- **Front/back arms.** Upper arm, forearm, hand zones; the deltoid stays on the torso and the arm carries a round
  end of the same cap pixels about the pivot.
- **Legs.** Front/back: thigh, shin, foot zones (the shorts legs ride on the thighs, the pelvis is the waistband).
  Side: the shorts below the waistband are split between the legs at the midpoint between the shins; the far shin
  and foot reuse the near leg's pieces.
- **Closures and backing** (all hidden while the pose is as drawn): piece ends another piece covers at rest are
  rounded and closed with the outline colour (upper arm under forearm, forearm under fist, thigh under waistband
  and shin, shin under foot). Where a neighbour covers a piece's edge at rest, the piece gets a backing strip
  (copies of its own solid edge skin, outline on the new edge): the South torso under the arms (3 px), the North
  arms behind the body, the waistband under the torso, forearm under fist and upper arm under forearm, thigh under
  shin and shin under foot, and 3 px on the front/back walk torsos (the engine swings the idle arm pieces over those
  drawn frames). Without them, every lean or swing opened a white sliver or a pin-hole.
- **The outline colour is a solid pixel.** The sheet's body pixels have alpha 248-253 and its fringe is faint black
  at alpha 1-127. The outline colour used to be the most common dark pixel, which was that faint fringe, so 345
  closure and edge pixels were drawn almost invisible. Closures, backing and fills now use solid pixels only
  (alpha 128 and up) and never turn a faint fringe pixel solid.
- **Check:** the idle pose rebuilt from all of this is pixel-identical to the drawn idle cell in all four views
  (0 pixels missing, added or recoloured).

## Renderer flags (Orc profile)

`source/engine.js` is the approved Human renderer plus `tools/patch_engine.py`: literal, gated additions. With the
flags off it behaves exactly as the approved Human's.

- `frontLegsSquash` (on): wherever the front or back body is drawn (front/back views and the East/West bow, which
  uses the front body) a stepping or crouching leg keeps its knee on the hip-ankle
  line and both leg pieces shorten along it (a leg bending toward the camera), instead of the knee buckling
  sideways. The Orc's shorts legs are 12-14 px wide and 8 px long; buckled sideways they tore apart.
- `sideHeadOnTop` (on): in East/West (not the bow, not the drawn idle/walk frames) the head is drawn after the near
  arm. This Orc's shoulders sit level with its jaw and its snout reaches as far forward as its arm, so a forward
  slash or throw covered the whole face; now the arm passes under the jaw, as the Human's passes under its chin.
- `closePinholes` (on): after each frame is drawn, a transparent pixel with body on both sides horizontally and
  vertically (within two pixels) takes a neighbour's colour. Separately rotated pieces leave such one-pixel seams
  where they meet (142 in 60 checked frames before, 23 after); real gaps such as an armpit slit or the space
  between the legs are not enclosed both ways and stay open.
- `bowSideBody` (off): an alternative East/West bow drawn on the side body. The side bow uses the approved
  construction instead: the front body with the real East/West head turned to aim. With whole heads that is clean.

## What else changed, and why (condensed history)

- Open cut ends showed as jagged skin at every bend → closed ends (above).
- Deltoid in the arm piece broke the shoulder line at every bend → cap on the torso.
- Elf guard offsets, scaled or not, raised the fists 2–7 px too high → the draft's grips.
- Row-copied torso under the near arm striped the side torso → walk-frame body.
- Near arm cut from a walk frame was swung and foreshortened → idle cell only.
- Tusks stayed on the torso when the head turned → tusks in the head piece.
- Far side leg from a walk frame was a spike → near leg's pieces on the far chain; then no thigh at all → split
  shorts.
- Joints from zone edges put the shoulder on the arm's outline → skeleton joints.
- Side head on the South body for the bow looked like a frankenstein turn → the cause was the jaw: the side head
  had none and the front torso kept its own. Whole heads fixed it; the bow keeps the approved construction.
- Skeleton side shoulder at mid-arm, a second arm swinging out of the chest → matched to the body (joints table).
- Sideways-buckling front/back knees tore the wide shorts legs → `frontLegsSquash`.
- A forward side-view arm covered the whole face → `sideHeadOnTop`.
- White slivers between pieces on every lean and swing → backing strips.
- An independent review (equipment off, beside the approved Human) found the side body caving in behind the hips
  when the arm lifts, invisible closures, pin-holes between rotated pieces and front legs buckling in the side bow
  → back and seat from the forward-arm walk frame, solid outline colour, more backing, `closePinholes`, squash keyed
  on the drawn body.

## Shared with the approved Human

`source/engine.js` is the approved Human renderer (source pivots, lead leg, North draw orders accepted
2026-10-31) plus the gated flags above. The Human's own repair scripts
(`refine_front_back_arms.py` and friends) are not used here: they recolour pixels and cut by Human rows.

## Rebuild

`python3 tools/build_orc.py` rebuilds this whole folder from the sheet, the staged zones and the staged skeleton
(the old folder goes to the Trash; `README*.md` and `review/` are carried over). Steps: stage inputs; side zone
fix; `standalone/goa-races/character-retarget/retarget.py` into a fresh folder; copy and patch the approved
renderer; `tools/recut_by_zones.py`; draft grips, bow targets, flags; copy tools and inputs; rebuild; manifest.

## Review

`review/`: Elf, Human and Orc side by side at key times, the draft hold against the rig's guard, the pieces with
their joints. Check idle_armed, slash .16/.3, lunge .36, thrust .18, bow_ready .5, bow_shot .72/.9, throw .38 in
all four views, with equipment off as well. The idle pose must stay pixel-identical to the drawn idle cell;
`recut-report.json` lists the chains, the chin and backing pixel counts and the side torso's sources.

## Not done

- Not approved by the owner yet. No baked export sheets. Nothing in the live game.
- Front/back heads still tilt with 0.3 of the torso lean, as on the Elf and Human.
- The side throw passes the spear across the face, as the Elf and Human do.
- A raised side-view arm shows its chest-side edge without an outline; the sprite draws a soft crease there, not
  a line, so that edge is left as drawn.
- The far side leg at rest is the near leg's big foot on the far chain, 3 px longer than the drawn sliver.
- Rotated pieces show the renderer's usual nearest-neighbour jaggies (the Human has the same); on this body's big
  fists and forearms they are more visible.
- In the front view, arms raised over the head (chop, slash wind-up) cross the face, as the Human's do; on this
  body the fist covers half the head.
- The guard pose uses the sword-and-shield draft's grips; the fists sit higher and wider than the Human's.
