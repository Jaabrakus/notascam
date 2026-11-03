# Vampire and werewolf plan: secrecy, fear, blood and frenzy (2026-10-27)

The owner asked: "plan the vampire and werewolf features". This is a plan only. Nothing in `game/`, `engine/` or `art/`
has changed, and nothing was built or run. The designs come from the Crimson Grid survey
(`reports/crimson-grid-survey/REPORT.md` section 5, "Powers as data", "Sacred sites and renown"). Only the ideas are
taken; everything is rebuilt on our own procs. Every number here is a proposal for the owner to set.

Sizes: **S** is about a day with its proof, **M** is 2-4 days, **L** is a week or more. Every proof is an arena test at
speed 32.

## The short answer

Our vampires and werewolves are still the 2006 creatures. They bite, infect, burn in the sun and change at night, and
dice decide almost all of it. The plan turns them into a strategy layer built on systems we already have:

- **Blood is the hunger, for both kinds.** This follows the owner's rule: "they need blood to stay at 300 or they die".
  We use the existing `BloodContent`, whose full value is 300 for every vampire and every race that can become a
  werewolf, and add no new resource. Blood drains on the hunger clock and comes back only by feeding. At 0 the unit gets
  the 60 s dying state, and only blood saves it.
- **Secrecy uses real witnesses.** A breach is an act seen by a unit with real sight: the fog radius, with walls
  blocking. Each witness remembers what it saw and tells its own realm when it next sleeps at home. Until then the
  breacher can silence, win over or kill it. Told breaches lower the realm's standing, and a ruler can issue a hunt
  order.
- **Fear.** Seeing a werewolf in war form costs morale through `RmMoraleAdd`, more the closer it is. Vets are already
  immune.
- **Frenzy.** Fixed blood lines, no rolls. A hungry vampire is drawn to bleeding stumps and blood pools. A starving one
  frenzies. Fire holds vampires back.
- **Powers become data rows**, so a new power is a row, not code. Werewolves get dens that keep strangers out, and three
  renown tracks that become pack titles.
- **It scales because checks are event-driven.** Witness checks run only when an act happens, read the engine unit
  grid, and never run in asleep land. Nothing calls `view()` per unit.

## Owner's answers (2026-10-27 ~21:25)

Verbatim: "yea one meter, but we dont have to call it blood it can just be hunger then , but can only be refilled from
drink and also turning a unit , they can keep it or allow the unit to still be used by the owner but the can take
control anytime".

- **One meter, called Hunger** (question 1): the card's existing hunger meter, for vampires and werewolves alike. It is
  not shown or named as "blood". Full is 300 (the owner's earlier rule: "they need blood to stay at 300 or they die").
- **Refilled only by drinking and by turning a unit.** Meals, raw meat and devouring a body don't refill it (this
  replaces the werewolf refills in 2.1 and question 2).
