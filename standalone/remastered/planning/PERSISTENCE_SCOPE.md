# Standalone persistence scope

The packaged lifecycle checks verify original player/unit saves and acknowledged flushes. They do not certify persistence of the whole running world.

| State | Current evidence / behavior |
| --- | --- |
| Player roster, original units, carried inventory | Private new-game/save/reload and two-player isolated reload checks pass on their recorded versions. |
| Saved containment | Carried containers/captives retain containment; orphaned cage flags are reconciled when the ground container was outside the saved graph. |
| Work role, area, auto-unload, stockpile coordinates/filter | Saved fields; focused persistence checks. |
| Active/pending finite tasks and temporary delivery/defense targets | Temporary session fields; intentionally reset on restart. |
| World calendar | Original `world/New()` invokes `Date()`; original `world/proc/Date()` assigns a new random1–1000 value. The seventh Orc lifecycle's different day numbers are expected original restart behavior. |
| Built workshops, changed terrain, dropped stockpile items, free world population | No whole-world save/restore path was found in the included source. Original `SaveUnits()` writes the connected player's object graph; server startup loads compiled maps. Arbitrary world state is not covered by the passing unit-save reports. A dedicated persistence design and full two-launch world-state matrix remain open. |

Source anchors: `game/Code/Saves.dm`, `game/Code/World.dm`, `game/Code/History.dm`, and the shared local-save launcher helper. This document records existing scope; it does not introduce a save-format migration or alter the normal player's files. Preserve old saves and worlds before any future map-persistence work.
