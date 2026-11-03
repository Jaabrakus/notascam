# Traits: a plan (2026-10-26 night, combat-rules; for after the feature freeze, nothing built)

The owner, 10-26 ~21:40: "so we should do traits for skills level increases? right and then trait trees depending on
what and how they evole right?", then: "so this trait system will be handsoff they just obtain it... we need a huge list
of traits and stat gains and then negative traits so this would be perfect".

It fits the standing rules: **no fixed classes** (roles come from skills and gear, and now from what a unit lived
through), **veterans rewarding but not unbeatable**, **brutal but savable losses** (a loss leaves a mark), and
**players plan, workers act** (nobody picks traits; units earn them).

## 1. How it works (hands-off)

1. **Every unit keeps a tally of what it does** (its deeds): blows parried, blows taken on its shield, foes felled with
   each weapon, limbs taken, falls survived, fights won outnumbered, fights on high ground, nights slept rough, blocks
   mined, meals cooked... These are cheap counters kept on the unit and saved with it.
2. **A skill level-up at a milestone gives a trait at once**: levels 5, 10, 20, 30, 40, 50, 60, 70, 80, 90 and 99 of any
   skill. The game picks it, nobody chooses: from that skill's tree, weighted by the unit's deeds (a swordsman that
   parried 400 blows gets a parry trait; one that took 200 blows on its shield gets a shield trait).
3. **Trees branch**: most traits have a tier 2 and tier 3 that come only to a unit that already has tier 1 and keeps
   doing that thing. Two Sword-50 units end up different, by how they fought.
4. **Negative traits come from what happens to it** (a limb lost, a fall, starving, captivity, a rout...), at the
   moment it happens, not at level-ups. Some can be overcome later by deeds (a "Shaky hands" unit that lands 100 blows
   loses it; "Scarred" turns into "Battle-scarred" at 3 healed wounds).
5. **Small and sideways**: each trait is a few percent, and most have a cost. A level-99 unit with every combat trait
   should still lose to a swarm in the open (tonight's battle numbers: ten level-50s already lose 10 of 10 to a hundred
   recruits, even in a 3-wide pass). Cap: **6 positive traits shown and working** at a time (the newest replace the
   oldest of the same tree), negatives uncapped.
6. **Shown**: a Traits tab on the unit card (one tab per thing, as the card rule says), each trait with one line of
   what it does and how it was earned ("Shieldwall: took 212 blows on its shield"). A Village > Log line when one is
   gained or lost. No pop-ups.
7. **Saved with the unit**; a captured or traded unit keeps them. Inherited traits are a later idea (families).

## 2. The trees (positive traits)

