# Launch audit, 2026-10-25 (playtest)

Build 30 (engine v12e = v11 + save patch + unit grid ON, heights step 1), played as a new player on private test
profiles. The user's own saves were never used. Started on build 29's brief; build 30 landed at 18:20 before the first
real-app run, so everything below is build 30 or today's game/ (the same code, plus later landings in arena checks).

**Verdict: not launch ready yet. The biggest blocker is build 30's new death animations (the dead stay standing);
bare-fist fights that never end come next, and the other three are quick fixes. Most loops work.** (Updated 19:4x
with the user's answers: a new company being wiped early is intended, so it's no longer a blocker; fist fights must
end.) The onboarding cards, the gathering
loop, save/load, fog and the family/succession flow all work. Making, building and the supply chain pass every arena
check but weren't played by hand this round (see "Not covered").

## How it was tested

- **Arena and headless first.** 18 arena checks were run on today's game/ (one check per runlock call), plus today's suite
  and gate results from other sessions (18:00–18:30), plus every HUD panel rendered headless at 1280x720.
- **Real app, build 30.** A private profile (`hold.py`, `DM_STANDALONE_DATA_DIR` in my scratch folder). Round A1: the
  window came up in the middle of the user's screen, and **the user played it themselves**. They picked Frogmen,
  explored east and lost the company, and their bug reports from it went to the coordinator at 18:32–18:38. I stopped
  my own input while they played. I read their play from the client's command log and took stills with
  `screencapture -l`, which needs no focus. Round A2: once they left it on "Begin again", I started Dwarves and drove
  chopping, mining and the Build panel. I stopped there because every probe click brings the window to the front and
  moves the real cursor (WebKitBridge `dm_ui_test_focus`), and the user was at the Mac.
- **Performance at 200 units.** Taken from today's profiles on the build-30 game and engine (server-cost, world-look,
  hud-craft, map-memory). tick_profile refuses to run while a game window is open, and mine was open the whole time,
  so I didn't add a run of my own.

## Scores (1 = far from launch, 5 = ship it)

| loop | score | one line |
|---|---|---|
| Start and onboarding | 3 | The cards and goal tracker are good; letter keys fire old commands (A, D, W, S, Y) |
| Gathering | 4 | Gather switch, Chop/Mine labels, the exact yellow outline and one block per click all work; tended trees never fall |
| Making and supply chain | 3 | Every arena check passes (jobs, buildings, food); not played by hand this round |
| Needs and healing | 4 | care, doctor, food and stumps pass; the unit card shows blood loss, arm injury and bleeding stump clearly |
| Building | 3 | buildings 26/26, stone doors 11/11, plan-build 7/7; the Build panel is clear; not built by hand this round |
| Combat | 2 | **Doll deaths in build 30: the dead stay standing and can't be clicked.** Fist fights never end; check_combat can't start |
| Capture | 4 | Every case but the known `ko_still` (see capture below) |
| Families, houses, rulership | 4 | family, heirs and rulership pass; the death → heir → "Begin again" flow works in the real app |
| 3D view | 3 | Fog, light and hover outlines look good; the Sky button strands the camera; unseen water draws pale white |
| Saving and loading | 4 | check_app new army + reload passed on build 30 (saves unchanged); save round trip passes; old-save login 5 s at 200 units |

## Launch blockers, ranked

1. **The dead stay standing; bodies can't be clicked; a hit unit's flinch is left behind** (build 30, the user's own
   reports from my test window, 18:36–18:38; the coordinator sent them to unit-sprites with an off switch for build
   31). Bodies feed butchering, graves, forensics and looting, so this breaks several loops, not just the look.
   Already with unit-sprites; the off switch is in game/ (`rm_g3_dolls = 0`, Gear3D.dm) for build 31. Recheck there.