- **Turning a unit refills it, and the turner chooses:**
  - keep the turned unit (it joins the turner's house); or
  - leave it working for its own owner, as before, while the turner can take control of it at any time.
  This makes a turned unit a possible sleeper inside another realm, which ties into secrecy (2.2).
- Still open: whether turning needs a roped captive (2.5's Embrace and Curse rows; a sleeper left with its owner
  suggests not), whether a blood flask counts as drinking, and what the meter does at 0 (recommended: the 60 s dying
  state, saved only by drinking). The other questions keep their recommended answers only once the owner says so.

### Second round (2026-10-27 ~21:35)

Verbatim: "okay most reccommend are yes but vampires frenzy happen after the 60 death state, but vampire get 60 seoncds to
still move and drink. after 60 seconds they turn into a frenzy vampire a npc monster that wanders and or get the burn
death animations, yes lizardmen to".

- **Everything else takes the recommended answer** (the 20 questions as put to the owner): no rope to turn (the victim
  is drunk to empty and turns 60 s later); turning gives +150 Hunger; a blood flask counts as drinking (+40); drink +100,
  victim -100 and Non-lethal stops at 150; victims recover +25 a meal and +5 every 10 s in bed; away floor 200; sleepers
  hidden from their owner, seized from anywhere at once; sun at 0 HP is the 60 s window; fire as a hard rule; witnesses,
  true-form breach, standing, hunt order, fear numbers, den stone, renown and one global sun as recommended.
- **Vampire at Hunger 0, changed:** not a helpless dying state. It gets **60 s in which it can still move and drink**.
  If it hasn't drunk by then, it is lost: it **turns into a frenzy vampire, a wild NPC monster that wanders** (no longer
  the player's), or, in the sun, plays the **burn death**. There is no frenzy line at 50 any more; frenzy is this end
  state. The starving pull toward blood (under 125) stays.
- **Limb regrowth only asleep, paid from Hunger** (50 a limb, one per 2 min), and **Lizardmen move to the same
  asleep-only rule** (their cost from their own hunger).
- **Werewolves at Hunger 0** (owner ~21:40): like vampires: 60 s to move and drink, then a wild wolf NPC.
- **Vampire at the end of its 60 s (owner ~21:55, correcting the lead):** the lead misread "no they just burn they have the burn death animation" as dropping the wild vampire; the owner: "when did i say no wild frenzy vampire?". So: after its 60 s at Hunger 0 a vampire becomes a wild frenzy vampire NPC that wanders; in the sun it burns with the burn death animation. Werewolves: a wild wolf.
- **No automatic drinking (owner ~21:45):** "Never automatically: no auto-drink; just warnings, and I send them to drink myself" (after rejecting the Hungry line at 200: "thats like no time"). Warnings at 100, 50 and 0; the player orders every drink. Away: no drain, and no automatic refill or floor in the catch-up; they come back as they left.
- **GO (owner ~21:40):** "start building the vampire/werewolf plan with V0 (registry) and V1 (the Hunger meter, with the away part)".

## 1. What exists today

**Where they come from.** Neither kind is a starting people (`Restart.dm:41-49`).
- Vampires come from Unholy Blood, 1 in 4 (`HalfDemons.dm:22, 125-126`). They also come from a feed, 15%
  (`Vampires.dm:15`), or 1% on an autofeed. Some are NPC monsters (`Mobs.dm:1459-1478`, `Undead=1`).
- Werewolves come from the war-form bite (`Interact.dm:711-760`) and the Ring of Lycanthropy (`Turfs.dm:5777-5790`).
- So they live inside ordinary realms. That is what makes secrecy matter.

**The vampire today.**
- **Bite and feed.** A bite rolls `prob(Agility - Agility + 50)` (`Vampires.dm:6`), with a 30 s cooldown (`:3`).
  - It takes only `Level/5` of the victim's blood (`:11`) and sets the vampire's Hunger to 100 (`:13`).
  - A full plate helm shatters its teeth (`:17-22`).
  - Every landed melee blow also tries a bite (`Combats.dm:286`).
- **Infection.** The victim turns about 60 s later (`Vampires.dm:24-52`) and changes owner. That gets round the owner's
  rope rule.
- **Level gates.** Morph comes at Level 10, a disguise that wears the old race's look (`Vampires.dm:74-83`). Mist comes
  at 15 (`Interact.dm:489-494`).
  - Mist has no density, halves tiredness, uses no gear and can't rest (`Vampires.dm:84-108`,
    `Interact.dm:686-689`).
- **Fly** needs all four limbs and can't carry anything (`Race.dm:54-66`).
- **Growth.** Evolution gives +8 Strength and +8 Agility, then wings, then Daywalker at Level 40 (`Vampires.dm:53-73`).
- **Other traits.**
  - Sees at night (`Fog.dm:19`).
  - Immune to temperature and climbs cliffs (`Race.dm:13-22`).
  - Can't eat, use the tavern, breed or carry silver (`Food.dm:39`, `Tavern.dm:87`, `Capture.dm:19`, `Orders.dm:745`).
- **Bleeding.** It never bleeds (`Stumps.dm:131-141`), but blows still take its blood (`Chains/Strike.dm:143-144`).
- **Stake and water.** Stab Heart and water Spray only work on the NPC monster type (`Click.dm:965-989`,
  `Turfs.dm:1403-1411`).

**The sun.**
- `SunLight` takes 35 HP every 5 s on open ground by day (`Turfs.dm:17-43`).
- Open ground is grass, water, peaks, marsh, tropical land, desert, snow and the Sky level (`Turfs.dm:134-160`).
- It is checked on the ground timer about 1 s after a step (`Turfs.dm:81-94, 165-215`), and for everyone at dawn
  (`World.dm:67-69`).
- Rock, cave floor, built floors, bridges and Daywalker are safe.
- Death is at once ("The Sun", `Turfs.dm:32-37`). It is not spared, because `RmFallSpares` needs a mob as the killer
  (`Falls.dm:27-31`).
