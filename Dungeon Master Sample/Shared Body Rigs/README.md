# Three shared builds, six body masters

{
  "templates": 6,
  "builds": 3,
  "characters": 174,
  "female": 80,
  "headAttachmentsChecked": 2088,
  "bodyPoses": 72,
  "displayPresets": [
    "Standard",
    "Small",
    "Large stocky",
    "Small stocky"
  ],
  "originalHeadsRedrawn": 0,
  "equipmentRefitted": false,
  "templateSource": "Original approved sprite pixels; exact male/female Elf and Orc references provided by user",
  "polishVersion": 2,
  "hybridAppearances": 146,
  "bodiesWithIdentityMarks": 65
}

Standard uses Elf proportions; stocky uses Orc proportions; small uses Goblin proportions. Each has a male and female sheet with three poses and four directions. Dwarves use the stocky rig at a smaller whole-character display scale.

All existing race/hybrid heads are extracted as unchanged RGBA pixels and attached by integer translation. No head scaling, repainting or regeneration is used. Original donor atlases and hashes are included. Longer hair and wings/tails are identity layers. Extraction boundaries still need visual review.

Each body silhouette is identical to its master: only palette tint varies. Equipment must be authored once for each of the six fixed masters; no per-race armor stretching is performed. Helmets require head-specific clearance.

Body cores are 64×64 logical frames. Composites use padded 128×128 frames with a 64px body at (32,32), protecting large heads and horns. These sheets are not live-game integrated. Injury states, attacks, sixteen facings and the new fixed-rig armor sheets remain pending.