Effects use the game's own words: land chance (the melee land roll, percent points), damage, sever chance, armour save
(the d20 that turns a sever into a crush), bleed, morale (no effect on Defence 50+, tonight's rule). "T1/T2/T3" = tier.

### Attack (how it strikes)

| Trait | Tier | Earned by | Effect | Cost |
|---|---|---|---|---|
| Keen eye | T1 | landing 100 blows | +2 to land | - |
| Precise | T2 | 300 blows on limbs | its d20 body roll can be nudged one face toward a limb | crits on 20 only (no morale crit faces) |
| Surgeon of war | T3 | 50 limbs taken | sever chance x1.15 | -1 to land on armoured foes |
| Relentless | T1 | 30 fights lasting 60 s+ | swings 5% quicker after 30 s in one fight | swings 5% slower for its first 10 s |
| Opportunist | T1 | 50 blows on foes already fighting another | +3 to land on a foe whose target is someone else | -2 to land on a foe facing it |
| Executioner | T2 | 20 downed foes finished | finishing blows never fail; its own see it: +1 morale | its foes nearby: +2 morale (spite) |
| Duelist's patience | T1 | 20 one-on-one wins | +3 to land when only one foe is beside it | -3 when two or more are |
| Swarm fighter | T1 | 30 fights with 3+ foes beside it | ignores one extra foe for the surround bonus | - |
| Cleaving arc | T2 (axe) | 50 cleaves | cleave chance x1.25 | plain blows x0.95 |

### Strength (how hard)

| Trait | Tier | Earned by | Effect | Cost |
|---|---|---|---|---|
| Heavy hand | T1 | dealing 5,000 damage | +4% damage | swings 3% slower |
| Bone breaker | T2 (mace/fists) | 40 crushes | crush and stagger chance x1.2 | - |
| Knockout artist | T2 (fists, Non-lethal) | 20 knock-outs | knock-out at 40% health instead of 35% | - |
| Mule | T1 | carrying a full load 2 hours | +15% carry weight | - |
| Brute | T3 | 100 kills | +6% damage, knock-back on any big blow | -3 to land (wild swings) |

### Defence (how it lives)

| Trait | Tier | Earned by | Effect | Cost |
|---|---|---|---|---|
| Thick-skinned | T1 | taking 3,000 damage and living | wounds bleed 5% less | - |
| Shieldwall | T1 (shield) | 200 blows on its shield | +5% block with an ally on each side | -5% block alone |
| Hold the line | T2 | holding a pass/door 3 fights | ignores one extra foe for the surround bonus while it stands still | can't charge (no first-blow bonus) |
| Spartan | T3 | Hold the line + 50 foes felled while holding | +3 Defence while it hasn't moved for 10 s | -3 while walking |
| Iron limbs | T1 | 10 crushed limbs mended | armour save +1 | - |
| Hard to kill | T2 | 5 falls survived (saved while dying) | dying window 75 s instead of 60 s | - |
| Unshakeable | T1 | 20 fights won while Shaken | morale losses x0.75 (below Defence 50; at 50+ morale is gone anyway) | morale gains x0.75 |
| Parry master | T2 (sword) | 300 parries | parry chance +2 points | riposte comes round 20% slower |

### Ranged (bows, throws)

| Trait | Tier | Earned by | Effect | Cost |
|---|---|---|---|---|
| Steady aim | T1 | 200 arrows landed | +3 to hit standing still | -3 the shot after a step |
| Eagle eye | T2 | 50 shots at 6+ tiles | +1 tile reach | - |
| Point blank | T1 | 30 shots with a foe beside it | no aim loss with a foe beside it | - |
| High ground archer | T2 | 50 shots from a block up | +5 to hit from higher ground | - |
| Thrower's arm | T1 (throwing) | 50 throws landed | +1 tile throw reach | - |
| Quiver discipline | T1 | 1,000 arrows shot | picks up 25% of its spent arrows after a fight | - |

### Magic

| Trait | Tier | Earned by | Effect | Cost |
|---|---|---|---|---|
| Deep well | T1 | 500 mana spent | +10% mana | - |
| Battle caster | T2 | 50 casts with a foe within 3 | casting isn't broken by a blow | -5% mana |
| Channeler | T3 | 200 casts | spells cost 10% less | its blows (melee) x0.9 |

### Weapon skills (one small tree each; examples)

| Weapon | T1 | T2 | T3 |
|---|---|---|---|
| Sword | Quick guard (parry +1) | Parry master | Blade dancer (a parry gives +3 to land on the next blow) |
| Axe | Woodsman's swing (also chops 10% faster) | Cleaving arc | Berserker's axe (+5% damage per foe beside it, to +15%) |
| Mace | Dent (crush on armour +10%) | Bone breaker | Bell ringer (stagger lasts 0.5 s longer) |
| Spear | Long reach (reach blow 10% sooner) | Brace (first foe to step beside it is struck first) | Phalanx (+3 to land with a spear ally beside it) |
| Dagger | Quick hands (double stab +5%) | Bleeder (dagger wounds bleed 10% more) | Shadow (first blow on a foe that hasn't seen it +5 to land) |
| Fists | Brawler (+5% fist damage) | Knockout artist | Iron fists (fists count as blunt weapons on armour) |
| Bow | Steady aim | Eagle eye | Volley captain (allies within 3 +2 to hit on its target) |

### Body and mind (from living, any skill's milestone)

| Trait | Earned by | Effect | Cost |
|---|---|---|---|
| Iron stomach | eating 50 raw or spoiled meals | no sickness from bad food | - |
| Night owl | 30 nights worked | works at night at full pace | -5% by day |
| Early riser | 30 nights in a bed | wakes 10% sooner | - |
| Rough sleeper | 30 nights on the ground | rough sleep heals +8 instead of +5 | beds heal it 10% less |
| Marathon walker | walking 10,000 tiles | +5% walk speed on roads | - |
| Mountaineer | 500 blocks climbed | climbs and hops 15% quicker | - |
| Cold-blooded | 20 nights cold | cold hurts it half as fast | heat hurts it 25% faster |
| Survivor | living through 3 raids | +10 morale at a fight's start (below Defence 50) | - |
| Leader's voice | 20 fights with 5+ allies near | allies within 4: +1 morale a fight's start | - |
| Grudge | a friend killed beside it | +3 to land on that foe's kind for a day | -3 to everyone else |

### Work skills (the same system; a few each)

| Skill | Examples |
|---|---|
| Mining | Vein sense (sees ore 1 block deeper), Steady pick (10% quicker on stone), Deep lungs (ignores mine gas 50% longer) |
| Woodcutting | Clean cut (+1 log in 5), Feller (trees fall 10% sooner), Forester (zone saplings grow 10% faster near it) |
| Fishing | Patient (bites 10% sooner), River reader (finds the best spot in a zone first) |
| Cooking | Hearty (meals +5 health), Frugal (1 in 5 meals uses no salt/spice), Burnt-proof (never burns) |
| Smithing / crafting | Fine hand (Quality one rank higher 1 in 10), Thrifty (1 in 6 uses no ore), Fast hands (10% quicker) |
| Doctor | Steady hands (stump treatment never fails), Field medic (treats from 2 tiles), Bonesetter (crushed limbs mend 25% faster) |
| Farming / hauling | Green thumb, Strong back (+1 item per trip), Sure-footed (never drops a load) |

## 3. Negative traits (earned by what happens to it)

| Trait | Comes from | Effect | Goes away |
|---|---|---|---|
| Scarred | a wound that bled out to under half blood and was saved | -2% max health | becomes **Battle-scarred** (+2 morale at a fight's start) after 3 more healed wounds |
| One-handed | an arm lost | no shields or two-handed weapons; -10% work speed | Restoration potion or a grafted arm |
| Limp | a leg lost or crushed 3 times | -15% walk speed, dodge halved | a grafted leg; never otherwise |
| Shaky hands | being downed 3 times in a week | -3 to land for a day after each fight | land 100 blows |
| Fearful | Broken 5 times | morale losses x1.25 | win 10 fights while Shaken |
| Glass jaw | knocked out 5 times | knocked out at 45% health instead of 35% | a month without a knock-out |
| Bad back | carrying overweight 2 hours | -10% carry weight | a week of rest (beds) |
| Gaunt | starving to under 10 hunger 3 times | -5% max health, eats 20% more | 10 days well fed |
| Insomniac | 10 nights woken by fights or cold | sleeps 20% longer for the same rest | 10 nights in a bed with a roof |
| Haunted | seeing 10 friends die beside it | -5 morale at a fight's start | 3 fights won |
| Captive's mark | a month as a captive | -10% loyalty gain toward a new house; +5 to break free | won over to 100% loyalty |
| Coward | routing 3 times (NPCs only: player units never flee by themselves) | routs at Shaken instead of Broken | never |
| Clumsy | 20 failed crafts in a row | 5% more failed crafts | 50 good crafts |
| Drunkard | the tavern 20 nights running | -2 to land after drinking | 10 dry nights |
| Old wound | a severed limb regrown | -5% max health of that limb | never |
| Bitter | a lost duel to the same foe 3 times | -3 to land on that foe | beat it once |

## 4. Stat gains (the quiet part)

Besides traits, every milestone gives a small, permanent gain picked by its deeds, the way RuneScape levels feel:
+1 Strength / Agility / Defence base stat at 10, 30, 50, 70 and 99 of a combat skill, toward what it used most
(a swordsman that dodged a lot gets Agility, one that took hits gets Defence). Work skills give +1 of their own
stat (mining: Strength; crafting: Intelligence). Max +5 a stat from milestones in all.

## 5. Balance guard rails

- Positive traits work at 6 at most; the oldest of the same tree drops when a 7th comes.
- No trait adds more than +5 to land, +6% damage or +3 Defence.
- Every T3 has a cost. Negative traits stack; they are the price of a long life.
- Tests before landing (the battle tool from tonight, `reports/polish-night-1026/combat-rules/tests/cr_fair.dm`):
  level-50 with 6 combat traits vs level-50 without (want 60-70% wins, not 90%); 10 traited veterans vs 100 recruits
  in the open (still a loss) and in a pass; one-on-one duel table unchanged at level 1.

## 6. Build steps (after the freeze)

1. Deeds counters on the unit (cheap: numbers in one list, saved with it).
2. The trait table as data (one file, like GearData.dm), with the tree links.
3. Milestone hook in the skill level-up (one place: Skills.dm / CombatSkills.dm), negative-trait hooks at the events
   (limb loss, fall saved, KO, starving, capture, rout).
4. Effects read through the existing rolls (land roll, damage, sever, armour save, bleed, morale), one line each.
5. Traits tab on the unit card; Log lines.
6. Battle and duel tables to the owner; land.

## 7. Questions for the owner

- 6 positive traits at once, or all of them?
- Should a few traits be very rare (1 in 100 units, "legendary": e.g. **Born leader**, **Unbreakable**)?
- Inherited traits through families (a child may get one of a parent's)?
- Do NPCs get traits too (a bandit chief that is a known "Executioner")? It would make named NPCs feel real.
