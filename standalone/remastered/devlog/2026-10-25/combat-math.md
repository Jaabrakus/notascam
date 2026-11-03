# Combat: the math, and how it plays at scale (2026-10-25, unit-sprites session)

You asked for the numbers behind combat, and whether what makes sense for one unit against one still makes sense in a big
battle. Below: the formulas as the game runs them today, what real battles in the test arena did, and the knobs worth
trying.

## 1. The math

Times are game seconds. "Defence", "Attack", "Strength" and "Ranged" are the new skills (1-99, RuneScape style). "Sword",
"Bow", "Shield" and the rest are the original game's weapon skills. Agility and Strength (no "skill") are the original stats.

### How often a unit swings

Each weapon has its own swing timer, doubled by `rm_swing_pace = 2` (Hits.dm) for a slow, grindy feel:

| Weapon | Seconds per swing |
|---|---|
| dagger | 2.0 |
| arming sword, scimitar, fists, claws, bow | 2.4 |
| longsword, hand axe, mace, spear | 2.8 |
| morning star | 3.0 |
| warhammer, pickaxe, staff | 3.2 |
| battle axe | 3.6 |
| halberd | 4.0 |

A slower weapon hits harder by the same ratio: the blow's damage is multiplied by its timer over the unit's step (a
longsword about 3.5 times).

### Does a melee blow land?

In order, each a separate roll:

1. **Shield block:** (target's Shield ÷ 2 − attacker's Agility ÷ 4)%, at most 90%. A spear also blocks (Spear ÷ 50)%.
2. **Dodge:** target's Agility ÷ 4 − attacker's Agility ÷ 6, **+ target's Defence ÷ 12 − attacker's Attack ÷ 8**. No dodging
   with both legs gone or blind; half with one leg gone.
3. **Where it lands:** the original game rolls each body part on its own: head 3%, each arm 4%, each leg 4%, upper and lower
   body 4% each. About **1 blow in 4 hits a part at all**; the rest do nothing. Weapon moves (Lunge, Cleave...) always land.

### How hard it lands

    weapon damage (its min to max) + Strength ÷ 2
      + Strength skill ÷ 6 − target's Defence skill ÷ 8
      + 3 for each blow before it that did nothing (an "opening")
    × the swing factor (above), at least 5
    then the armour on the part it hit takes its share: armour ÷ (armour + 100),
      armour = the piece covering that part × 6 + the body's own toughness

A blow of 28 or more that doesn't kill knocks the target back a tile (a warhammer two) and stuns it a moment
(`rm_knock_dmg`, Hits.dm).

### What kills

Not the HP bar alone. A unit's health is every part added up (a new human: **2,770**, of which HP is 350). A unit dies
when a vital part goes (head, heart, brain, throat...), when it bleeds out, or when HP reaches 0. So a few blows to the head
kill, while many to an arm cripple it.

### Arrows

1. **Hit:** **Bow ÷ 4 + Agility ÷ 2 + Ranged ÷ 8 − target's Defence ÷ 12** (the target's Defence counts since today).
2. **Shield block:** (Shield ÷ 2)%; the arrow sticks in the shield.
3. **Armour turns it** (only with chest armour): **(Defence + Armour skill) ÷ 10**% (the skills since today).
4. **Where:** a d20: 1-2 a leg, 3-4 an arm, 5-6 the head (an eye), 7 the heart, 8 the belly, 9-10 a lung, 11-20 the body.
5. **Damage:** the bow's own damage + Ranged ÷ 6 − target's Defence ÷ 8, less the armour on that part.

### Thrown javelins and axes

Hit: 35 + Agility + Throwing ÷ 4 + Ranged ÷ 8 − target's Defence ÷ 12 (between 5% and 95%), then a shield block
(Shield ÷ 2)%, then a leg, an arm or the chest (the chest twice as likely), less that part's armour.

### What the skills do, in one line each

