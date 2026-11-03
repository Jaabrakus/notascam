> Updated direction: the user requires an exact Dungeon Master replica. The combination proposal below is historical and is not the current implementation target. See `../replica/REPLICA.md` for the original-code compatibility work.
>
> Asset extraction update: all 61 legacy binary icons have been decoded. The current catalog contains 255 PNG-backed sheets with 4,764 states, plus one GIF. All original bytes remain in `original-icons/`. Legacy conversions preserve decoded pixels and metadata; their PNG bytes differ from the originals. Original hashes and converted PNG hashes are recorded separately. The three empty source files and the unresolved LizardWoman reference remain. Earlier extraction counts and gaps below describe the initial assessment.

# Combining Dungeon Master and Lands of Legend

This is a source and asset assessment, plus a working offline sprite catalog. No gameplay has been ported yet. The original projects remain untouched.

## Proposed game

A 2D fantasy sandbox where you begin as an adventurer, develop practical skills, recruit followers, and build a settlement. Explore the surface and underground, gather materials, produce equipment, and defend your community among rival kingdoms and creatures.

This combines the games' complementary strengths. It is a proposed direction, not a claim that the original systems already interoperate.

| Area | Dungeon Master evidence | Lands of Legend evidence | Proposed combination |
| --- | --- | --- | --- |
| Player and followers | `Code/Ownership.dm` manages player-owned units; `Code/Selection.dm` selects workers and marks autodig areas | `Login.dm`, `Mobs.dm`, `Vars.dm` center on a character with personal stats and skills | Direct character control plus commands for recruited followers; use one entity model for both |
| Gathering and settlement | `Code/Building/Building.dm`, `Code/Building/TurfTypes.dm`, `Code/Items/CraftingStations.dm` | `Objs.dm`, `Turfs.dm`, `Vars.dm` contain resources, structures, and gathering skills | Shared materials and construction recipes; designate jobs for workers |
| Crafting and equipment | `Code/1 - Item Making.dm`, `Code/Items/Equipment Lists.dm`, workshop definitions | `Crafting.dm` calculates equipment quality, durability, weight, and defense from materials and skills | One crafting pipeline, with material and skill effects adapted from Lands of Legend |
| Combat | `Code/Creatures/Combats.dm`, `Combat - Bows.dm`, `Health.dm`, `DamagedParts.dm` | `Combat.dm`, weapon skills and limb condition variables | One combat model supporting character and follower attacks; choose shared timing, damage, and equipment rules |
| Peoples and creatures | `Code/Creatures/Race.dm`, race modules for dragons, spiders, vampires, werewolves | `Mobs.dm`, race artwork, kingdom rank definitions in `World.dm` | A shared species catalog; distinguish playable species, recruitable units, wildlife, and bosses |
| Living world | `Code/World.dm` has seasons, day/night, population updates; `Breeding.dm` has reproduction | `World.dm` has a calendar, day/night, kingdom ranks, world state | One clock and population simulation, with settlement growth added after the basic game works |
| World geography | Four maps included by the DME: ground, underground, sky, hell | DME includes `OldSmallWorld.dmm`; other map files and map imagery are also available | Import maps as separate regions initially; reconcile travel links and terrain definitions before joining them |
| Persistence and multiplayer | `Code/Saves.dm`, BYOND client and ownership APIs | Save/load routines, `Login.dm`, BYOND identity and membership APIs | New save format and player identity; server authority if multiplayer is retained |

## Accessible assets and data

| Inventory | Dungeon Master | Lands of Legend |
| --- | ---: | ---: |
| DM source files, including unreferenced files and backups | 114 | 15 |
| DMI icon files | 163 | 96 |
| PNG-backed DMI sheets available in this browser | 107 | 87 |
| Named sprite states in those sheets | 1,418 | 2,900 |
| Direction/frame cells described by those states | 7,907 | 7,389 |
| DMM map files, including backups and alternatives | 9 | 8 |
| WAV/MIDI sound files | 9 | 23 |

All 259 original DMI files are copied into `original-icons/`, keeping the games in separate namespaces. The 194 readable PNG sheets are in `sprites/`. The exported PNG files preserve the original bytes, including their DMI metadata. `manifest.json` contains state names, direction counts, frame counts, frame delays where supplied, cell offsets, original paths, and hashes. That provides the data needed to construct animations in another engine.

Of the readable sheets, 191 use 32×32 cells. Three use larger cells. Matching tile sizes help reuse the art together, but do not establish matching palettes, attachment points, or equipment overlays. No byte-identical PNG-backed DMI sheets were found across the two projects; similarly named artwork must still be reviewed visually.

The inventory indexes source, maps, interface definitions, images, and audio in their original folders with file sizes and hashes. Existing player saves, logs, and configuration data are deliberately outside this content catalog. Game definitions are still DM source: recipes, species inheritance, and item stats have not yet been converted into a new engine's data model. DMM maps are accessible text, but their object paths depend on those definitions.

## Extraction gaps

- 61 icons have the older binary DMI signature and need a decoder. Their original bytes are preserved.
- One further icon is actually a GIF stored with a DMI extension. It is exported as a GIF and included in the browser; it has no DMI state metadata.
- Three icon files are empty and contain no recoverable pixels in these copies.
- The direct DME source-resource scan found an unresolved `LizardWoman.dmi` reference in `Code/Creatures/OverlayBuilds.dm`. This scan covers quoted image/audio references in directly included files, not runtime-generated filenames or every dependency recursively.
- Map inventories include unused versions. The DME include lists identify the startup maps; additional runtime loading requires inspection before import.

The originals' license and readme files are preserved in `original-notices/` for later attribution and distribution review. Asset access does not itself establish the provenance of every contributed sprite or music file.

## Decisions required during implementation

The two games have incompatible ownership, stat, race, equipment-slot, combat, timing, and save structures. Porting both implementations directly would duplicate systems. Instead, build one common implementation and translate selected definitions from each source into it. Keep namespaced original IDs so each imported item can be traced to its source.

The suggested first playable slice is a small surface area and cave, one controllable character, one recruitable worker, gathering wood and stone, one crafting station, one enemy, and save/load. It exercises the proposed adventurer/settlement combination before importing the full content libraries. Existing kingdoms, specialized species, deeper crafting, additional realms, and multiplayer can then build on that foundation.

## Browse and regenerate

Open `index.html` directly in a browser. Search by filename, game, or state name, and expand a sheet's animation metadata. No server, BYOND installation, or Python package is required to browse.

Regenerate the inventory with Python 3 from the Dungeon Master folder:

```sh
python3 standalone/tools/catalog_assets.py
```

The optional `--dungeon` and `--legend` arguments select other source-folder locations. Regeneration updates the generated catalog and preserves this assessment.
