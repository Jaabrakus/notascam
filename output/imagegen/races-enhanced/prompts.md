# Enhanced race turnaround sheets

Created using the built-in image_gen tool on 2026-10-24.

Files:
- races-8-angles-heads-enhanced.png: enhanced head-and-shoulder reference sheet.
- races-8-angles-enhanced.png: enhanced full-body reference sheet.

Both sheets contain 13 races and eight yaw views. These are generated art reference sheets; frame bounds and source pixel dimensions are not preserved for direct atlas replacement. Original files were left untouched. No game asset references were changed.

## Head sheet prompt

Use case: identity-preserve.
Asset type: enhanced fantasy voxel / pixel-art character HEAD TURNAROUND reference sheet.
Input image 1 is the EDIT TARGET, a 13-row by 8-column head-and-shoulder sheet. Input image 2 is supporting full-body identity reference only. Output ONE enhanced version of image 1, not a collage of the two sheets.

Preserve the entire original grid: exactly 13 race rows, exactly eight views per row, all 104 portraits visible, same row order and column order. Preserve the tall portrait canvas proportions, charcoal-gray background, head-and-shoulder framing, and small pale-gray labels. Leave clear gutters. The eight columns show the SAME character rotating in 45 degree steps with the same slightly elevated orthographic camera. Keep the source-facing directions: front, front-three-quarter toward screen right, right profile, rear-three-quarter toward screen right, back, rear-three-quarter toward screen left, left profile, front-three-quarter toward screen left. The back view has no face. No repeated front views.

Enhance the artwork significantly while retaining its unmistakable chunky voxel proportions and crisp pixel-art edges: deliberate pixel clusters, clear silhouettes, cleaner contours, refined three-to-five-tone material shading, softly warm top-left light with cool shadows, expressive well-defined eyes, readable noses and mouths, restrained ambient occlusion. Replace noisy banding with intentional plane shading. Keep small-scale readability. No blur, gradients, painterly smoothing, realistic anatomy, or glossy plastic. Preserve the original base characters and all defining colors, hair shapes, ears, horns and body proportions.

Race-specific polish in the exact top-to-bottom order:
1 Human: warm sandy skin, original close-cropped blond head shape, clearer brow and subtle warm skin shading.
2 Dwarf: stocky broad amber-brown head, robust jaw and brows, warm ochre shading, preserve original hair and mouth design.
3 Night Elf: dark midnight-indigo skin that remains legible, silver-gray hair with organized locks, pointed ears and vivid red-white eyes.
4 Orc: deep rich green, pronounced brow and jaw, red eyes, small ivory tusks and clear ears; reduce harsh neon clipping.
5 Goblin: smaller olive-green face, large round-pointed ears, bright yellow eyes, mischievous features.
6 Kobold: original ochre/olive skin and huge upright pointed ears with reddish inner ears, angular little muzzle, yellow eyes.
7 Lizardman: teal and turquoise scale plates, small coherent scale clusters following head planes, slit golden eyes.
8 Frogman: bright leaf/lime green with controlled highlights, broad rounded amphibian head and white eyes, defined mouth; eliminate blown-out neon.
9 Vampire: pale ivory skin, original large pointed ears and forehead ridge, ruby eyes, tiny fangs, cool lavender-gray shadows.
10 Demon: crimson red, preserve the exact ivory horn pair and golden eyes, richer maroon shadows and readable teeth.
11 Gargoyle: weathered medium-gray stone, original ears/ridges, discreet cracks and chiseled facial planes, clear eyes.
12 Skeleton: ivory skull, well-defined charcoal sockets, nasal cavity, teeth and cheekbones; preserve the skull silhouette.
13 Zombie: preserve the stylized red/pink and dark-teal exposed-undead design with coherent pixel clusters and subtle material contrast; same cartoon intensity as source.

Text: column labels exactly "yaw 0", "yaw 45", "yaw 90", "yaw 135", "yaw 180", "yaw 225", "yaw 270", "yaw 315". Row labels exactly "Human", "Dwarf", "Night Elf", "Orc", "Goblin", "Kobold", "Lizardman", "Frogman", "Vampire", "Demon", "Gargoyle", "Skeleton", "Zombie". No title or added text.
Constraints: This is an enhancement of the supplied character roster, not replacement designs. Stable anatomy, ear and horn placement, palette and facial identity throughout each eight-angle sequence. All 13 rows must fit uncropped, including Skeleton and Zombie. Do not add armor, accessories, weapons, hats, scenery or new characters. Render a large, finely resolved sheet close to the original 1870x2760 proportions.

## Head sheet targeted correction