2. **Bare-fist fights don't end** (the user, 19:3x: "bare fist should end why wouldnt they?"). In the pace arena 7 of
   8 fist duels were still going at the 6-minute cap, with about 8 hits in 100 swings (swords: about 45). Cause
   (Combats.dm `Attack`, the original's body-part code): a blunt blow lands only when one of the 3–4 % part rolls hits,
   and it can't take a part below 10 HP: the part is clamped at 10 ("Mangled"), so every later punch there does
   nothing. Blunt blows bleed only once a part is down to 40. So a fist fight can end only by a rare head blow (brain
   damage: the one fist death) or slow blood loss, and today's slower swings (Hits.dm `rm_swing_pace` 2) push that
   well past 6 minutes. Natural healing is gone now (Healing.dm), so Pace.dm's old note blaming healing no longer
   applies. Traced (19:36, `PC_ONLY=fists PC_TRACE=1`):
   - In the fights that go on, body health falls 2770 → ~2200 (-20 %) and then flattens.
   - HP stays at 350/350 throughout, and both fighters end up unable to walk, still punching.
   - 3 of 8 died (13 s, 235 s and 305 s: two by bleeding, one by brain damage); 5 were still going.

   Maces and bows are Blunt too, so mace fights may stall the same way. → stump-care (combat pace): message sent,
   board request filed.
3. **Letter keys run the original game's commands.** In skin.dmf:
   - A = Attack mode
   - D = DeclareLeader
   - W = SendMSG (a text prompt)
   - S = WorldSay (a text prompt)
   - Y = GMChat

   The user's first minutes in the window logged Y, Space, A, D and Cmd. They were partly typing meant for another app
   (the window had popped up in front), and partly A/D. The results:
   - Attack mode came on silently, and the next click was an attack-move. That ends the arrival grace, and in round
     A1 it marched the company into the band that killed it.
   - D sent one "To rule your camp, X must hold a Chief's Totem or better (made at a carpentry from 2 wood and 1
     bones, or a Bone Crown)." per selected unit into the chat.

   An RTS player's hands go to WASD for the camera. W/S opening chat prompts and D trying to crown someone will
   confuse a new player in the first minute.
   [Picture: Attack lit, the crown lines](../reports/polish-2026-10-22/playtest/launch-audit/a1-12-hover.jpg).
   → rts-feel.
4. **The Sky button strands the camera on the Sky with no units up there** (the user's build-30 screenshot came from
   this window: they clicked Sky seconds after Begin). It shows a dark slab and pale empty areas, and nothing brings
   the camera back but the Surface button. Already diagnosed: ramps-gather 18:39 and world-look 18:5x; the fix is
   rts-feel's staged "earned Sky".
   [Picture](../reports/polish-2026-10-22/playtest/launch-audit/a1-01b.jpg). Recheck in build 31.
5. **No combat regression gate.** `tools/check_combat.py` exits at once: `--label` is defined twice, by check_combat
   itself and by `check_engine.add_args`. It isn't in the suite, so nothing flagged it; its last good run was 04:28.
   It's a one-line fix (drop check_combat's own `--label`), then it should join the suite. → qa-stability.

## Decided by the user: not a blocker