- Day and night are one switch for the whole world, every 5500 ticks, with a 50 s dawn and dusk
  (`World.dm:28, 53-90`). A full day is about 18 minutes.

**The werewolf today.**
- **War form** is forced at dusk and undone at dawn (`World.dm:86-87`, `Werewolves.dm:47-73`).
  - It gives +20 Strength, +20 Agility, +50 Defence plus 1.4 a level, and claws (15-20 damage plus 0.25 a level). Gear
    goes off.
  - It takes 5 less damage, 15 less in war form (`Combats.dm:380-382`). Silver does +12, plus 0.7 a level in war form
    (`:402-404`).
- **Bite** is only in war form (`Interact.dm:700`, `Abilities.dm:79`).
  - It rolls `prob(Strength - Strength)` (`Interact.dm:713-714`).
  - Infection is three rolls: 50%, then 65%, then 90% that the turned unit becomes the biter's slave (`:726-746`).
  - A race that can't take the curse loses 250 blood (`:756`).
- **The war-form Defence is not "vet" Defence.** `RmMoraleVet` reads the Defence *skill* (`Morale.dm:110-112`,
  `CombatSkills.dm:38-41`), so war form never makes a wolf a vet.

**Both kinds regrow lost limbs.** It is `prob(20)` a limb each minute, awake or asleep (`Health.dm:151-200`,
`Mob Procs.dm:17, 21`). This goes against "no automatic healing".

