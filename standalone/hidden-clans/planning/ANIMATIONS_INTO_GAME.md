# Unit animations and 3D gear: into the game (plan, 2026-10-25)

Everything below works today in the animation arena (art/gear3d, preview only). The user OKed putting it in the
game. Stages, each checked with no game window first (headless), the real client only at the end:

1. **The page.** The art/gear3d scripts (gear3d, ragdoll, skills, deaths, work, magicfx) go into game/Interface,
   loaded by remastered.html. The eight page hooks the preview patches in (gear records, the gear shader mode, drawing
   after the silhouettes, kept records) become part of the page, behind one switch (on).
2. **3D gear on every unit.** The server sends each unit's weapon, shield and helmet (style and tier) from what it
   has equipped: the new gear by its rm_gear name, the original gear by the old-looks table. The unit's 2D picture
   then leaves those three layers out, so nothing is drawn twice. The piece pictures (16 facings) and gear3d.json
   are sent once to each player (browse_rsc, as the beasts' breath is): about 7 MB pixel art, or 34 MB smooth.
3. **A doll for every unit.** parts.py, run once over every Races64 sheet, writes each race's part map (which pixel
   is head, torso, upper and lower arm, thigh and shin, for each facing) and joints. When a unit needs a doll, the page
   cuts the unit's own picture (its armour as it wears it) with its race's map, so every race and armour works
   without cutting anything ahead.
4. **Combat.** The page already gets every blow: who struck, from where, with what class of weapon, who was hit, and
   the result (hit, kill, miss, block, parry, out cold). It plays the swing, the guard, the flinch or the death from
   that. The server adds what the page can't guess: the body part hit, the cause of a death that isn't a blow
   (DeathType), where a launched or thrown unit lands, and a limb lost.
5. **Work.** The server sends each worker's job and the tile it works (mining, chopping, smithing, building, rod,
   harpoon or net fishing, picking, gathering, tilling, planting, harvesting) and what it carries; the page plays the
   move with the tool in hand.
6. **Checks, then the build.** Headless checks (check_arena) for each stage; ask before an app build (builds were on
   hold).

Status (2026-10-25 ~16:45, unit-sprites). Look chosen by the user: palette pixel art pieces in each tier's colours, the
smooth world; climbing shows only the unit's back.
- Stages 1-2 done in game/, checked headless (tests/gear3d_check.dm 15 checks; the page's doll path in the arena):
  Gear3D.dm + Gear3DData.dm (art/gear3d/install.py), the page's guarded hooks (rm-gear3d marker, gear records, walking
  records, hit handler, t.g3doll picture skips), each unit's doll cut on the page from its own picture by its race's map
  (parts.py --races: bare and sleeved), blows, kills and deaths (Death.dm RmG3Died, a "die" hit with DeathType) as moves.
  In build 25 (stage 1 only); its client errors were the app dropping Interface/gear3d/*.json (build_app.py fixed).
- Stage 5 done (17:20): work from each job's own state (Gear3D.dm RmG3Work: mine, chop, fish by method, smith at a
  forge, build at a workshop or the piece just built; Blueprints.dm one line), climbing from D["climb"] at the server's
  pace, seen from behind, a rope only with climbing gear; stone doors drawn as the climbing stone (game.js g3stoneDoor,
  one page hook in v3obj). Applied with reports/gear3d-staged/stage5_patch.py after passing on a clone.
- Not yet: carrying while walking (a doll that walks with its unit), cooking and farming moves from the server.

Not in the first pass: big beasts' dolls, the lobster cage, casting with the Spells tab (staff spells only).