- **A new company can be wiped minutes after it arrives.** The user, 19:3x: "new realms are hostile.. and brutal
  normally no hand holding". So there will be no safe zones, warnings or truces for new realms. For the record, round
  A1's timeline:
  - 18:31: Begin; the Frogmen arrive at 197,689.
  - 18:31–18:34: the user walks them about 60 tiles east.
  - ~18:35: the A key turns Attack mode on, and the next click is an attack-move (that ends SafeStart's grace).
  - 18:36: a band of frogman warriors and scouts, lizardmen and skeletons is on them.
  - 18:37: two are dead.
  - 18:42: all three are dead, and "Begin again" shows.

  Pictures: [the fight](../reports/polish-2026-10-22/playtest/launch-audit/a1-14-watch.jpg),
  [the heir card](../reports/polish-2026-10-22/playtest/launch-audit/a1-15-watch.jpg),
  [Begin again](../reports/polish-2026-10-22/playtest/launch-audit/a1-16-watch.jpg). Only the A-key part stays open
  (blocker 3).

## Polish (not blocking), ranked

1. **Poison spore plant chat spam.** The line is "PoisonSporePlant spews corrosive posion spores into the air!" (the
   raw type name, "posion", and "!!" in the source). It comes every 2 s while anyone stands next to one, four times
   in the first minute of round A1. `Critters.dm` ~88. **Fixed in game/ 19:08:** "A poison spore plant spews
   corrosive spores into the air!", at most every 30 s per plant.
   [Picture](../reports/polish-2026-10-22/playtest/launch-audit/a1-04-now.jpg).
2. **A tended tree never falls.** "Tend living" is on by default, so the first Chop takes half the tree and ends with
   "Gathered; the tree is tended, so it's left to grow back". The tree stays up, and a new player thinks the chop
   failed. The message should say how to fell whole trees. **Fixed in game/ 19:08** (Orders.dm): "Gathered half:
   tended trees are left to grow back (Tend living: off in Work fells them)".
3. **The crown notice repeats once per selected unit and says "1 bones".** Rulership.dm `rm_seat_made` and
   `RmCrowningRegalia`. **"1 bone" fixed in game/ 19:08.** Still open: one line per unit when D is pressed with
   several selected (rulership's owner, after rts-feel moves D off the key).
4. **Water out of sight draws pale white**, brighter than the lit ground beside it: the rivers and ponds just past
   the fog edge in [a1-06](../reports/polish-2026-10-22/playtest/launch-audit/a1-06.jpg) and
   [a1-09](../reports/polish-2026-10-22/playtest/launch-audit/a1-09.jpg). Explored ground goes blue-grey as it should,
   but the water looks like snow. → world-look.
5. **The first workshop asks the player to visit three tabs.** The Build panel says "No stockpile yet: place one in
   the Work tab" and "Set the Builder job in Village → Roster". Both lines are right, but neither is a button.
   [Picture](../reports/polish-2026-10-22/playtest/launch-audit/a2-07-build.jpg). → hud-craft (make the two hints
   jump to the place they name).
6. **The server sheds load with 3 units on a busy Mac.** SHED fired 3 times in round A1 (ratio 0.81–0.91, 6–8 s
   each) while 3–5 other sessions' arenas ran. That's not a player's Mac, but a reminder that SHED is visible to
   players. Fine as is.
7. (Moved: bare-fist fights not ending is now blocker 2, by the user's answer.)
8. **Two arena tests fail on drift, not game bugs:**
   - `fishing_test` FI|rot looks for "miasma", but bodies now give off "rot" (Vapours.dm, the user's 10-23
     change). → qa-stability.
   - `limb_gear_test` gives sword=0 in all 9 cases (every limb and armour case passes). Gear3D.dm leaves a 3D-looked
     weapon out of the unit's picture layers and the page draws it, so the test's 2D sword check is out of date.
     → unit-sprites: confirm the 3D sword still shows after a limb is lost.

## Each loop

### Start and onboarding: 3
- Works (real app): the start card (A1), the race card with one line per people and the rare draw starred
  ([Illithid offered](../reports/polish-2026-10-22/playtest/launch-audit/a2-01-race.jpg)), the story card, Begin, and
  the goal tracker stepping Meet your company → Secure supplies → Establish a camp. The heir card ("Murora has died.
  Long live Ribakk, eldest of the house, now head of House Hartwell") has Crown as Chief / Select / Close. "Begin
  again" comes up when everyone is gone.
- Arena: safe_start passes (swamp, roof, migrants, three logs of room).
- Bugs: blocker 3 above; polish 1. The early wipe is intended ("Decided by the user").
- One thing I couldn't pin down: on the A2 restart the story card was answered "Begin" (askanswer 4|1) about 4 s
  after my one click on Dwarf, and I never saw it. Maybe a stray click; watch for it next round.
- Confusing: Gather is off by default and nothing on screen says so until the switch is pressed. The goal "Secure
  supplies" doesn't mention it (the tool tip does).

### Gathering: 4
- Works (real app A2): Gather on gives "Gather on: a click on rock mines it, on a tree chops it."; the hover label
  reads "Chop" or "Mine" with a yellow outline on exactly the tree's tile or the block pointed at
  ([chop](../reports/polish-2026-10-22/playtest/launch-audit/a2-03-tree-hover.jpg),
  [mine](../reports/polish-2026-10-22/playtest/launch-audit/a2-05-rock-hover.jpg)); one click takes one block
  ("+1 Stone", [picture](../reports/polish-2026-10-22/playtest/launch-audit/a2-06-mine.jpg)); the once-per-player
  tool notices ("Your people need Woodcutting 15 to use a metal axe well…", the same for Mining).
- Arena (today): gather 24/24, plan 6/6, plan-build 7/7, mountain levels 4/4, mountain heights 5/5, breaking passes in
  full after ramps-gather's 18:24 update.
- Bugs: polish 2 (tended trees). Known: obey's 6 chop cases (arena trees tended), the same rule.
- Not seen this round: the Plan mode in the real app (arena only).

### Making and the supply chain: 3
- Arena: jobs passes (5,000-unit pool, spread passes; 30k skipped by the user's rule), buildings 26/26 (suite 17:41),
  food 7/7. The Work page (headless) explains Gather / Make / Serve and lists workshops with costs.
- Not played by hand this round, so the score stays at 3 until a real round confirms it.

### Needs and healing: 4
- Arena: care (eating, no-fire note, interrupt, saved home), doctor (herbs, remedies, HUD, away, salt, save), food
  7/7, stumps 23/23 (suite 16:11).
- Real app: the card shows "Blood loss", "Arm injury", "Bleeding stump" and "Looks bleeding badly, missing an arm"
  ([picture](../reports/polish-2026-10-22/playtest/launch-audit/a1-14-watch.jpg)). Healing wasn't seen; the company
  died first.

### Building: 3
- Arena: buildings 26/26, stone_door_check 11/11 (live 17:35), plan-build 7/7. Real app: the Build panel lists
  Fortress / Buildings / Halls / … / Workshops with costs, race lines and one line of how-to; the hints say what is
  missing (polish 5).
- Not built by hand this round.

### Combat: 2
- Arena: attack passes (hostile, target, no hijack, move clears, attack-move, goal); throwing passes; weapon_cap
  passes; formations 7/7 (149 checks, formations off is today's default); pace (speed 1, 8 pairs each), as below.

  | matchup | first blow | first limb (median) | fight ends (median) | how fights end |
  |---|---|---|---|---|
  | iron swords | 1 s | 70 s (27–104) | 85 s (32–118) | 6 dead, 1 fainted, 1 still going |
  | swords in full metal armour | 1 s | 67 s (37–105) | 89 s (42–112) | 5 dead, 1 fainted, 2 still going |
  | bare fists | 6 s | none | 56 s (1 ended) | 1 dead, 7 still going |

  Sword fights are long and brutal, with limbs lost before the end, as the user asked (vanilla-WoW pace). Fist
  fights must end too (the user), and they don't: blocker 2.
- Real app: the user's fight. Limbs came off ("Frogman Warrior cuts off Murora's left leg!"), there was the "Attack
  alert · Go to unit" banner, and "Krobbo attacked; 0 nearby helpers responding." in the log.
- Bugs: blockers 1, 2 (fists) and 5.

### Capture: 4
- Arena (16:00, and this audit's run at 19:09): every case passes except the known `ko_still` (walks_awake=0).
  Passing: bind, lead, fetch a rope, drag, win over, enslave, break free, guarded, revolt, stake, tree, cage, cage
  walk, limbs, rope look, save.
- Not played by hand.

### Families, houses and rulership: 4
- Arena: family passes (lost father, rename, reload, data), heirs passes (18:08 and 19:28), rulership passes
  (64 checks, 15:56 and 19:27). Real app: succession on death and "House Hartwell has no one left to lead it" when the last one dies.
- Bugs: polish 3.

### The 3D view: 3
- Works: fog (12-tile sight, soft edge, blue-grey, explored stays), night light and torches, the hover outlines, the
  level buttons, Iso/Top/Chase. Arena: fog passes (remembered building, last-seen attack, host switch, save round
  trip, cost), delta3d 9/9 + 48/48 (suite 16:16).
- Bugs: blocker 4, polish 4.

### Saving and loading: 4
- check_app on build 30 (coordinator, 18:20): new army 92 s, reload 72 s, 3 units saved and back, saves unchanged,
  0 errors, every part matches the build. save_roundtrip passes (work resumes, chopped trees stay chopped, nothing
  left nowhere, no runtime errors). grid-save-roundtrip passes (18:03).
- map-memory 18:4x, logins at 200 units: 5.0 s on an old 140 MB save until the game next saves; then 1.7 s cold and
  0.5 s warm on the 20 MB save the fix writes.
- Not done by hand this round (Save button, quit, relaunch).

## Performance at 200 units

| what | number | source |
|---|---|---|
| server, quiet village (build-30 game) | world.cpu average 15 %, worst tick 105 ms, 0 s behind over 212 s | levels3-after-200 (18:08) |
| server, orders every 10 s + camera pan (v12 engine) | average 27.7 %, worst 92 ms, 1.7 s behind over 240 s | gq-200-cand (17:28) |
| server, the same on a busy Mac | average 24.7 %, worst 589 ms, 8 ticks over 100 ms, 3 "cannot keep up" | levels4-before-200 (18:30) |
| fog's share | 3D things 35 ms a tick with fog on vs 17.5 ms off | check_fog cost line (this audit) |
| client frame (real app, 203 units) | median 17.0 ms (60 fps is 16.7); 27 frames over 33 ms per 20 selection changes | hud-craft hudprof (15:56–16:16) |
| Select all | worst frame 40–45 ms in the real app; 19–20 ms in the WKWebView probe | hud-craft (known, being chased) |
| login with 200 units | 5.0 s freeze on an old save, then 1.7 s cold | map-memory (18:4x) |

Steady play at 200 units is fine. What a player will notice are the 40–50 ms frames on selection changes and the
first login on an old save.

## Not covered this round, and why

- By hand: making, a full building, needs and healing, capture, families, Plan mode, and save → quit → reload. The
  user was at the Mac, and every probe click takes focus and moves their cursor. All of these pass in the arena.
  Next round: a no-input probe, or a real round when the user is away.
- A fresh 200-unit profile of my own, for the tick_profile reason above.

## Requests filed (board, Requests, From playtest)

- qa-stability: blocker 5 (check_combat), polish 8 (fishing test drift). The early-wipe request is withdrawn (the user's
  answer).
- stump-care: blocker 2 (fist fights).
- rts-feel: blocker 3 (letter keys).
- world-look: polish 4 (pale water out of sight).
- hud-craft: polish 5 (Build hints as buttons).
- playtest (mine): polish 1–3 wording, landed in game/ 19:08: compile OK, chat filter check PASS. Not yet in an
  app build.
