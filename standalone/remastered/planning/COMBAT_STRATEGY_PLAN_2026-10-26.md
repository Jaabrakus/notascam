# Combat strategy plan (2026-10-26)

The user's aims: "a balanced system with some dopamine hits"; a trained unit that dies quickly "would devastate" a
player; players "want strategy ... flanking to feel rewarding"; units that grow strong must stay rewarding without
making old players unbeatable. Each system below is designed and tested first. Its numbers go to the user, who
decides before anything lands.

## Principles

1. Decisions win battles; dice decorate them. A loss should read "I got flanked", not "I rolled badly".
2. In the open, numbers win: an army's strength is about quality x numbers squared (Lanchester), so a veteran is worth
   the square root of its strength in recruits. Where fights go one at a time (a gate, a pass, a tunnel, a shield
   wall), a veteran is worth its full strength. So veterans are pieces you place, not a stat multiplier.
3. Losses hurt but are savable: knock-outs, the bleeding-out rescue window, routing, capture and ransom.
4. No hand-holding for new realms (no safe zones or truces), but recruits can still win with numbers and terrain.
5. Test battles, not only duels. Duels (tools/check_pace.py) tune a blow; battles show strategy.

## Where combat stands (build 52)

- Melee: one land roll (27% at level 1: 27 + (Attack-1)/4 - (Defence-1)/6), then one d20 for the body part.
- Weapon moves: their own land roll, 30 + (Attack-1)/4 + (weapon skill-1)/4 - (Defence-1)/6. They hit a d20 part
  through armour.
- Criticals: a natural 20 always lands for 1.5x (shield and dodge still apply first).
- Armour per part: armour / (armour + 100). Real plate (Quality, Defence 12) stops about 44%.
- Wounds bleed by a formula. Slashing cuts can sever, and Defence lowers the chance. A d20 armour save turns a sever
  into a crushed limb.
- Bleeding out is a 60 s rescue window. A unit still up treats itself first and calls for help once. A downed unit
  never treats itself.
- New units start at level 1 in Attack/Strength/Defence. Combat XP is RuneScape's pace (1 per point of damage).
  Skills count 2x.
- Duels, real plate:
  - recruit vs recruit: sword 63 s, plate 130 s, limbs off in 7-8 of 8 fights;
  - level 25 beats a recruit 8/8 in 50-56 s;
  - level 50 beats a recruit 8/8 in about 30 s.
- Missing:
  - facing (a shield blocks from any side), flanking, morale, routing;
  - NPC combat levels (every raider sits at level 1);
  - battle-level tests.

## The systems, in order

### 1. NPC combat levels (LANDED, build 53)
- Seeding from the original skills made scouts 25-40 and warriors, guards and leaders 99/99, so one wandering scout
  could wipe a new 3-unit realm. The user: "lets do our own what we think would be right".
- So NPCs are seeded by role instead (Attack / Strength / Defence, then Ranged):
  - Villager 5/5/5, Ranged 1;
  - Scout 10/10/8, Ranged 10;
  - Hunter 12/10/8, Ranged 20;
  - Warrior 25/25/20, Ranged 10;
  - Guard 35/30/45, Ranged 15;
  - Commander / Chieftain 50/50/40, Ranged 25;
  - bosses (King, Lord, Warlord, Lich King, Skorn, Demon lord, Noble) 75/75/65, Ranged 40.
- Race offsets: orcs +5 Strength, goblins +5 Attack, dwarves +10 Defence, lizardmen and frogmen +10 Ranged,
  kobolds and ratmen -5 on all.
- Aims: a fresh realm beats a lone scout together; three warriors wipe a fresh realm in the open but not one with
  level-15 units or walls; guards hold doors; bosses need a trained army.
