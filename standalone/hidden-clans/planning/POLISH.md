# Polish pass (before any graphical change)

The user's direction (2026-10-17): perfect the current systems before step 4 (3D models).

## Round 1, done 2026-10-17

Three independent code reviews plus a 200-unit stress test. Every finding was verified against the code before fixing. One finding was a false alarm: tool tiers *are* wired into `Bump.dm`, a Latin-1 file that ordinary search skips.

**World save**
- Items the season Repop puts back are recorded as map content, so they no longer multiply on every restart.
- Owners who are offline at autosave keep their workshops and items (the owner key is kept).
- The save is crash-safe: temp file, then backup, then swap. Loading falls back to the backup and skips unreadable records instead of stopping.
- Null and icon settings are restored, and workshops get their station art back.
- "Supported" is part of the tile signature.

**Blueprints**
- Builders only take items they're allowed to collect.
- Direct orders come first. Builders aren't pulled away by jobs or the board, and their paused job resumes when building is done.
- A crash in the original build code can't leave your selection swapped.
- Dig marks and powers apply immediately instead of becoming blueprints.
- Unreachable piles are given up after 30 s.
- Painting refuses a layer with no builder on it.

**Self-care**
- Any order, stop or job change interrupts care and holds it off for 1 minute.
- Care never takes over a unit the player is marching or fighting with.
- Give-ups wait 5 minutes, and an unreachable home bed is forgotten.
- No rough sleep with enemies within 7 tiles. Rough sleep is less restful than a bed (Tiredness capped at 70).
- Beds owned by other players aren't claimed.

**Bulletin board**
- Claims with no progress for 2 minutes, or held by paused workers, are released, and that worker skips that order for 5 minutes.
- Wood or stone orders aren't taken when the stockpile filter refuses them, and the order says so.
- Re-claimed craft orders queue only what's left, and the board never deletes crafts the player queued.
- Turning off a standing order closes its open order. Claim counting is one pass per tick.

**Lineage**
- When a parent is lost during pregnancy, the child still gets both real parents (parents are carried for every pregnancy).
- Critters are kept out of family records.

**HUD**
- Esc while placing in 3D no longer clears the selection.
- Board cards and the hero frame update in place, so clicks and open menus aren't interrupted.
- The 3D toggle doesn't flicker back, and turning 3D off cancels placement.
- Camera keys no longer stick when the window loses focus. Cmd/Ctrl/Alt shortcuts are ignored by 3D keys.
- Keyboard panning doesn't rubber-band, and server x-ray and cutaway settings are respected.
- The top bar wraps at small widths, and toasts no longer block map clicks.
- Lineage text is escaped and house colours validated. Typing a house name isn't wiped by updates.
- A broken terrain update can't leave deleted GPU buffers in use.
- A press that ends over a panel doesn't click the ground.
- Each HUD part renders independently, so one error can't freeze the rest.
- Accessibility: skill tiles work with the keyboard, the top bar is no longer a noisy live region, and labels are clearer.
- **The HUD accepts the first click even when the game window isn't in front.** This was verified with real clicks while Safari was in front.

**Speed**
- The skill tick is about 130 → 30 ms per second at 200 units.
- 3D: unit sprites are cached per appearance, and nothing is sent when nothing changed.
- 3D clicks are limited to 25 tiles and can't target invisible things.

**New regression checks:** care interrupted by an order, Repop items not saved, a child's father kept when he dies mid-pregnancy.

## Still open (next polish rounds)

- **3D render loop:** ~~it allocates new arrays every frame (GC hitches with many units)~~ done 2026-10-22 night (world-look:
  5.8 → 0.7 MB of garbage a frame at 200 units, terrain rebuilt in chunks; see `POLISH_OVERNIGHT_2026-10-22.md`). Still
  open: clicking a wall top picks the tile behind it.
- **3D fog of war:** things behind walls are sent and drawn (`range` ignores walls). Use what the player's units can see.
- **World save gaps:**
  - Tile changes far from your units aren't tracked: fire spreading, monsters breaking walls, offline players' units.
  - Item scans loop over the whole world at autosave and login. Keep a registry instead.
- **Lineage:**
  - The payload is rebuilt every 0.5 s while the view is open. Cache it.
  - Captured units bring a house the new owner doesn't know about.
- **Not yet built:** heirs and succession; group needs line and helping each other; hero/village mode; village crafting at every station; patrol routes.
- **Bigger scale:** see `SCALING.md`.

## Play-test checklist (things only a real session can confirm)

1. **Building and restart:** build a wooden wall and a workshop (Work › Place a workshop), quit, reopen. Both should still be there, with the workshop still yours.
2. **Construction site:** plan a stone wall with no stone anywhere. A "Mine stone for building" order should appear on the board. Set two villagers to Board worker and watch the wall get built.
3. **Roster:** change Job, Priority and Defense with the dropdowns, and use bulk "Set job…".
4. **Care vs orders:** let a villager get cold at night, then give it a move order. It should obey at once.
5. **3D:** F8, rotate (right-drag, Q/E), zoom, and click to move. Use "," and "." to change layers, and C for cutaway.
6. **Skills:** chop for a while and watch XP drops and level-ups. Click a skill tile for the guide.
