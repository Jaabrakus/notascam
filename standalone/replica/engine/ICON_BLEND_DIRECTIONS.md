# Blend source direction fallback

The private candidate fixes a verified shared-runtime omission: an image blend
with no source art for the destination direction now uses the source's SOUTH
cell. It changes only `DreamIconOperationBlendImage.ApplyToFrame`. The installed
runtime remains the lead's TypesOf build until the lead promotes this candidate.

The [staging manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-blend-staging.json)
records the precise source/runtime diff, hashes, reports and unchanged installed
baseline. Candidate runtime is
`3879e6f7ad058d41d6fd8e65082f188829696489136515b1aadbf5b0bef590db`.
No original sprite, game source, client, parser, save or normal application was
changed by this task. All tests are headless private worlds.

## Reference evidence

The [oracle runner](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/audit_icon_blend.py)
executes 114 cases using unchanged Human, Female, BoneItems and MetalObjects
art in BYOND 516.1655 and the replacement runtime. It exports both inputs before
each blend, so a constructor discrepancy cannot masquerade as a Blend result.
It covers one/four/eight-direction destinations and sources; explicit SOUTH,
NORTH and EAST/frame-2 filters; all seven blend modes; seven half-alpha color
controls; and two separately identified frame-expansion examples.

The [official Blend reference](https://www.byond.com/docs/ref/info.html#/icon/proc/Blend)
describes the seven pixel operations. Direction fallback below is established
by the retained executable oracle, rather than inferred from that page.

| Destination/source condition | Measured BYOND behavior | This increment |
| --- | --- | --- |
| Source contains destination direction | Use that source direction | Preserved |
| Source lacks direction | Use source SOUTH | Fixed |
| Four-direction source, diagonal destination | Use SOUTH, not EAST/WEST | Fixed |
| Explicit source direction/frame filter | Filtered artwork is stored as SOUTH and applies to all destination directions | Fixed |
| Destination needs extra directions | Copy destination SOUTH before blending each new direction | Deferred |
| Source/destination frame counts differ | Frame repetition/expansion behavior | Deferred |

The renderer's `ParsedDMIState.GetFrames` is deliberately not reused. Its
diagonal EAST/WEST fallback differs from the measured Blend behavior. The
candidate leaves existing source directions, bounds, pixel/color/alpha math,
frame limits and destination allocation unchanged.

The [before report](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-blend-before.json)
has 37 complete matches. The
[candidate report](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-blend-candidate.json)
has 78. All 72 single-frame cases which need no destination expansion match
exactly for OVERLAY, UNDERLAY, ADD, SUBTRACT, MULTIPLY and AND. Every extracted
input matches BYOND. The seven color controls and all existing source-direction
pixels remain identical to the old runtime. Original assets are unchanged.

`ICON_OR` already differs even when the source contains the requested direction;
its existing bitwise arithmetic is separate from this lookup fix. Half-alpha
color OVERLAY also has an existing arithmetic discrepancy. These cases remain
in the audit and are not counted as exact parity.

## Actual game impact and remaining limits

The unchanged
[MakeBody routine](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Creatures/Death.dm:89)
blends a single SOUTH underwear cell onto female Human/Elf/Dwarf bodies. The
[real-game candidate audit](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-fallback-blend-candidate.json)
and its
[independent repeat](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-fallback-blend-candidate-repeat.json)
run the same seven original constructor/body variants in both engines.

| Frame-0 body | NORTH mismatched pixels before → after | EAST/WEST before → after |
| --- | --- | --- |
| Human female | 52 → 10 | 56 → 13 each |
| Black Human female | 52 → 10 | 56 → 13 each |
| Elf female | 40 → 5 | 54 → 13 each |

All seven default SOUTH cells stay exact. Every direction of Human male,
Dwarf male, Orc male and Orc female stays exact. Female composite parity is
still incomplete: one previously correct opaque EAST/WEST pixel per female
control changes away from the reference, while total mismatch decreases.
Later missing-state Hair/BlackHair construction and destination/frame
expansion remain independently documented gaps. No unexpected visible pixels
appear in transparent reference regions. Bodies are created SOUTH; this audit
does not claim a newly observed normal-play facing change.

## Verification and reproduction

The [focused checker](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/check_icon_blend.py)
passes 588 assertions, including the 72 exact image cases, unchanged controls,
unchanged oracle/input metadata, and quantified real-body comparisons.
The counts include structural assertions; they are not 588 distinct gameplay
scenarios. The existing generated-icon 11, idle/walk-variant 81, rewind 22 and
buffer 120 checks also pass on the private runtime. Buffer verification uses
the candidate's first real-game run as its opaque-pixel baseline, then checks
an independently started repeat; the separate Blend checker records the
intentional differences from the old runtime instead of weakening old reports.

All executions completed by 06:30:25 UTC, before the lead's 06:30:55 compiler
standard distance update. They used `_Standard.dm` SHA-256
`9bdcaceeffc68991d167c71d56f2eed56859fb9e1068b5cedc6031e6c921432c`.
This runtime patch does not change the compiler or standard library.

```sh
python3 standalone/replica/tools/audit_icon_blend.py \
  --server /tmp/dm-runtime-audit/blend-source-server \
  --label fresh-candidate --port 12193 \
  --reuse-reference standalone/replica/reference/icon-blend/before
python3 standalone/replica/tools/check_icon_blend.py \
  --candidate fresh-candidate --label fresh-check
```

Use a fresh label for each run. The retained private server, builder source and
all original evidence stay available for lead review. Promotion remains a
separate lead-owned action; no packaged app or runtime was installed here.
