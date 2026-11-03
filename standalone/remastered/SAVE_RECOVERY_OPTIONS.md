# Kiwi save recovery options

Read-only inspection: 2026-10-17T05:14:18-04:00. No game, server or client was launched; no save was restored or copied into the normal profile. All three source-file SHA-256 values were unchanged after inspection.

The current Kiwi save has an **empty UnitList (0 units)** and no saved Monster objects in its10-entry graph. This explains why loading that save provides no army: current LoadUnits restores only its UnitList. This does not establish how the army disappeared or whether the units died; it is evidence of saved state, not a diagnosis of the earlier loss. The camera/player record remains at820,491,1, with key localhost@kiwi and Race Orc.

| Save | File modification time (Eastern) | Saved roster | Progress and direct carried contents |
| --- | --- | --- | --- |
| Current normal save | 2026-10-16 23:52:38.982412 EDT | 0 | Empty roster;73,820 bytes |
| before-border-menu-animation-20261016 | 2026-10-16 21:43:56.568438 EDT | 3 Orcs, HP350/350/450 | Levels6/6/8; contents12/4/5;2,803,542 bytes |
| before-selection-facing-20261016 | 2026-10-16 21:25:05.023536 EDT | 3 Orcs, HP350/350/450 | Levels4/4/7; contents4/4/4;1,512,461 bytes |

Times above are filesystem modification times, not independently verified original play-session timestamps. Both backup rosters contain two ordinary Orcs and King {Player} Orc with IsRoyal1. Every unit has HP equal to MAXHP, GoingToDie0, both legs, and Caged/InHole0. The newer army positions are812,486,1;818,487,1;820,487,1. The older positions are842,494,1;841,495,1;841,494,1. Counts come from UnitList references, not a scan that might accidentally include corpses or unrelated objects.

**Preferred recovery candidate: the newer border/menu backup.** It contains the same three-unit roster with later levels and more carried resources: five stone, two silver ore, one iron ore, one uncut diamond, three sleeping bags, three pickaxes, three bucklers, two Orc axes and one carried body. The older selection/facing backup is a fallback with three sleeping bags/pickaxes/bucklers, two axes and one stone. Every serialized graph reference resolves within each file (196/196 references in the newer graph;130/130 in the older). The JSON graph parses and the original type paths/roster/coordinates are present. These are viable recovery candidates **based on read-only structural evidence**; neither was loaded in the current runtime during this audit, so current-runtime compatibility and complete behavior are not certified.

Exact files and SHA-256:

- [Current normal Kiwi save](</Users/kiwimango/Library/Application Support/Dungeon Master Remastered/world/units/localhost@kiwi_save.sav>)  
  `368992a781598c7703b64091935e081666dd9052808ee4d881ba5fa98d74fac4`
- [Preferred newer three-Orc backup](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/restore-points/before-border-menu-animation-20261016/player-units/localhost@kiwi_save.sav>)  
  `9f5cf0944ea917fe20385eb51d62e3666437046cb926a04c42ded34523560c09`
- [Older three-Orc fallback](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/restore-points/before-selection-facing-20261016/player-units/localhost@kiwi_save.sav>)  
  `340036a64b7d47ce4d6a0d675ff6c6d2fb21ab1291523d1e5a542ac849d415d8`

**No silent restore.** Neither backup has been installed. Any future recovery must identify the chosen snapshot and preserve the current save before replacing it; it rolls the army back to that backup's recorded state. A private copied-profile load check is still needed before claiming a verified recovery. The backup is a player/army save, not proof of a complete terrain/building/world snapshot.

Method: Python JSON parsing only, using the same existing `_nodes` → `.opendream_graph.Objects` → UnitList.Id → Values graph representation used by tools/check_app.py167–176. Scalar unit fields were read through Fields._nodes; all graphref IDs were checked for in-range references. Current source Code/Saves.dm26–75 supplies the load-loop interpretation and owner reassignment; missing serialized Owner/loc alone is not treated as corruption because that loader restores ownership and saved coordinates.
