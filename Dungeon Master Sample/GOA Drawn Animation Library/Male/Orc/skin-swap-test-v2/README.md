# Orc skin-swap test

The same body-only Orc pose pixels are recolored using grey and red skin palettes
sampled from the existing Ashen and Hellblooded Orc art. Only selected green skin
RGB pixels change; alpha and every pixel outside the skin mask are identical.
Eyes, tusks, shorts, outlines and pose geometry are preserved. This is a palette
demonstration, not a finished recreation of either hybrid appearance: horns,
markings and tails require additional parts.

Open comparison.png for the first pose in all four directions. The individual
PNGs retain all sixteen poses. verification.json records the pixel comparisons.
The input is a generated drawing draft; recoloring does not make it a registered
native game atlas. No smoothing or resizing was applied.