- Later: when raids come, and danger rising with distance from a realm's start.
- Check: a before/after level table per NPC. No battle test (the user's call).

### 2. Facing and flanking (LANDED, build 54; fix in progress)
- Firm-up, 10 battles per case at 4x: facing as built rewarded the holding line and punished attackers.
  - Head-on: the holding line won 9/10 off, 8/10 on.
  - Flank: the attacker won 3/10 either way.
  - Rear: the attacker won 6/10 off but only 1/10 on, because the line saw it coming at 3 tiles and turned.
- Fix, the user's choice "(a) + (b) together":
  - (a) rear surprise: no noticing a foe in the rear arc until struck or the foe is beside it;
  - (b) a charge: a unit that moved 2+ tiles into contact has its sides covered for ~1 s, and its first blow gets +25%
    damage and +2 to land.
  Then re-run the 10 per case.
- Landed with morale, build 55 (the user, 10-26: "Land both"). Results, 10 a case, off -> on: head-on holder 8 -> 10,
  flank attacker 3 -> 4 (misses "clearly loses"), rear attacker 4 -> 6, veterans flanked holder 10 -> 10.
- Next (the user, 10-26): re-run at 30 a case before changing flanks; a sword parry follows facing like the dodge
  (half from the side, none from behind; it ignored facing, 6-30%).
- 30 a case (Unit sprites, 10-26, facing2 + morale in), attacker wins off -> on: head-on 3 -> 6, flank 12 -> 12, rear
  12 -> 12, veterans flanked 0 -> 0. Facing changes no outcome: once the lines meet, side and rear blows fall on both
  sides alike (59 vs 58 a fight), because a flanked side with nothing in front simply turns round. Flank and rear
  already beat head-on (40% vs 10-20%) from geometry alone. The 10-a-case numbers were noise.
- Parry follows facing: staged (parryfacing/land_parry.sh), per 100 blows front/side/behind 6.0/4.1/0.5 (recruit),
  18.0/12.7/2.1 (Sword 99); battle table to come before landing.
- Pinning: staged by Unit sprites (pinning/land_pinning.sh; facing_check 19/19), NOT ready. 30 a case, attacker wins
  without -> with: flank 12 -> 11 (p 0.79), rear 12 -> 9 (p 0.42); 4-5 units pinned a side a fight. No effect, because
  all 20 attackers go round, so nothing holds the front. Next: a hammer-and-anvil test (10 at the front + 10 at the
  side or back vs 20 holding, against 20 head-on), facing and pinning off vs on; the user decides (Unit sprites asks).
- Hammer and anvil (Unit sprites, 10-26; 10 at the front, 10 behind about 2 s later), attacker wins of 30, no pin -> pin:
  5 -> 3 (p 0.45); head-on 6 -> 9 (p 0.37). Still no effect: the holding line is 2 deep, the anvil pins only its front
  row and the back row turns to the hammer; splitting the attackers lets the holders beat each half. Pinning stays
  staged; 2c (surround bonus + high ground) is next.
- Facing is the unit's world direction on the server (its dir, 8 ways), not the camera. The 3D view already draws
  the sprite's side from that direction and the camera angle (gear3d.js), so orbiting only changes the view (the
  user asked, 10-26).
- Each unit faces where it last moved, or the foe it is attacking. It does not snap round to every attacker: turning
  to a new target takes about 0.5 s, or flanking would never count. The original turns instantly; this needs care.
- Arcs of the 8 tiles around a defender: front = its facing +-45 degrees (3 tiles), side = +-90 (2), rear = +-135
  and straight back (3). Possible refinement: the shield is on the left arm, so the left side keeps half the shield
  block and the right side gets none.