- **Attack:** fewer of your blows are dodged (one point per 8 levels).
- **Strength:** your blows hit harder (one point per 6 levels).
- **Defence:** you dodge more (one point per 12 levels), take less from blows and arrows (one point per 8 levels), are hit
  by fewer arrows and throws (one point per 12 levels), and your armour turns more arrows.
- **Ranged:** more arrows and throws hit (one point per 8 levels) and they hit harder (one point per 6 levels).
- **Weapon skills:** their own tricks (a sword parries, an axe cleaves a second foe, a mace staggers, a spear reaches two
  tiles) and they unlock the weapon moves. No weapon skill goes above Attack.

## 2. The test: real battles in the arena

`tests/battle_scale_check.dm`: two realms at war. Both sides are new humans with iron longswords and their own starting
stats (Strength about 8, Agility about 9, Sword 20, Bow 15, every new skill at 1). Every fight ran at once in its own field
at speed 4. An idle unit goes at the nearest foe, and the side that orders first swaps each tick. Three runs:

| Fight | First death | Over at | Swings per kill | Blows that drew blood | Winner left |
|---|---|---|---|---|---|
| 1 v 1 | 10-35 s | 10-35 s | 6-23 | 17-33% | 1 |
| 5 v 5 | 6-15 s | 49-95 s | 13-16 | 14-23% | 1-2 of 5 |
| 20 v 20 | 1-8 s | 54-73 s | 14-15 | 15-18% | 5-13 of 20 |
| 50 v 50 | 1-5 s | 82-146 s | 17-18 | 15-17% | 4-27 of 50 |
| 10 swords + 10 bows v 20 swords | 5-7 s | 59-63 s | - | - | the all-sword side, 12-16 of 20 |

- **Each landed blow did about 120 of a body's 2,770 points.** About 1 swing in 6 draws blood.
- **The archers:** 75 arrows, 3 drew blood (4%). At starting skill an archer's chance to hit is about 8%.

## 3. What it says at scale

- **One against one is fairly slow, but a battle isn't.** A lone duel takes 10-35 s. In a battle the front line gangs up:
  the first death comes in 1-5 s, and kills come faster the bigger the fight (0.16 a second at 5 v 5, 0.66 at 50 v 50). A
  50-unit army is gone in about 1½ to 2½ minutes.
- **It snowballs.** With equal sides the winner is a coin toss, and it ends with anywhere from 4 to 27 of 50 left. Whoever
  gets the first few kills outnumbers the rest and wins big. Formations, terrain and numbers will matter a lot (good for
  war bands).
- **Swings per kill barely change with size** (about 15). What changes is how many swing at once.
- **Starting archers are a waste of a soldier.** At about 8% to hit they barely matter, and an army that swaps 10 swords for
  10 bows loses badly. They become useful as Bow, Agility and Ranged grow: Bow 40, Agility 20 and Ranged 30 is about 24%.
