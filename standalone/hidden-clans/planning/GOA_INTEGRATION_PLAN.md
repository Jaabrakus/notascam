# Hidden Clans: bringing GOA in, start to finish

Hidden Clans is a hero battler: you play one ninja on Banners' engine, 3D world and body-part combat, with Naruto GOA's
way of fighting and growing. This plan takes GOA's systems (read from `~/Downloads/GOA Source/code`, numbers in
`planning/GOA_MECHANICS_PLAN.md`) and lands them in order, each phase playable on its own. GOA's names never come over
(the game is hosted publicly); its mechanics do.

How to read it: each phase says what you get, where it lives, how it is checked, and what only you can decide. Sizes:
S = a session, M = a day, L = several days.

## Now, one at a time (the owner, 11-01: "keep it simple and do it one by one")

1. ~~Punch and kick as one combo~~ done 11-01: jab, cross, kick, kept while blows come within 4.5 s.
2. ~~Responsive~~ done 11-01 (hero mode): keys reach the page in 35-50 ms; blows, hits and effects now go out the tick
   they happen (updates in a fight every ~0.2 s, not 0.5 s); swings twice as often (rm_swing_pace 1). Left for later:
   your ninja moved on screen before the server answers (matters online, not on this Mac).
3. **GOA animation sprites on every race**: found 11-01 that GOA's drawn Run, PunchA/KickA, HandSeals, Throw and hurt exist
   only at 32 px on GOA's original body. The Human's parts posed into them was turned down ("just make the original
   sprites updated"): GOA's own frames updated to 64 px instead (enhance pipeline, `art/goa-actions/updated.py`,
   review.html?set=updated). Then each race's own head and skin on those frames (owner: "our heads and skins";
   `heads.py`, races.html; 8 races, men only so far), and GOA's body reshaped to each race's own build with its own
   shorts and bare feet (`bodyfit.py`), and each race's own body pixels through GOA's per-pixel part map (`partmap.py`,
   `uvmap.py`); every humanoid sheet, women and hybrids too (152). Next, once approved: put them in the game: Run after 4+ steps in a second (GOA's runlevel,
   speed unchanged), the punch and kick frames in the jab/cross/kick combo.