- At army zoom, a notch on the selection ring (or a formation's front edge) shows facing. No far-unit arrows.
- Hit from the side (90 degrees off its facing): no shield block, half its dodge.
- Hit from behind: no shield block, no dodge, and criticals on 18-20 (15%) instead of only 20.
- Awareness roll (the user, 10-26: "a skills check where units roll"): a blow from the side or rear makes the
  defender roll a d20 to turn in time: 15+ (side), 19+ (rear), +-1 per 10 levels of its Defence over or under the
  attacker's Attack, a natural 20 always turns. Made: it counts as from the front, "Turned to meet it!". Rates:
  - recruit vs recruit: side 30%, rear 10%;
  - Defence 50 vs recruit: 55% / 35%.
  Turning to a new target speeds from 0.5 s to about 0.3 s with Defence. Switch rm_aware_on.
- A floating "Flanked!" / "From behind!" when it happens. The battle report counts them.
- Switch: rm_facing_on. Size: medium (Combats.dm CheckDefence, the land roll, the 3D word).
- Test: 20v20 head-on against 20v20 with one side taken in the flank. Target: the flanked side clearly loses.

### 2b. Parting blow (DROPPED 10-26, the user: "Parting blows no good and remove"; in testing it fired 400-700 times a fight as melee units shift tiles, halving fights; never in game/, staged work deleted. Was approved 10-26; the user, 10-26: "a parting blow allows players to get a hit on routed units")
- Today a unit walking away from a swordsman at the same speed is never hit again; only archers, throwers and spears
  punish a retreat or a rout (Creatures/Bump.dm: melee only on the chosen target, swings on their own timer).
- Rule: a unit that steps from beside a foe to a tile out of its reach (1 tile, a spear 2) gives that foe a swing.
  - Who: each foe beside it that can swing (a melee weapon or fists, awake, an arm free). Surrounded by 3, up to 3.
  - The swing: the foe's next normal swing taken at once (land roll, d20 part, armour save, crits); its swing timer
    restarts from it, so no extra swings over a fight, only one that lands before the unit gets away.
  - From where: the leaver faces where it walks, so it is mostly from behind (no shield, no dodge, crits 18-20); the
    rear awareness roll (19+) can still turn and meet it.
  - Limit: once per foe per leaver every 5 s (no stepping in and out for free blows).
  - Sidesteps that stay beside the foe give none. Morale as for any blow; no new morale rules.
  - Switch rm_parting_on. Size: small (the step in Move, only for units in a fight in the last 10 s).
- Odds of a parting blow from behind (land roll 27 + Attack/4 - Defence/6; 15 in 100 swings are crits from behind):

  | Swinger -> leaver | Lands | Crits |
  |---|---|---|
  | Recruit -> recruit | 27% | 15% (over half the hits) |
  | Attack 50 -> recruit | 39% | 15% |
  | Recruit -> Defence 50 veteran | 19%, and it turns to meet it 35% of the time | 15% |
  | 3 recruits around one recruit | at least one lands 61% | |

- After the parting blow, routers at full speed still outrun melee; archers, throwers and spears finish them, and a
  unit with both legs crushed or lost crawls (a tile every 2 s) and can be caught.
- Pros: retreats and routs cost a blow against melee too; surrounding pays more (fits flanking); existing dice, one
  new number (5 s); no extra swings overall.
- Cons: breaking out of a surround gets deadly; a rescuer carrying a downed friend out of a fight takes the blows; a
  player pulling a wounded unit back to bandage pays one too.
- Test: 20v20 where one side retreats at 50% losses, on and off; and the rescue window's saves, on and off.

### 2c. Surround bonus and high ground (NEXT, after the current work is perfected)
The user, 10-26: "start with the surround bonus (with veterans resisting swarms) plus high ground we can build this
next and let perfect what we are doing now". Why: facing and pinning change no battle result (2, 2b notes); what wins
is more of your units touching fewer of theirs. The user also wants heroes' "Spartan 300 vs 10k" moments: chokepoints
cancel the bonus, so a held pass or door makes the veteran's own skill count.
- Surround bonus: every enemy beside a unit (its 8 tiles) beyond the first gives each attacker +5 to land on it
  (melee land roll, CombatSkills.dm). Only foes actually beside it count, so rock, trees, water and doors limit it.
- Veterans resist swarms: Defence 50 ignores 1 extra foe, Defence 80 ignores 2.
- High ground: a unit standing 1+ block above its foe gets +5 to land in melee; its arrows reach 1 tile further.
- Switches rm_surround_on, rm_high_ground_on. Later, if battles need them: tree cover (arrows -10) and bad footing in
  shallow water or swamp (its own blows -5).
- Numbers, Defence 50 veteran against recruits (land 19% one on one):

  | Where it stands | Foes that reach it | Each lands | Hits on it a round |
  |---|---|---|---|
  | Open, swarmed (6 around) | 6 | 39% | 2.3 |
  | Shield line (allies at its sides, front 3 tiles open) | 3 | 24% | 0.7 |
  | Pass, tunnel or door, 1 wide | 1 | 19% | 0.2 |

  Recruits around one recruit: 1 -> 0.27 hits a round, 2 -> 0.64, 3 -> 1.11, 4 -> 1.68.
- Pros: surrounding pays even in a scrum (only the side with local numbers gets it); veterans hold passes and are
  still beaten by swarms in the open; terrain becomes the strategy; existing dice.
- Cons: numbers matter more in the open; a trapped veteran falls faster; a held pass may be too strong (siege engines,
  archers and diggers are the counters).
- Tests: 10 veterans vs 100 recruits in the open and in a 3-wide pass, on vs off; 20v20 in the open (fight length);
  20v20 for a hill vs on flat ground; the duel table unchanged one on one.

### 3. Morale (in progress: Unit sprites): two parts, personal and group

Combat only: it starts at 0 when a unit enters combat and ends 10 s after. Total = personal + group, -100..+100.

| Personal: its own fight | Change |
|---|---|
| It lands a blow | +1 |
| It lands a critical / a crush | +3 |
| It severs a limb / kills | +5 |
| It is hit from the side / from behind | -2 / -4 |
| It fights 2 or more foes at once | -1 a second |
| It loses a limb | -15 (half for a veteran that lost one before); a crushed or missing limb caps it at Steady until treated |
| Second wind: a critical or kill while Broken | +20 |
| It is treated (bandaged, rescued, the Doctor) | +10 |

| Group: what it sees within 4 tiles (switch rm_morale_group) | Change |
|---|---|
| An ally lands a critical or crush | +1 |
| An ally severs a limb or kills | +2 |
| An ally is crushed / severed / dies | -2 / -3 / -5 |
| Its ruler or an NPC leader dies within 6 tiles | -20 (kept by the user, 10-26: killing a commander is a strategy) |
| Its side is outnumbered 2:1 around it | -1 a second |
| A banner, war drums or a hero within 6 tiles | +1 a second, up to +30 |
| Covering hit: an ally hits the foe attacking it while it is Shaken or Broken | +3 ("Covered!") |

Rules for both:
- A change away from 0 is scaled by (1 - |total| / 100); a change toward 0 counts in full.
- After 3 s with no change it drifts back toward 0, 1 point every 2 s.
- Shake-off: when it lands a blow, a negative group part is cleared to 0.
- Committed: a unit that made a covering hit has its awareness roll 3 harder for 3 s.
- Log: Village > Log (Morale filter), the player's own units, state changes only, grouped in one line.

| State | Line | Sever chance (attacker) | Armour save (defender) | Awareness roll | Criticals | Bleeding | Self-care |
|---|---|---|---|---|---|---|---|
| Battle fury | +60 | x1.25 | -2 | no roll | - | adrenaline: 25% slower in the fight | won't bandage mid-fight |
| Emboldened | +30 | x1.1 | - | 3 harder | 19-20 | adrenaline: 15% slower in the fight (the user, 10-26: "Keep 15%") | - |
| Steady | -30..+30 | - | - | - | - | - | - |
| Shaken | -30 | - | +1 | 3 easier | none | adrenaline: 15% slower in the fight | bandages first |
| Broken | -60 | - | - | - | none | adrenaline: 25% slower in the fight | - |

- States enter at their line and leave 5 points back inside.
- Adrenaline (the user, 10-26: fight or flight works both ways): blood held back in Battle fury, Emboldened, Shaken or Broken (only Steady bleeds at the full rate) is all lost at once when the fight ends (the user, 10-26: "All at once like it is now", not drained over time); a unit that drops into bleed-out gets the 60 s rescue window.
- Knock-out or kill is the striker's Lethal toggle only (Subdue.dm), never a roll (the user, 10-26: "we have lethal and non lethal toggle so we should really pick and choose to knock out or kill").
- Emboldened and Committed add up: awareness roll 6 harder.
- No dodge, block, flat damage or move-speed changes.
- Player units never flee on their own; NPC raiders rout when Broken.
- Shown while fighting: a bar centred at 0 and the state icon on the card, and a word in 3D when the state changes.
- Test: morale off vs on, by layer. The first sever or kill's win rate must not rise.

### 3b. A skill bar for area attacks (the user, 10-26: "a skill bar the user can click for aoe spells from casters and ranged units and or throwables"; after morale)
- Select units and a bar at the bottom of the HUD shows what the group can do. Each button shows how many units can,
  plus a cooldown ring. Hotkeys must avoid A, the digits and R.
- Click a button, then the ground: the exact tiles it will hit light up, not a circle (the user, 10-26). Volley shows
  its 3x3 tiles, Fireball its blast as a small tile diamond. The highlight follows the cursor and fades like the
  placement grid once it fires. Tiles holding your own units glow a warning colour. On mountains it sits on the top
  block the effect lands on. The selected units walk into range and fire together.
- Abilities:
  - casters: Fireball (about a 2-tile blast, sets fire), chain lightning, a healing circle;
  - archers: Volley, using arrows. Drag a line of tiles where it should land (the user, 10-26: "draw a tile line of
    where to shoot ... condense or spread out"). The archers split their arrows along it, so the line's length sets
    the spread: 10 archers on 3 tiles is ~3.3 arrows a tile, on 10 tiles 1 a tile. Each tile's brightness shows its
    arrows. A plain click is the default 3x3. A modifier key makes the line 2 rows deep (a formation's front and second
    rank). Like a formation drag sets its width (Formations.dm remaster_face);
  - throwables: a javelin or axe throw, firepots or bombs (splash and burn, used up);
  - siege: the catapult's existing splash (Siege.dm), aimed from the bar.
- Limits: a cooldown per unit, plus magic charge or ammunition. Friendly fire hits your own units in the circle (it
  could follow the Lethal switch). An auto-cast toggle per ability for offline players.
- Why: area attacks counter blobs (a fireball hits 9 in a 3x3 clump, 2 in a spread line), breaking "numbers win" and
  rewarding formation and timing.
- Builds on MagicTarget.dm (single-target magic today) and Throwing.dm.
- Owners: HUD craft (the bar, the targeting circle), Unit sprites (rules, effects).
- Test: a blob against a spread line under Volley and Fireball; the worst server tick in a 1,000-unit battle.

### 4. Battle tests (a tool, built once and used by every system)
- Cases:
  - 20v20 straight vs flanked;
  - 20 veterans vs 40 recruits;
  - one level 50 vs 2/3/4/6 recruits, in the open and in a one-tile doorway (the user said not yet);
  - holding a narrow pass.
- What it reports: winner, survivors per side, time, routs, limbs off, crushes, flanks, and the server's worst tick
  (big-battle lag is a launch blocker).
- Base it on Unit sprites' tests/battle_scale_check.dm, at speed 4.

### 5. Veterans lift others (needs morale)
- Steadiness: a unit's morale floor and its gain grow with its level, e.g. at level 50 it never drops below 20 while a
  friend stands beside it.
- Leadership: a unit with Attack or Defence 40+ given the role of sergeant or banner-bearer raises the morale of
  recruits within 4 tiles by +1 a second, and they waver later (under 20 instead of 30).
- A level-60 veteran in a recruit line makes the line hold. An old player's edge then comes from leading numbers well.
- Test: 20 recruits with and without a level-50 sergeant, against 20 recruits.

### 6. Veteran rewards (no balance effect, all pride)
- A veteran mark on the unit and the card at levels 25, 50, 75 and 99.
- A title from a list: "the Shieldbreaker", "One-Arm", "the Unbowed".
- Kill and battle tallies on the card.
- Scars and lost limbs tell a story: memory lines such as "lost his arm at the river".
- New weapon moves at milestones (10 Lunge today; more at 30, 50 and 70) for variety, not only numbers.

### 7. A WoW-style ability kit (horizontal growth; needs facing for some)
- Units use these by themselves on a shared 1.5 s cooldown between swings. The player sets each unit's or group's style
  on the Combat tab (as Accurate / Aggressive / Defensive today).
- The kit:
  - Rend: a cut that keeps bleeding;
  - Hamstring: a leg hit that slows;
  - Sunder: dents the armour on that part for the fight;
  - Overpower: a sure hit after the target dodges;
  - Revenge: a strong counter after a block;
  - Shield Bash: a short stun;
  - Execute: a finisher on a badly hurt part;
  - a war cry: nearby foes' Attack drops, ties to morale.
- Each needs a rule, an animation and a duel test. Size: large.

### 8. Capture and ransom (needs routing)
- A roped enemy veteran can be ransomed back to its owner for a price both sides see (its levels decide the price), or
  kept, or enslaved, as today's capture rules allow.
- Veterans become prizes; a lost battle need not wipe years of training.

### 9. Costs that keep veteran armies a choice
- Upkeep: food and pay rise with level.
- Fatigue in long fights: swing speed drops after 60 s of fighting; rotating lines matters.
- Injuries and lost limbs slow them. Old age ends them.
- A retired veteran can train recruits faster (legacy).

## Open decisions for the user

- Quicker swings: a third quicker at three-quarters the damage, same fight length. Not decided.
- Parting blow (2b): DROPPED (the user, 10-26: "Parting blows no good and remove").
- Formations and frontage: on hold since 10-25; they pair with flanking and morale.
- The order above, and which of 2-9 to start after NPC levels.

## Ownership

- Unit sprites in 3D: combat rules, moves, wounds, animations (1, 2, 3, 5, 7).
- HUD craft: morale, banners and the battle report on the page.
- The coordinator: landing, builds, and the duel and battle tables for the user.
