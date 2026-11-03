# North-facing wing corrections

The user approved the first Vampire design's original bottom four flying sprites.
The separately generated VampireFly design was rejected as a different character.
The approved north view now draws wing roots in front of the back. South, East and
West are retained byte-for-byte in `Vampire-flight-approved-north-fixed.png`.
This is one approved appearance per direction; a complete matching flight loop
is still pending. Its converter job is recorded in `vampire-job.json`.

DemonFly, GargoyleFly and the flying gargoyle eye variants draw their north-facing
wing membranes in front of the upper back, following the user's later correction
that roots alone were insufficient. Other directions and all ground gargoyle rows
retain their registered source cells. See `verification.json` and
`vampire-verification.json` for exact unchanged-cell checks.

Creative changes used the built-in image generation tool. `generation.json` and
individual prompt files record those edits. Image extraction and atlas assembly
are mechanical packaging steps; no Python pixel painting was used.

`register.py` detects the actual separated source sprites before placing them in
square cells. Some generated source sheets did not place complete wings within
mathematically equal cells; this avoids carrying clipping into the 64-pixel export.
`assemble.py` replaces only the north cells with the native generated edits.
Backups are retained beside the active source sheets.

Updated sheets are copied into Dungeon Master Sample. The updated races/hybrids
gallery includes these sheets, 64-pixel exports and playback of the supplied
movement frames. Full limb-loss, sleep, armed and hybrid walking sheets remain
pending and are tracked separately in `../full-states/coverage.json`.