- **3 blows in 4 doing nothing** (the original's body-part roll) is the main reason fights take as long as they do. It's
  also why they feel random: two blows to the head end a fight that twenty to the arms didn't.

## 4. Numbers to try

| Knob | Where | Now | What it would do |
|---|---|---|---|
| `rm_swing_pace` | Hits.dm | 2 | 3 = everything a half slower; 1 = the original's pace |
| the body-part roll | Combats.dm (HitHead 3, others 4) | ~1 blow in 4 lands | higher = faster, less random fights |
| `RM_DEFENCE_DODGE` / `RM_ATTACK_DODGE` | CombatSkills.dm | 12 / 8 levels a point | lower = skills matter more against each other |
| `RM_STRENGTH_DMG` / `RM_DEFENCE_DMG` | CombatSkills.dm | 6 / 8 levels a point | lower = levels matter more for damage |
| archers' starting chance | Combat - Bows.dm (Bow ÷ 4 + Agility ÷ 2) | ~8% | a base of +15 would make new archers useful |
| `rm_knock_dmg` | Hits.dm | 28 | lower = more knock-backs in a fight |

To rerun the battles after a change:

    python3 tools/runlock.py --who you --kind run -- python3 tools/check_arena.py --test tests/battle_scale_check.dm --entry BsRun --timeout 900

The results are the `BS|` lines in `tests/battle_scale_check-checks-server.log`. It reports FAILED only because it has no
pass/fail checks.

**Open questions for you:**
1. Should a 50-unit battle last longer than about 2 minutes?
2. Should new archers be worth fielding from the start?
3. Should 3 blows in 4 keep doing nothing, or should more of them land?

## 5. After the rework: training pays (22:30-23:00)

**Undone (23:10):** it landed, then the duel test showed fights at 52-55 s instead of about 85, every duel ending in death with no knock-outs, and recruits learning the lunge mid-fight. You chose to undo it and keep the wounds. It is out of the game; the landed version is kept in `restore-points/training-landed-20261025`. A retry has to beat fights of about 85 s, some knock-outs and limbs off in most fights.

You asked for training to pay: Ranged caps Bow and Throwing, the skills count about 4 times as much, Agility counts half,
and blows land about twice as often at half the damage. That is now built and tested (`reports/gear3d-staged/training`,
`tests/training_check.dm` 4/4).

### The new numbers

- **Attack:** one point off the enemy's dodge every **2** levels (was 8).
- **Strength:** one more point of damage every **1.5** levels (was 6).
- **Defence:** one point of dodge every **3** levels (was 12), one point off a shot's chance to hit every 3 levels, and one
  point less damage every **2** levels (was 8).
- **Ranged:** one point to hit every **2** levels (was 8), one more point of damage every 1.5 levels (was 6).
- **Bow and Throwing** are held at the **Ranged** level (they were held at Attack). An archer now trains by shooting.
- **Agility** counts half: the dodge (Agility ÷ 8 against ÷ 12), a shield block (− attacker's Agility ÷ 8), an arrow
  (Agility ÷ 4) and a throw (35 + Agility ÷ 2).
- **Blows:** the body-part chances are doubled (`rm_blow_land 2`), so about 2 blows in 5 hit a part, and each does half
  (`rm_blow_share 0.5`). Knock-backs start at 14 damage instead of 28.

At level 99 against level 1, Attack now takes 49 off the dodge (was 12), Strength adds 65 to a blow (was 16), and Ranged
adds 49 to an arrow's chance (was 12).

### The battles again (two runs)

| Fight | Over at | Blows that drew blood | Damage per landed blow | Winner left |
|---|---|---|---|---|
| 1 v 1 | 15-91 s | 39-45% | 50-90 | 1 |
| 5 v 5 | 57-60 s | 31-34% | 54-60 | 4 of 5 |
| 20 v 20 | 83-84 s | 32-34% | 71-72 | 11-12 of 20 |
| 50 v 50 | 93-128 s | 30-32% | 72-75 | 17-23 of 50 |
| 10 swords + 10 bows v 20 swords | 70-80 s | - | - | the all-sword side, 15-16 of 20 |
| **20 trained (level 50) v 40 fresh** | **25-29 s** | 26-29% | 147-149 | **the trained: 19 of 20** |
| **10 swords + 10 trained bows (50) v 20 swords** | 48-69 s | - | - | **the side with bows: 16-17 of 20** |

- **Training pays now, a lot.** Twenty level-50 units wiped out forty fresh ones in under half a minute, losing one.
- **More blows land and each does less.** Blood is drawn on about 1 swing in 3 (was 1 in 6) for about 60% of the
  damage. Fights last about as long as before (a 50-unit battle 1½ to 2 minutes) and end with steadier numbers left: 11-23
  where it was anywhere from 4 to 27.
- **Fresh archers are worse than before.** With Agility counting half, a new archer hits about 6% of the time. Trained ones
  (Bow and Ranged 50) hit about 39% on paper, and the side that had them won with 16-17 of 20 left. (The test counts an
  arrow as landed only when it hurts at once, so it undercounts arrows.)

**Still open:** should a new archer start with a base chance to hit, as a throw has (35)? A base of +20 would make a
fresh archer hit about a quarter of the time.