**The 300 rule (the owner's) against today's code.** No 2006 rule kills either kind below 300. The rule is new.
- **What 300 is today.**
  - It is the full `MaxBloodContent` of vampires (`Mobs.dm:1477-1478`) and of every race that can become a werewolf
    (Human `Mobs.dm:345`, and so on).
  - It is also the "Very Mildly" bleeding line (`Combats.dm:82`).
- **A vampire's real hunger today is the `Hunger` value**, not blood.
  - It drops 1 every 40 s, only while the owner is connected and the unit isn't in a hole (`Mob Procs.dm:42-69, 55`).
  - At 20 or less it bites any creature beside it (`Mob Procs.dm:70, 82-83`).
  - A blood flask gives +20 Hunger (`Turfs.dm:1434-1440`). The flask is filled from blood pools on the floor
    (`Turfs.dm:1371-1374`).
  - At 10 or less it loses HP each beat, and dies of "Starvation" at once (`Mob Procs.dm:72-79`). Falls.dm leaves
    starvation out of the dying state (`Falls.dm:6`).
- **A vampire's blood** falls from blows and never refills, except:
  - a full heal;
  - being saved from bleeding out (`BleedOut.dm:67`);
  - adrenaline (`Morale.dm:192-195`).

  At 0 nothing happens, except at the end of a fight, which puts it into a bleed-out that a bandage saves
  (`Morale.dm:216-220`).
- **A werewolf's blood** returns to 300 by itself when bleeding stops: 1 chance in 5 every 5 s (`Health.dm:67-69`). A
  stump holds it back; blood then returns at 3 every 5 s (`Stumps.dm:29, 197-205, 235-238`).

**What the rest of the design reads.**
- **Morale** exists only in combat (`Morale.dm:3-5`). Vets return early from `RmMoraleAdd` (`Morale.dm:114-120`).
  Broken NPCs rout (`:155`), and the underdog table keeps it a tug of war (`Underdog.dm`).
- **Fog** is circles with no line of sight: 12 tiles, ±3 for night, height and flying (`Fog.dm:38-46, 300-345`).
- **Facing** is off (`Facing.dm:13`).
- **The engine grid** is behind `RmUnitsNear` but switched off (`rm_grid = 0`, `Native.dm:243, 269-282`).
- **Far records** keep vampires as full units (`FarRecords.dm:71`) and are off (`:62`). "Nobody starves while away"
  (`Away.dm:16`).
- **Laws and war.** The 5 laws are laws of succession (`Rulership.dm:46-51`). Realms are at peace by default
  (`War.dm:1-12`).
- **Claims, captives and NPCs.**
  - Claims give land a border (`Claims.dm:1-7`).
  - Captives need rope and are won over or enslaved (`Captives.dm:1-25`).
  - NPC Alliance units attack Undead, Morphed and war-form units (`Monster AI.dm:253`).

## 2. The design

### 2.1 Blood is the hunger, for vampires and werewolves
- The 40 s hunger beat drains `BloodContent` for both kinds. Their `Hunger` is held full, and the card's fullness bar
  shows blood out of 300.
  - Vampire: −2 a beat. From 300 to 200 takes 33 minutes; to 0, 100 minutes.
  - Werewolf: −1 a beat, −3 in war form.
  - Powers cost what their rows say.
  - Drain runs only while the owner is connected, as Hunger does today.
- **Lines, all fixed with no rolls:**
  - Sated 200 and up.
  - **Hungry** under 200: feeds by itself on a willing unit beside it, and the care step walks it to a donor, captive or
    blood flask within 20 tiles.
  - **Starving** under 125: drawn to fresh blood (2.4).
  - **Frenzy** under 50.
  - **0**: the 60 s dying state (`RmBleedOut`'s window). Only blood saves it, from a flask or a donor brought beside it.
- **Refills.**
  - A vampire feed gives +100. A blood flask gives +40.
  - A werewolf bite gives +60, devouring a fresh body +100, raw meat +30.
  - A feed counts as a meal (+20 HP, `Healing.dm` `RM_HEAL_MEAL`).
- **Werewolves.** Their bleeding no longer puts blood back by itself (`Health.dm:67-69` is skipped for them). Lost blood
  comes back only by feeding.
- **The victim.**
  - Feeding takes from the victim what it gives.
  - With Non-lethal (the striker's toggle) it stops at the victim's 150. With Lethal it can drain to 0, and the victim
    then falls dying for 60 s, never killed outright.
  - A victim gets blood back only from meals (+25) and sleep (+5 every 10 s in a bed, +2 sleeping rough). So a captive
    costs food and beds, and is not a free well.
- **Vampires still never bleed.** Blows take their blood (the built rule), so fighting makes them hungry.

### 2.2 Secrecy (masquerade)
- **Breaches.** Every power row has a `breach` flag. Beyond the rows, these count:
  - feeding of any kind;
  - the true form being seen (a vampire not Morphed, a werewolf in war form);
  - a vampire burning in the sun;
  - a frenzy.
- **Witnesses.**
  - A witness is a `/mob/Monsters` unit that:
    - is not cursed or undead;
    - is not an animal;
    - is awake and not out cold;
    - can see (`CanSee`);
    - belongs to another realm and is not an ally, or to an NPC settlement.
  - It must stand within its own `RmFogRadius` of the act (12; −3 at night without dark sight; +3 on the Sky level; +3
    flying). The Sky can see down onto the ground, as the fog does.
  - Walls block: a line walk over opaque turfs, run only for units already inside the circle.
  - There is no facing cone (facing is off).
- **Memory.**
  - Each witness keeps up to 4 sightings, saved on the unit by uid (never a mob ref, per `Lineage.dm:2-4`).
  - A sighting holds the breacher, the act, the time and the place. The same breacher is stored once per witness.
- **Telling.**
  - A witness tells when it next sleeps inside its own realm's claim. An NPC tells when it is back at its home spot (a
    rout home counts).
  - Its realm then **knows** the breacher:
    - that realm's view draws it in true form (the disguise fails for them);
    - its card shows what it is;
    - a log line names it.
- **Before it tells, a breach clears if:**
  - the witness dies;
  - it is won over and joins the breacher's realm (Captives.dm);
  - it is roped or a slave (it can't tell while bound);
  - Cloud Memory is used on it;
  - 2 game days pass (about 36 minutes) with it still untold.

  So the play is positional: hunt down the scout before it gets home to bed.
- **What the breacher's owner sees:**
  - a red eye over each witness its side can see;
  - a "Seen by" list on the vampire's card, marking each as untold or told;
  - "Galas saw Orin feed. He will tell when he sleeps at home."

### 2.3 Standing and the hunt order
- **Realm standing** runs from 0 to 100 and starts at 100. It shows on the Realm page.
  - −10 for each told breacher, once per breacher per realm per game day.
  - +5 for each game day with none.
  - Below 60: NPC Alliance hunters with silver join that realm's seasonal raids (Raids.dm).
  - Below 30: every realm knows all of its cursed units.
- **The hunt order** is a ruler's decree on a unit their realm knows.
  - Their units on guard, defence and attack-move treat that one unit as a foe on sight, even at peace, and striking it
    does not start a war.
  - The ruler sets a bounty in coins from the treasury. It is paid to the realm whose unit downs or kills the hunted.
  - At most 3 hunts at once. Each lasts 3 game days, or until the unit dies or is pardoned.
  - At the Kingdom stage the High King's hunt binds members and vassals.

### 2.4 Fear, hunger pull, frenzy and fire
- **Fear (delirium).** The source is the werewolf, not every unit looking round.
  - Once a second, each war-form wolf in awake land asks `RmUnitsNear(6)`, after the engine's `rm_foe_near` pre-check.
  - Each unit that would count as a witness and has line of sight to the wolf takes group morale per second, by
    distance: −4 at 2 tiles or less, −2 at 3-4, −1 at 5-6.
  - The total is capped at −6 a second, plus −10 once per fight at first sight.
  - A unit not yet fighting starts morale as at a first blow. The wolf counts as "engaged" while it is in sight.
  - Vets, the cursed and the undead are immune.
  - The underdog table and shake-off stay, so it doesn't snowball. Broken NPCs rout. Players' units never flee.
- **Pull.** A Starving vampire, or a werewolf in war form, leaves job and board work for the nearest open stump, bleeding
  unit, dying unit or blood pool within 8 tiles, and feeds there.
  - It feeds Non-lethal unless its toggle is on Lethal.
  - A direct order holds it back for 30 s at a time.
- **Frenzy** under 50.
  - It ignores orders and strikes the nearest living unit that isn't cursed, within 8 tiles: bleeding ones first, of any
    realm, its own included.
  - It feeds Lethal until it is back to 150, then comes to.
  - A roped vampire can't move to frenzy.
  - The log warns at each line: "Orin is starving: about 25 minutes to frenzy".
- **Fire.**
  - A vampire won't step onto or beside a burning tile, and can't feed with fire within 1 tile (a torch-bearer guards a
    sleeper).
  - NPC vampires keep 2 tiles from fire.
  - In a fight, fire within 2 tiles costs −3 personal morale a second (vets immune).

### 2.5 Powers as data
- A table, `rm_powers`, with these fields:
  - id, who (vampire or werewolf) and what unlocks it (level, wings, renown rank);
  - blood cost and drain per beat;
  - cooldown, range and target kind;
  - breach, usable in frenzy, and day or night only;
  - the proc it calls.
- The skill bar (`Abilities.dm:53-80`) reads the rows for cursed units instead of scanning the Interact menu.
- Today's procs (`VampireMistForm`, `VampireMorph`, `Fly`, `WerewolfTransformation`) are wrapped, not rewritten.

| Power | Unlock | Blood | Cooldown | Target | Breach | Replaces or wraps |
|---|---|---|---|---|---|---|
| Feed | any vampire | +100 (victim −100) | 30 s | beside: held, asleep, out cold, roped, willing (own or ally), animal (+50) | yes | the `prob` in `Vampires.dm:6` |
| Battle bite | any vampire | +25 | shares Feed's | a landed bare-hand blow | yes | `Combats.dm:286` |
| Morph | Level 10 | −10 | 10 s | self | if the change is seen | `Vampires.dm:74` |
| Mist | Level 15 | −20, then −2 a beat | 30 s | self | yes | `Vampires.dm:84` |
| Fly | wings | −10, then −2 a beat | 30 s | self | yes | `Race.dm:54` |
| Cloud Memory (new) | Level 20 | −40 | 60 s | a witness beside, not fighting, 5 s still | no | new |
| Embrace (new) | Level 25 | −150 | 1 game day | a roped captive at 0 blood; it turns 60 s later and joins the house | yes | the 15% bite (`Vampires.dm:15`) |
| Blood Mend (new) | vampire or werewolf | −50 a limb | one limb per 2 min asleep | self | no | `prob(20)` regrowth (`Health.dm:151`) |
| War form | werewolf | −2 a beat | forced at dusk | self | yes, while seen | `Werewolves.dm:47` |
| Hold the Change (new) | Packleader | −60 | once a night | self, at dusk | no | new |
| Bite | war form | +60 | 30 s | beside | yes | the `prob` in `Interact.dm:714` |
| Devour (new) | werewolf | +100 | 10 s | a body dead under 5 min | yes | the commented one in `Death.dm:254` |
| Curse (new) | Hunter | −100 | 1 game day | a roped captive of a race that can take it (`Interact.dm:739`). It turns at the next dusk and joins the house; other races lose 250 blood and fall dying | yes | the 50/65/90% rolls (`Interact.dm:726-746`) |

### 2.6 Dens and renown
- **The Den stone.**
  - Built like a Claim banner (3 stone, 1 bone), inside one's own claim, one per Packleader.
  - At night its ring of 8 tiles:
    - turns NPC creatures and raiders away (they path round it);
    - gives player strangers inside it fear, as from a wolf at 5-6 tiles, and alarms the den's members once a minute.
  - The stone has 300 health. Striking it alerts every member.
  - By day the ring is down: that is when to assault it.
- **Renown**, three tracks saved on each werewolf:
  - **Glory:** +1 for each foe it brings down in war form, +3 for each hunted unit it brings down.
  - **Honour:** +1 for each night it ends with no told sighting of it, −3 for each told sighting.
  - **Wisdom:** +1 for each night spent in its den, +1 for each captive or witness it wins over.
- **Ranks**, shown as the pack title on the card:
  - Cub at 0;
  - Hunter at 10 in all;
  - Packleader at 30, with each track at least 5;
  - Elder at 80, with each at least 15.
- Ranks gate power rows and den founding. For a werewolf ruler, the stage-4 title needs Packleader and the stage-5 title
  needs Elder (`Rulership.dm:31-38`).

### 2.7 The MMO side
- **Cost at 30k units.**
  - Acts are events. Each runs one grid box query (31×31 tiles, at most 4 cells of 16×16), then the radius filter, then
    the line walk for those inside the circle.
  - A true-form sweep runs every 5 s for each showing cursed unit, only in awake land (`RmAwake`): no player unit within
    32 tiles means no player witness, and asleep NPCs don't witness.
  - Each breacher is limited to one sweep every 2 s, and sweeps run under a tick ledger budget (Spread.dm) that spills
    over to the next tick.
  - Estimate: 500 cursed units awake comes to about 5 ms a second with the grid. With `rm_grid = 0`, `range(15)` would
    cost 30-100 ms a second, so sweeps need the grid and stay off without it. Single acts may fall back to `range`.
- **Dawn and dusk.** Today both loop over every creature in the world (`World.dm:67, 86`). A registry of the sun-shy and
  the cursed (`rm_cursed`) replaces that.
- **Away and records.**
  - No drain while away.
  - The catch-up floors blood at the Hungry line (200) and feeds from the realm's flasks and willing units, as
    `RmFarMeal` feeds others. There is no frenzy offline.
  - Records can then keep vampires: Vampire comes off `rm_far_kept_races`.
  - A werewolf record takes the current night's form when it wakes.
  - Witness memory is a saved unit value, so records keep it. Telling happens in the live-through's sleep. Records never
    witness and never breach.
- **The sun.** One global sun stays ("light comes from the sun and sky"). The Sky level burns by day, so a flying vampire
  is out of the question by day unless it is a Daywalker.

## 3. The pieces

### V0 Registry and counters (S, exact)
- **Players see:** nothing.
- **What it does:**
  - `rm_cursed`: vampires, werewolves and Svartalfar, kept up to date at race change, death and load. The dawn and dusk
    loops walk it.
  - Counters for bites, infections, burns, changes and, later, sightings.
- **Depends on:** nothing.
- **Proof:** the dawn tick cost on a 30k test map, before and after; `vampire_defense_test`, `werewolf_defense_test`.

### V1 Blood is the hunger (M, rule change)
- **Players see:** a blood bar out of 300 on cursed cards; the hunger lines; the 60 s dying state at 0, saved by a flask
  or a donor.
- **What it does:**
  - drain on the hunger beat;
  - feeding refills, and counts as a meal;
  - werewolves no longer get blood back by themselves;
  - victims get blood back only from meals and sleep;
  - the care step walks hungry units to food;
  - old saves start at `max(150, 3 × Hunger)`.
- **Away part:** this lands together with V10's away part.
- **Depends on:** V0.
- **Proof** (`tests/vw_blood_check.dm`):
  - the drain rate over 30 game minutes;
  - each line triggers at its value;
  - a 0 is saved by a flask and dies without one;
  - one captive fed on keeps a vampire only while it is fed itself;
  - offline: no drain.

### V2 Feeding and turning without dice (M, rule change)
- **Players see:**
  - Feed always works on a held or willing target, and Battle bite rides on a landed blow.
  - The Lethal toggle decides whether the victim is drained.
  - Turning needs a roped captive (Embrace, Curse).
- **What it removes:** `Vampires.dm:6, 15`, `Interact.dm:713-714, 726-746`.
- **Depends on:** V1, and the V8 rows if V8 lands first (it can go either way).
- **Proof:**
  - 50 feeds give identical results;
  - full plate still blocks the bite;
  - a turned captive joins the house;
  - no unit changes owner without rope.

### V3 Sun and the dying window (S, rule change)
- **Players see:** a vampire at 0 HP in the sun burns down for 60 s. Dragged into shade and given blood, it lives;
  otherwise it is ash.
- **Depends on:** V1.
- **Proof:**
  - burn rate on each kind of open ground and on the Sky;
  - shade saves it, and staying in the sun does not;
  - Daywalker is unaffected.

### V4 Secrecy: witnesses, memory, telling (L, rule change)
- **Players see:** 2.2 in full: red eyes over witnesses, the "Seen by" list, log lines, known units drawn in true form.
- **Depends on:** V0, V8 (the breach flags), and the engine grid switched on for sweeps.
- **Proof:**
  - a wall blocks a witness;
  - night shortens sight;
  - the same breacher is stored once;
  - each way of clearing a breach works;
  - telling happens at the first sleep at home;
  - a 30k map with 500 cursed units stays under its ms budget.

### V5 Standing and the hunt order (M, rule change)
- **Players see:** standing on the Realm page; a Hunt button on known units; the bounty paid.
- **Depends on:** V4; War.dm (peace); Raids.dm.
- **Proof:**
  - a hunted unit is attacked at peace with no war starting;
  - each standing line triggers;
  - a High King's hunt binds vassals.

### V6 Fear (M, rule change)
- **Players see:** "Dread" over Shaken units near a wolf; NPCs routing.
- **Depends on:** Morale.dm and Underdog.dm only. It can land early.
- **Proof:**
  - morale loss by distance;
  - no loss behind a wall;
  - vets stay Steady;
  - 60 fights in `cr_fair.dm` with wolves on one side still have both sides winning.

### V7 Pull, frenzy and fire (M, rule change)
- **Players see:** starving vampires drawn to stumps; frenzy, with its warnings; vampires that won't cross fire.
- **Depends on:** V1, and Stumps.dm (bleeding stumps and blood pools).
- **Proof:**
  - the pull triggers at 125 and frenzy at 50;
  - frenzy ends at 150;
  - a roped vampire can't frenzy;
  - a torch-bearer stops a feed.

### V8 Powers as data (M; wrapping is exact, new rows are rule changes)
- **Players see:** the same buttons, plus each new row as it lands.
- **Depends on:** Abilities.dm.
- **Proof:** the bar for today's powers matches the old scan exactly (`abilities_test.dm`); then each row's cost,
  cooldown and breach flag.

### V9 Dens and renown (M, rule change)
- **Players see:** the Den stone and its ring at night; pack titles on the card.
- **Depends on:** Claims.dm; V6 (fear); V4 (Honour needs told sightings).
- **Proof:**
  - NPCs path round the ring;
  - a stranger triggers the alarm;
  - striking the stone alerts the members;
  - renown ranks are reached at their thresholds.

### V10 Away and records (M, rule change)
- **Players see:** after time away, vampires come back hungry, never dying.
- **What it does:** the catch-up's blood floor and flask feeding; Vampire off `rm_far_kept_races`; the werewolf record's
  night form on waking.
- **Depends on:** V1. The records part also waits on `rm_far_on`.
- **Proof:** 8 hours away with no flasks leaves blood at 200; `far_records_test.dm` round trip with a vampire and a
  werewolf.

## 4. Ways it could break, and what stops each

| | How it breaks | What stops it |
|---|---|---|
| 1 | Witness checks spike in a big fight or at 30k | Event-driven checks, a 2 s limit per breacher, sweeps only in awake land and only with the grid, a ledger budget, V0 counters |
| 2 | A crowd watching one vampire floods the log and standing | One stored sighting per witness per breacher, at most 4 per witness, one standing hit per breacher per realm per day |
| 3 | One captive feeds a vampire forever | A victim gets blood back only from meals and sleep |
| 4 | A frenzy wipes out its own village | Frenzy only below 50 (over an hour online with no feed), warnings at each line, it ends at 150, roped vampires can't frenzy |
| 5 | Turning gets round the rope rule | Embrace and Curse work only on roped captives |
| 6 | Hunt orders used as war without war | Only on known units, at most 3 at once, 3 days, pardons |
| 7 | Fear snowballs into routs | Capped at −6 a second, the underdog table, shake-off, vets immune, players never flee |
| 8 | Units starve or frenzy while away | No drain offline, the catch-up floor at 200, no frenzy offline |
| 9 | A vampire at 0 blood is saved by a bandage (`Morale.dm:216-220` → bleed-out) | For the cursed, only blood saves the dying state |
| 10 | Saved refs duplicate units | Memory stores uids, never mob refs |
| 11 | A witness never sleeps at home and the breach hangs forever | It fades after 2 days; NPCs tell when they get home |

Found on the way (each an exact fix, the owner's call):
- The werewolf's dawn change zeroes weapon damage and puts back the evening's Defence, losing anything gained overnight
  (`Werewolves.dm:64-73`).
- NPC Alliance attacks *disguised* vampires but not undisguised turned ones (`Monster AI.dm:253`).
- Blessed weapons do 2 *less* to vampires (`Combats.dm:421`).
- Stake and Spray miss turned vampires (`Click.dm:965-989`, `Turfs.dm:1403-1411`).

## 5. Order

1. V0.
2. V1 together with V10's away part. "Away never starves" must hold from the first day.
3. V2, then V3.
4. V6. It stands alone and shows quickly.
5. V8, then V4 (once the engine grid is on), then V5.
6. V7, then V9.
7. V10's records part when `rm_far_on` returns.

## 6. Questions only the owner can answer

1. **What does "blood at 300 or they die" mean?**
   - *Recommended:* 300 is full. Blood drains and death comes at 0, with the lines Hungry 200, Starving 125, Frenzy 50.
   - Drain: vampire −2 a 40 s beat; werewolf −1, or −3 in war form.
   - The other reading: any time below 300, the unit loses HP.
2. **Werewolves: does blood replace their food hunger?**
   - *Recommended:* yes, one bar. Refills: bite +60, devour +100, raw meat +30. Their bleeding no longer refills them by
     itself.
3. **Blood at 0, and the sun: the 60 s dying state?** Today starving is left out of it (`Falls.dm:6`).
   - *Recommended:* yes for both. Only blood saves the first; shade plus blood saves the second.
4. **Away: is the floor 200?** *Recommended:* yes, with flasks and willing units fed from in the catch-up.
5. **Feeding numbers?** *Recommended:*
   - a feed +100; a flask +40;
   - the victim −100, stopping at 150 with Non-lethal;
   - the victim gets back +25 a meal and +5 every 10 s in bed.
6. **Turning only on roped captives (Embrace 150 blood at Level 25, Curse 100 blood at Hunter), joining the house, with
   the dice removed?** *Recommended:* yes.
7. **Who witnesses?**
   - *Recommended:* other realms that aren't allies, and NPC settlements; never one's own realm or allies, animals or
     the cursed.
   - Fog radius with walls blocking; telling at the first sleep at home; untold sightings fade after 2 game days.
8. **Is the true form itself a breach (a vampire not Morphed, a werewolf in war form)?**
   - *Recommended:* yes, once per witness. Morph at Level 10 is the disguise.
9. **Standing per realm or per house?** *Recommended:* per realm, 0-100. −10 per told breacher per day, +5 per clean
   day. Lines at 60 (NPC hunters) and 30 (all disguises fail).
10. **The hunt order: a decree, not a sixth law of succession?**
    - *Recommended:* a decree, only on known units.
    - Fair game at peace without war; a bounty in coins; 3 at once; 3 days; the High King's binds vassals.
11. **Fear numbers?** *Recommended:* −4, −2, −1 by distance (2 or less, 3-4, 5-6); a cap of −6 a second; −10 at first
    sight; line of sight needed; it starts morale in units not yet fighting.
12. **May a frenzy strike its own realm?** *Recommended:* yes. Starving has to cost something.
13. **Fire as a hard rule?** *Recommended:* yes: no stepping beside fire and no feeding beside it, plus −3 morale a
    second in a fight.
14. **Limb regrowth only asleep and paid in blood (50 a limb, one per 2 minutes)?** *Recommended:* yes. Should
    Lizardmen move to the same rule?
15. **Den ring: hard for NPCs, soft for players (fear and an alarm)?** *Recommended:* yes. Radius 8, 300 health, one per
    Packleader, inside one's own claim.
16. **Renown thresholds?** *Recommended:* Hunter 10, Packleader 30 (each track at least 5), Elder 80 (each at least 15).
    Werewolf rulers' stage-4 and stage-5 titles need Packleader and Elder.
17. **Keep one global sun (18-minute day)?** *Recommended:* yes.
