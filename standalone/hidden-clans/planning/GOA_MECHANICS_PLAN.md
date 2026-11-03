# Carrying GOA's mechanics into Hidden Clans

Hidden Clans keeps Banners' body (limbs, wounds, blood, severing, KO by the Lethal toggle), its 3D world, villages,
work and RTS control. From Naruto GOA (`~/Downloads/GOA Source`, read 2026-11-01) it takes the *mechanics*: a chi
pool, techniques with seals and cooldowns, elements, clans, clones, ranks and missions. GOA's names are never used:
the words below are working names until the owner picks the real ones.

Play: your own ninja is played directly (GOA-style); the village's ninjas work and fight RTS-style.

## What GOA does, and where it lands

| GOA (code, numbers) | Banners already has | Hidden Clans |
|---|---|---|
| **Chakra**: max (500 + CON×5) × clan mult (750 at start); regains 1.5% of max a second; skills, water walking (5 a step) spend it; current can reach 3× max | Mana only inside staffs (`MagicGear.dm`), circuits (`Runes.dm`) | **Chi** on every ninja: a max from a stat, regain % a second, spent by techniques; a bar on the unit card and frame |
| **Stamina** = the knock-out bar (2000 + level×25 + STR×13); **wounds** to a limit of 100 = death; both regen | Health as the near-death bar, wounds per body part, blood, severing, no automatic healing | Keep Banners' body as it is (the owner asked to keep limbs). GOA's stamina/wounds don't come over |
| **Stats** STR, CON, RFX, INT from 50; level cap 100; +6 points a level | Strength, Agility, Intelligence, Defence; RuneScape skills Attack, Strength, Defence, Ranged, Magic (`CombatSkills.dm`) | CON becomes a new **Chi control** skill (chi size, technique damage). Magic's place: **Techniques**. Ranged/Throwing: kunai and stars |
| **Skills**: chakra/stamina/supply cost, cooldown, seal time (a freeze while forming seals), charge skills, 1 s global lock; 10-slot hotbar keys 1-0 | Race specials (`Specials.dm`): one aimed skill per race with cone/line/throw/self/dash/leap/blink shapes, range, cooldown, 3D aim preview; skill bar on the unit frame (`Abilities.dm`) | **Techniques** = the specials engine with many per ninja: chi cost, seal time (cast delay), cooldown, unlocked by skill levels. Cast for every selected ninja, as specials are |
| **Elements** Earth, Fire, Lightning, Water, Wind, 4 skills each; each extra element costs more (250…1050 points) | Fire and gas that spread (`Vapours.dm`), swimming, block-by-block mountains, stuns | Fire techniques start real fires; earth raises or breaks rock blocks; water works with rivers; lightning stuns. Elements are learned, more each costs more |
| **Clans** (10 bloodlines + village traits), each with 3-6 own skills: eye modes that see chakra and copy skills, shadow binding, growing huge, bone armour, sand that guards, puppets, explosive clay, blood bond, ice | Races, each with its own body and special | **Clans** as bloodlines on top of race, each with its own techniques and passive. Our own clans, built from the same kinds of power |
| **Taijutsu**: RFX rolls, combo meter (knockback above 13, daze above 20), block halves damage; gates: +30-60% at a cost of wounds | Melee land roll, moves through body parts, combat styles, knockback, morale | Taijutsu techniques on Banners' melee; a **Limit break** (gates) that pays in wounds |
| **Thrown weapons** use supplies (100, +20 a level of Projectile Master) | Throwing sub-skill, thrown items | Kunai and stars as thrown gear; exploding tags |
| **Clones**: decoy, a controllable copy, up to 21 AI copies for all your chakra | Units you command | Clones are real temporary units you can select and order: a natural RTS fit |
| **Substitution** (leave a log, return within 4 min), **flash step** (appear by the target, then a 2.7 s stun) | Dash/leap/blink specials | Two starting techniques every ninja has |
| **Ranks** Academy → Genin → … → Elite; exam every 48 h (scroll hunt, then a tournament); **missions** D-A with XP 1000-7000; villages, war over maps | Quests tab, bulletin board, quest maker plan, realms, rulership, wars | Ranks and exams as village events; missions as quests; GOA's villages map onto realms and wars |
| **XP from regenerating**: every second of chakra coming back gives XP | Skills train by use, slow RuneScape pace | Chi control trains by spending chi |

## First slice (proposed)

Small enough to play and judge in one sitting, in the browser:
1. **Chi** on every ninja: a max from Chi control, regains a share a second, a bar on the unit card and frame.
2. **Techniques on the specials engine**, several per ninja, each with a chi cost, seal time and cooldown, on the skill bar:
   - Substitution: swap places with a log when hit; the log stays.
   - Flash step: appear beside the target, then a short stun.
   - Fireball: a throw-shape fire burst that starts real fires (`Vapours.dm`).
   - Kunai: a thrown blade from carried supplies.
3. The village's ninjas use the same techniques under RTS orders.

Then: clans (two first), elements, clones, ranks and missions.

## Owner decisions still open
- Real names: the game, the chi pool, techniques, ranks, clans.
- Keys: Banners uses 1-9 for unit groups; GOA used 1-0 for the hotbar. Moving your ninja with keys is new too
  (Banners pans with the arrows only).
- Who holds GOA's code and art rights; until then GOA is a design reference only.