Everything below is the longer road, taken one piece at a time after these. The female bodies and the male Elf are
being done in their own session meanwhile (they only touch the GOA pipeline's folder and the female sheets).

## Where it stands (2026-11-01)

| In | Notes |
|---|---|
| One ninja (hero mode), WASD on the tiles at walking pace, first step and turns at once | `Drive.dm`, page 027 |
| Left-click a foe: your ninja attacks; the ground: nothing | `Drive.dm`, `View3D.dm` |
| Keys 1-4: Substitution, Flash step, Fireball, Kunai at the mouse | `Drive.dm` RmNinjaCastAt, page 031 (in the test world now) |
| Chakra (refills 1.5%/s), techniques with seals and cooldowns, used by NPC ninjas too | `Ninja.dm` |
| GOA bodies for every race and hybrid, women on their own bodies, generated armour | `game/Icons/Remastered`, `FemaleBodies.dm` |
| GOA punch and kick for bare hands; the animations as they are | `art/gear3d` skills.js, game.js |

## Phase 1: The battler screen (S-M)

Make the screen a hero game, not an RTS.
- **Hotbar:** a bar at the bottom with the four techniques (1-4), their cooldowns ticking down, chakra and kunai, and
  health. It replaces the RTS action bar (Stop, Gather, Plan, Build...).
- **Crosshair:** the mouse shows what a key would hit: the technique's shape on the tiles under the cursor (the race
  specials' 3D aim preview already draws shapes, `Specials.dm` / page). Red when out of range.
- **Off:** box select, the Village/Work/Build/Army tabs, unit groups, the company list, the work guide steps.
- **Names:** "Hidden Clans" in the tab title and the guide; the race blurbs say one ninja, not "3 settlers".
- Check: play from Join to a fight with only the keyboard and mouse; no RTS button on screen.
- You decide: what stays from the village (see the end).

## Phase 2: Stats and growing stronger (M)

GOA: four stats from 50 (STR stamina/damage, CON chakra/technique power, RFX hit/dodge/speed, INT skill points),
levels to 100 on a set XP curve, +6 points a level, a passive tree per stat (every 10 points of a stat = a passive point).
- Map onto Banners: STR = Strength, RFX = Agility (Attack), CON = a new Chakra stat (chakra max, technique damage:
  GOA's CON/150 multiplier), INT = Intelligence (skill points, genjutsu). Banners' slow per-skill training can stay as
  it is, or give way to GOA's levels: your call.
- XP: from regenerating chakra (GOA's odd but defining rule: spend, refill, grow), kills, missions.
- Level-up card: spend the points; the passives (Efficiency -4% chakra cost a level, Hand Seal Mastery -3% cooldown,
  Projectile Master +20 supplies, Regeneration, Combo...).
- Check: a test ninja levels from 1 to 10 in the test world; numbers match GOA's formulas (regeneration.dm 987-995).
- You decide: GOA levels, Banners' RuneScape-style skills, or both.

## Phase 3: The technique system (M-L)

From four hand-made techniques to a data table any technique fits into.
- **One table** per technique: chakra/stamina/supply cost, cooldown, seal time, range, shape (line, cone, circle, self,
  dash), charge, what it does. `Ninja.dm` becomes the engine; techniques become rows.
- **A skill tree:** buy techniques and elements with skill points; techniques need others first (GOA skilltree.dm).
- **Elements:** fire, water, wind, earth, lightning, four techniques each (20), each extra element costing more
  (250 / 450 / 650 / 850 / 1050). Banners gives them real effects: fire burns the ground (`Vapours.dm`), water works
  with rivers, earth raises or breaks rock blocks, lightning stuns.
- **The basics every ninja gets:** Substitution, Flash step, Clone, Transform, kunai, shuriken, exploding tags.
- **GOA's rules:** a 1 s lock after any technique, charge techniques that drain while held, the seal freeze doubled
  when slowed.
- Check: each technique in a test fight; costs and cooldowns as the table says.

## Phase 4: Fighting like GOA (M)

- **Block** on a key (halves damage, a front blow blocked outright; GOA's D).
- **Combo meter:** hits build it; past 13 a chance of knockback, past 20 a 3 s daze; it fades after 3 s.
- **GOA's punch and kick strings** for bare hands, mapped to clicks (click, click, click: jab, cross, kick).
- **Thrown weapons** from supplies (100, refilled at a shop): kunai, shuriken (3), needles (5), exploding kunai.
- **Knock-out and death in Banners' body:** GOA's stamina bar becomes Banners' knock-out; GOA's wounds become Banners'
  limb wounds and blood (kept, as you asked). Death at the limit, a medic's 60 s to save you, then the village hospital.
- **Limit break** (GOA's gates): +30-60% power for a while, paid in wounds.
- **Water walking** with chakra (5 a step), as GOA.
- Check: a duel against a test ninja; block, combo, knockback, KO and getting up all seen.

## Phase 5: Clans (L)

Ten bloodlines of our own, built from GOA's ten kinds of power, each with its own techniques and passive:
| Kind of power (GOA) | Ours to name |
|---|---|
| Eyes that see chakra and copy a technique seen | |
| A shadow that binds, held by chakra | |
| Growing huge, with pills for strength | |
| Ice: needles, spikes, mirrors; walks on water | |
| Bone: hardened skin, bone weapons | |
| Blood bond: wounds shared with a foe; a ritual for a while undying | |
| Sand that guards and grips | |
| Puppets, bought and fitted with weapons | |
| Clay that explodes, shaped into birds and spiders | |
| A soft fist that blocks chakra | |
Plus traits for the clanless (more stamina, more chakra, a higher wound limit). Two clans first, then the rest.
- Check: each clan's techniques in a test fight; the eye clan's copy works on a technique cast at it.
- You decide: the clans' names and which two come first.

## Phase 6: Villages, ranks, missions, war (L)

- **Villages** as Banners' realms: three hidden villages and the rogues. A village leader (Banners' rulership) promotes.
- **Ranks:** student, then four ranks up to elite, gated by level and an exam.
- **The exam** (every 48 h or called by a leader): a scroll hunt in a closed forest (two halves of a pair to get in the
  tower), then a tournament.
- **Missions** D to A from a board (Banners' quests and bulletin board): deliveries, escorts, hunts, raids; XP 1,000 to
  7,000, shared in a squad.
- **War:** take a neighbouring region with enough players there; defended, a 10-minute war decided by deaths.
- **Shops:** supplies, bandages, pills, swords.
- Check: a mission from the board to its reward; an exam run with test players.

## Phase 7: Responsive (M)

- Measure every input: key to the ninja's first step (now 12-60 ms locally), click to the blow, key to a technique.
- Your own ninja moved on screen before the server answers, then corrected (no waiting on the network).
- 20 server ticks a second if the CPU allows (now 10): blows and techniques on finer timing.
- Check: the numbers before and after, online through the hosted link, not just on this Mac.

## Phase 8: Art and feel (ongoing, alongside)

- A male Elf body (elf men are on the Human body today); tune the 79 first-pass female bodies (Human Female is the
  only tuned one).
- Effects for each element and clan power (fire, water dragon, lightning, sand, ice, clay), as Banners' breath and
  spark effects are drawn.
- More GOA attack frames as clips (Ki side project: jab, cross, rising kick, aerial sweep).
- Keep the animations as they are; only add.

## Order, and who does what

1. Phase 1, then 2, 3 and 4 in this session, one after another: they all change the same game code and page, so two
   sessions at once would trip over each other's builds.
2. Phase 8's body work can run at the same time in its own session: it works in the GOA pipeline's folder
   (`standalone/remastered/reports/goa-sprite-test/staged`) and only copies finished sheets into Hidden Clans.
3. Phases 5 and 6 need your names and choices first; 7 can slot in whenever the lag bothers you.

Each phase ends with you playing it in the test world (http://127.0.0.1:8090 while it runs) or the app, a devlog entry
with pictures, and the app rebuilt.

## Only you can decide

- The village: gone (one ninja, GOA's way), or kept working on its own in the background.
- GOA's levels and stat points, Banners' skills, or both.
- The names: the game's world, the villages, the ranks, the clans, the techniques.
- Multiplayer first (villages, wars, exams need people) or single-player first.
- Who holds the rights to GOA's code and art: until then GOA is a reference, and its art stays in the GOA pipeline's
  own pictures that you've approved.
