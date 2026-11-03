# Second pass: creatures and magic (polish-creatures)

Looked again at taming, abilities, magic gear, runes: last night's 16 fixes all pass on build 68's live game (CRP 9, CRQ 6, CRR 4 checks, 0 errors). One more unanswered interaction found and fixed.

| Fix | Before | Now | Landed |
|---|---|---|---|
| Feed order answers | Feeding a chained beast with a feeder who can't reach it (40 s) left them standing, labelled "Feeding"; a feeder whose meat was gone fed nothing; both silent | "[unit] couldn't get to [beast] to feed it." / "has no raw meat left to feed it with."; status clears | yes 08:09 (gate pass, combat 32/32) |

Proof: arena test CRS (tests/crea_polish4_test.dm), before FAIL x2, after PASS x2.
Speed: none measurable; runs on a feed order that fails, once per 40 s at most.

Still staged for the owner's eye: staged-dragon-tint. Open owner items unchanged from the 10-26 devlog.
