# Enhanced 64×64 artwork

`Goblins-standing-front-64.png` is the first actual 64×64 RGBA design sprite in the enhanced artwork style. It contains one front-facing standing Goblin. Artwork comes from the built-in image generator; the export step only crops, sizes and places it.

The selected version uses nearest-neighbor resizing and a 48×50 content region at `[8,10,56,60]` inside its 64×64 transparent frame. Its feet have a four-pixel bottom margin. This is a design-frame size, not a claim of alignment with existing game equipment.

`source-art/` preserves the generated transparent source. `pilot/` contains the recorded resize variants and provenance reports. V1 variants are rejected because faint pixels in the distant transparent margins caused the Goblin to be scaled too small. V2 uses an explicit crop; every discarded nonzero-alpha pixel had alpha1/255. No visible artwork was redrawn by the exporter.

`../_meta/goblin-enhanced-64.json` records the selected asset, generation prompt, export report and review. The single frame does not complete a source sheet; all animation and missing-limb states still need consistent enhanced outputs. 3D conversion comes later.
