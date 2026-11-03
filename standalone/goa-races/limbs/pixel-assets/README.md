# Sprite-pixel limbs and missing-limb bodies

These pieces come from the approved body sprites, sampled once into their 64px fitting space. No replacement limb anatomy is generated. Pure part pixels keep their original RGBA; masking removes exactly those pixels from the body. Wounds are a separate overlay of at most four existing-palette pixels per visible cut. Bone and stone do not receive red blood.

Each body folder contains normal/core references, four source limb layers and masks, 16 canonical missing-limb combinations, optional bloody versions, PNG/DMI atlases, timing/slot metadata and reconstruction proofs. DMI walk playback encodes neutral/step A/neutral/step B. That preserves existing poses; it does not establish full anatomical calibration of every motion frame.

Reuse the existing LimbFling/RmG3Limb/ragdoll path. existing-game-binding.json records the slot names, the different Surgery/G3 bit orders and the existing blood asset. These are asset exports, not a replacement simulation or a completed live-game integration. Updated body textures and their part maps must be registered together when integrating. The classic32px item icon path is separate from these64px body assets.

The default15 base families have a visual cutout review. Other appearances exported with --all remain shared-mask calibration drafts. Pure RGBA reconstruction proves preservation, not correct anatomical segmentation. Original images are never overwritten.
