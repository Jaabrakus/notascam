# Deepguard fitting polish — revision 2

- Sample the original full-resolution equipment once into the final 64px frame, avoiding the earlier double resize.
- Align each helmet independently of torso height. Keep the visible eyes clear on human, dwarf and goblin, including side views.
- Raise and widen the goblin chest, move its arm pieces outward, and fit its helmet without hiding its ears.
- Give the dwarf a broader cuirass while keeping its greaves and boots at their own width.
- Hide the underlying bare feet only while boots are equipped. Removing boots restores them.
- Restrict each extraction to its original figure bounds to prevent neighboring figure fragments, and omit pale source-body edge pixels from equipment layers.
- Keep the existing eight removable slots, per-facing adjustments, saved fitting recipes and PNG exports.

The previous comparison is preserved as `before-polish.png`. Source artwork remains unchanged. These are still four standing views; female/hybrid exceptions, motion and sixteen directions remain pending.
