# GOA Orc male animation rig — review candidate

Third character on the GOA animation rig, after the approved Elf and Human. Open `preview/index.html`.
Read [README-CLAUDE.md](README-CLAUDE.md) before changing anything.

- Body: the pack Orc sheet, original art, cut by the Orc's own zones (not Human proportions).
- Joints: the staged Orc skeleton (`inputs/Orc.json`), matched to this body (the side shoulder sits where the
  Orc's own walk frames swing the arm from); guard grips from the Orc sword-and-shield draft.
- Heads are whole heads, cut along the jaw outline, so the mouth moves with the head. The side bow keeps the
  approved construction: the front body with the real East/West head.
- Pieces are original sprite pixels. Ends and edges that a neighbour covers at rest are rounded, backed and closed
  with the sprite's outline colour, so leans and swings open no gaps. The idle pose is pixel-identical to the drawing.
- Renderer: the approved Human renderer plus gated flags for this body (`tools/patch_engine.py`): front/back legs
  shorten instead of buckling sideways, the side-view head is drawn over a forward-reaching arm, and enclosed
  one-pixel seams between rotated pieces are filled. With the flags off it is the approved renderer.
- Review sheets: `review/` (approved Human and Orc side by side, with and without equipment).

Status: needs the owner's visual review. Not baked, not in the live game.
