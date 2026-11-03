# Short-leg kick: side and back

The user's chosen side kick is shortened and newly drawn from behind. The rear views show a sideways kick seen from behind, not a northward kick into depth. Four impact-pose drafts; not a complete animation or game integration.

- `index.html`: side/back comparison.
- `short-kick-turnaround.png`: 2 × 2 transparent atlas, 80px cells.
- `pixel-preview.png`: integer 5× preview without smoothing.
- `side-east.png`, `side-west.png`, `rear-kick-right.png`, `rear-kick-left.png`: individual cells.
- `generated-draft.png`: original built-in image_gen output.
- `prompt.txt`: exact generation prompt.
- `chosen-pose.png`: user-supplied pose reference.
- `build.py`: reproducible pixel extraction and packing; reuses the curated set's palette conversion.

The right-column cells are exact horizontal mirrors of the selected left-column drawings. New rear anatomy came from drawing, not mirroring the side view. Native exports use the existing 16-color palette, binary transparency, a fixed scale, and nearest-neighbor sampling. Their mirrored pixels, alpha and clear cell borders are checked during the build. Character continuity beyond these mirrored pairs remains an artistic review item.