Use case: precise-object-edit.
Input 1 is the EDIT TARGET: a polished 13-race, 8-angle head-and-shoulders sheet. Input 2 is the ORIGINAL head sheet as a framing reference only.
Make ONE targeted correction to input 1: the bottom row labeled "Zombie" incorrectly contains full bodies. Replace ONLY these eight bottom-row sprites with enlarged HEAD-AND-SHOULDERS portraits, cropped at the upper chest, matching the framing and visual head size of the other twelve rows. Use the exact Zombie heads and eight directions already present in input 1; enlarge them into the bottom-row cells. Each portrait must fill its cell similarly to the Skeleton row just above. No legs, feet, waist or floor shadows should appear in the Zombie row. Keep the eight views in order: front, right front three-quarter, right profile, right rear three-quarter, back, left rear three-quarter, left profile, left front three-quarter. Preserve red/pink, ivory and dark-teal colors, head details and crisp voxel pixel art. Keep the "Zombie" label aligned to the row.
Preserve ALL other pixels and design choices as closely as possible: the first twelve rows, 13-by-8 grid, angle headings, labels, charcoal background, character identities, colors, lighting and composition. Do not redraw the other races. No added title, accessories, objects or decorative elements. Return the complete corrected sheet at the same aspect ratio, uncropped.

## Full-body sheet prompt

Use case: identity-preserve.
Asset type: enhanced fantasy voxel / pixel-art FULL-BODY character turnaround sheet.
Input 1 is the EDIT TARGET, the original full-body sheet. Input 2 is a supporting enhanced HEAD STYLE AND IDENTITY REFERENCE ONLY. Output ONE polished full-body version of image 1. Do not combine sheets or use portrait framing.

Composition: preserve the tall portrait canvas and the complete exact 13-row by 8-column matrix, 104 full-body characters. Every figure visible from top of head and horns to bottom of feet. Keep original race-relative heights, compact voxel proportions, neutral standing poses and slightly elevated orthographic camera. All eight figures in each row share scale and ground baseline. Small consistent dark contact shadows. Preserve dark charcoal-gray background, clean row gutters and small pale-gray labels.

Rotation: same character in eight 45-degree steps across each row. In order: front, front-three-quarter facing screen right, right profile, rear-three-quarter toward screen right, back, rear-three-quarter toward screen left, left profile, front-three-quarter facing screen left. Match original yaw conventions exactly. No face on back views, no repeated front views.

Enhance with the same crisp chunky pixel-art style and refined shading as input 2. Make silhouettes and joints readable: separate hands from hips, clarify shoulders, elbows, knees, ankles and feet with deliberate pixel clusters, strong clean contours, carefully controlled 3–5-tone material ramps, warm upper-left highlights, cooler shadows. Retain the original unclothed stylized modular base bodies; do not add equipment, clothes, jewelry, weapons or hair changes. Use restrained highlights, intentional plane shading and clear eyes. No blur, painterly smoothing, soft gradients, smooth 3D or glossy plastic.

Exactly these 13 rows top-to-bottom, matching all head identities and proportions from source:
1 Human: sandy warm skin, original blond close-cropped head, normal compact build.
2 Dwarf: short broad stocky amber/ochre character, original broad brown head and jaw.
3 Night Elf: slender indigo character, gray hair, red-white eyes; lift darkest blue values enough to reveal limbs.
4 Orc: muscular rich green, red eyes, ivory tusks and strong ears.
5 Goblin: small olive-green character with broad ears and yellow eyes.
6 Kobold: small ochre/olive character, large upright pointed ears with red interiors and yellow eyes.
7 Lizardman: teal/turquoise scales, golden slit eyes; use coherent scale plates rather than visual noise.
8 Frogman: broad bright leaf-green amphibian, white eyes, broad mouth and wide webbed feet; rich controlled green highlights.
9 Vampire: pale ivory character with distinctive tall ears, red eyes and subtle cool-gray shadows.
10 Demon: deep crimson character, paired ivory horns, golden eyes and teeth; use readable red midtones.
11 Gargoyle: medium-gray carved stone character with original ears/ridges, subtle facets and cracks, visible limb shading.
12 Skeleton: ivory skull and bones, dark sockets, clearly separated ribs, spine, pelvis and limbs; exact source anatomy.
13 Zombie: source stylized exposed undead red/pink, ivory and dark teal patches, coherent pixel clusters and readable joints; same cartoon intensity as source.

Text: exact column labels "yaw 0", "yaw 45", "yaw 90", "yaw 135", "yaw 180", "yaw 225", "yaw 270", "yaw 315"; exact row labels "Human", "Dwarf", "Night Elf", "Orc", "Goblin", "Kobold", "Lizardman", "Frogman", "Vampire", "Demon", "Gargoyle", "Skeleton", "Zombie". No title or extra text.
Critical invariants: ALL 13 races and ALL 8 directions, complete full bodies, original order, original small-character proportions, consistent face/head design and material colors across views, no additional accessories. Entire Skeleton and Zombie rows fit within the sheet. Maintain the source tall canvas proportions (about 1710 by 3540) with high detail.

