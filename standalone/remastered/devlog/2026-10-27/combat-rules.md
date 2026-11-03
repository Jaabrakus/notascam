# Combat rules, second pass: what a player can read about a fight

## Decisions waiting for you

Nothing new. Last night's are still open in `devlog/2026-10-26/combat-rules.md`: morale lines at half, NPC warriors
at 15/15/12, quicker swings (my read: no), race stats on top of NPC levels, veterans in a pass, Lethal fists that only
knock out, traits, and the two training-vs-gear questions. The gear measurement you approved (step 0) is the lead's
job today (`reports/polish-night-1026/fixes-1027/gear-measure`). I changed no combat numbers.

**New today: bare fists that bleed out.** About 1 bare-fist duel in 20 ends with the loser bleeding out instead of
knocked out (28 knock-outs and 2 bleed-outs in 30 today), against "bare fists knock out first". Fists keep the
original's stacked blood loss and its bleeding over time, so a long brawl can run a unit dry first. Every fist fight
still ends. I measured one fix (fists bleed by the wound formula, as cuts do): 3 bleed-outs in 60 become 1, not 0, so
my read is no (`reports/polish-night-1026/combat-rules/options/fists-no-stacked-bleed/`). If you want fists never to
bleed anyone out, the cleaner rule would be "a bare-fist blow never starts bleeding": your call. Found while checking
screens' lower start rolls (landed by screens): those don't change it (1 in 30 with them).

## Landed

**combat-clarity** (`reports/polish-night-1026/combat-rules/clarity-1027/`). Four things a player couldn't read before:

| What you see | Before | Now |
|---|---|---|
| Chat, when a blow, shot or throw brings a unit down | "Grim collapses, bleeding out!" | "Grim is struck down by Thrak, bleeding out!" |
| Your log, the same moment | "Grim is bleeding out: 60 s to save them (...)" | "Grim was struck down by Thrak and is bleeding out: 60 s to save them (...)" |
| Your notice when a foe knocks out one of yours | "Grim was knocked out!" | "Grim was knocked out by Thrak: they wake in 30 s." |
| The card's Health tab, knocked out | nothing (only "Knocked out" as its order) | "Knocked out: wakes in 24 s" at the top, as it already did for "Bleeding out: 41 s left" |
| A unit whose Defence reaches 50 in the middle of a fight while Shaken | stayed Shaken until its morale drifted back | Steady at once (your rule: veterans are always Steady) |

- A unit that bleeds out from a stump's last blood, not a foe's blow, still reads "collapses, bleeding out", and
  names no one.
- Deaths already named the killer in your log ("Grim died (Thrak)"); falls now do too, so a fight reads the same
  way whether the unit is saved or not.
- Checked on the arena (`tests/cr_clarity.dm`, 7 checks): on today's game the four gaps above fail; on a clone with the
  patch all 7 pass, and on the live game after landing 7 of 7. Landed 11:58 (gate: compile, scripts, HUD, combat
  32/32, stumps 23/23); restore point `restore-points/before-polish-combat-clarity-20261027-111746`. Not built yet:
  it goes in the next batched build.
- **Speed: no measurable change.** The card's sheet costs 0.05-0.10 ms on both games, and a veteran's morale change
  costs 0.001-0.003 ms on both (`tests/cr_clarity_bench.dm`, 5 rounds of 1,000 sheets and 20,000 morale changes, each
  timed with `world.tick_usage`). Nothing else in it runs each tick.

## Landed: the old stats folded into the skills (your 21:55 "Fold old stats into skills", step 2)

Screens did step 1 (a new company's roll sets the skills; the Character tab shows one of each). This is the rest:
everywhere the game still read the old Strength, Agility or Intelligence of **your** units, it now reads the Strength,
Attack or Magic skill (plan: `planning/STAT_FOLD_PLAN_2026-10-27.md`; patch `reports/polish-night-1026/combat-rules/stat-fold/`).

- Covers melee and weapon-move damage, dodge, block, bow and throw aim, bites and grapples, heavy stone doors, a
  golem's grip, captives' win-over and escape odds, mind spells, magic and paper-making thresholds, the Evil Altar and
  a kill's XP: 38 places in 18 files.
- Bonuses still count on top: a werewolf's +20, a vampire's +8, a crown, tonics, surgery.
- Level-ups no longer add Strength and Agility to your units: their skills grow by use.
- Where Intelligence scales odds and costs (captives, mind spells, building), it counts up to 15 (today's top), so a
  Magic-60 mage doesn't swamp them.
- **NPCs, animals and great beasts are unchanged.** Folding NPCs would drop their preset Strength (50 and so on) and
  make every raid softer: that's your call, measured separately if you want it.

| 30 duels a row (units' character level and old stats as they'd really be at that level) | Before | After |
|---|---|---|
| Level 5 beats a recruit | 17 of 30 | 16 of 30 |
| Level 10 beats a recruit | 29 of 30 | 25 of 30 |
| Level 20 beats level 10 | 23 of 30 | 22 of 30 |
| Level 50 vs level 50 | 19 of 30 | 16 of 30 |
| Recruit duel length, plate / start kit / bare fists | 70 / 38 / 102 s | 80 / 45 / 118 s |
| Every bare-fist duel ends | yes | yes |
| 3 level-15s in plate beat 3 orc warriors | 14 of 30 | 9 of 30 |

- Who wins stays within chance. Recruit fights run 10-18% longer: a recruit's old Strength was its roll (about 7),
  and its Strength skill starts lower.
- The one to watch is level-15s against raiders (14 to 9 of 30, not significant on 30). Their old Strength had
  about 16 levels of gains on top of the roll (about 24), more than a Strength skill of 15. If raids feel harder,
  NPC warriors at 15/15/12 (last night's option) is the matching fix.
- Checks: the gate (compile, scripts, HUD, combat 32/32, stumps 23/23, obey 32/32), my fold check (11/11: skill as
  the number, bonuses kept and taken back, no level-up stats, NPCs unchanged, the switch), stone doors, golems and
  capture on the live game. Two old tests made a "strong" unit by its old Strength; they now set its Strength skill.
- **Speed:** the two stat reads on a blow cost about 1.5 us instead of 0.3 us. That's about 3 us on a blow whose strike
  chain costs about 150 us (2%); not measurable per tick. Switch: `rm_stats_folded = 0` brings the old stats back.
  Restore point `restore-points/before-polish-stat-fold-20261027-222714`.

**After the 60 s dying was removed (22:35):** the "struck down by" lines from this morning now show only if the
dying is switched back on. The rare bare-fist bleed-out (1 duel in 20) now ends in a death instead of 60 s down, so
your "should a bare-fist blow ever start bleeding?" question matters a bit more now.

## Checked and fine

- The morale card lines match your underdog table word for word (crits on 18-20 in a fury, Shaken lands a little less
  but its crits hit twice as hard, and so on), and veterans read "Steady: a veteran (Defence 50+)".
- The surround bonus counts only foes on their feet (not knocked out, bleeding out, asleep or a tied captive), so it
  hasn't got last night's morale miscount.
- Finishing off: only Lethal units, only with no standing foe within 5 tiles, never on another layer.

## Correction to last night

Last night's devlog said an iron breastplate takes 11% off a blow and a Hellforged one 17%. That left out that each
worn piece counts 6 times its Defence. The right numbers are 42% and 56% at full strength, and a Hellforged one
takes 46% at level 50 and 39% at level 25-35. Corrected there (the lead spotted it).
