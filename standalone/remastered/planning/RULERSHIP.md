# Rulership: stages, titles, regalia, succession, the heir's item

Draft written 2026-10-23 (afternoon), from the user's ideas:

- crowning should differ by the settlement's stage;
- the player picks what their leader is called;
- becoming ruler should need ruler items made from gold and other materials;
- there should be different kinds of succession and of ruler items.

**Being built (2026-10-23, evening).** The user said "build it in game" and decided:

- **Titles:** a list per race and stage, chosen when crowned. No "type your own".
- **The heir holds an item too.** The chosen heir carries a heir's item (a prince's or princess's circlet), and it can
  be stolen. Succession honours who holds the items, so someone could kill a prince or princess, take the heir's item,
  take the succession and take over their realm (section 5).
- **The crown:** +150 health at Kingdom (`RM_CROWN_HEALTH`, `RemasterCrownHealth`, CombatSkills.dm). It gives no weapon
  skills or Attack: weapon skills never go above Attack (same file). The table by stage below is the default.
- Where the user hasn't answered an open question, the draft's proposal is built and the question stays open (the end).

The code is `game/Code/Remastered/Rulership.dm` (with small hooks in Crowning.dm, Succession.dm, Progress.dm,
Names.dm, SelectedActions.dm, Item Procs.dm, Gear.dm, Realms.dm, War.dm and Captives.dm). The check is
`tools/check_rulership.py` (`tests/rulership_test.dm`).

## What the game did before

- **Anyone, any stage.** "Declare Leader" made any unit King or Queen, even at a Camp of three people. One King and
  one Queen at most, with an hour's wait after losing one (`AddLeader`, `Items/Crowning.dm`).
- **Crowns were optional.** A Bone Crown (bone crafter, bones) and a Gold Crown (forge, gold ingot) exist. Wearing one
  only changed the message.
- **Titles were fixed and flipped.** A ruler was crowned King or Queen, renamed Lord or Lady when the settlement became
  a Town, then King or Queen again at Kingdom (`RemasterRankUp`, `Progress.dm`; it also wrote the title after the
  "{House}" tag, so the name read "{House} Lord Grak").
- **Stages** (`rm_ranks`, Progress.dm): Camp, Hamlet (5 people), Village (10), Town (20, a dining hall), Kingdom (35, a
  crowned ruler, a throne room, the Gold Age).
- **Succession** (`Succession.dm`, `planning/FAMILY_HOUSES.md` phase 4): one rule, bloodline. Eldest child, then eldest
  sibling, then eldest of the house; the player could name another heir. When the ruler died, a banner offered
  "Crown heir".

## 1. A ruler for every stage

Each stage has its own seat of rule, with its own title, item and bonus. The ruler keeps their person; the title and
bonus follow the stage, as far as the regalia they wear reaches.

| Stage | Default titles | Ruler item (regalia) | Made at, from | Health |
| --- | --- | --- | --- | --- |
| Camp | Chief | Chief's totem (or the old Bone Crown) | carpentry: 2 wood, 1 bones | +50 |
| Hamlet | Headman / Headwoman | Elder's staff | leatherworks: 2 wood, 1 skin | +75 |
| Village | Reeve | Chain of office | forge: 3 iron ingots | +100 |
| Town | Lord / Lady | Silver circlet | forge: 2 silver ingots, 1 cut emerald | +125 |
| Kingdom | King / Queen | Gold Crown (the old one) | forge: 3 gold ingots, 1 cut ruby | +150 |

- **The items** are crafted with "Craft new gear" at the workshop: pick the material, then **Regalia**. They are worn
  in the crown's place (with a helmet). A regalia item never fades where it's dropped.
- **Becoming ruler needs the item.** Declare Leader only crowns a unit holding the stage's regalia or a better one
  (worn or in the bag: crowning puts it on). Without one, the unit card and the notice say what to make.
- **Rising a stage** asks for the next item. Until it's worn, the ruler keeps the old title and bonus, and the Realm
  page says what's needed ("Your Town needs a Lord or Lady: make a Silver circlet"). Once it's worn, the ruler is asked
  for a title from the new stage's list (or keeps the old one).
- **The Kingdom stage** keeps its own needs (35 people, a throne room, the Gold Age). Its "a crowned ruler" becomes "a
  ruler wearing the Gold Crown". A realm that is already a Kingdom stays one.
- **Losing the regalia:** if it's taken off, stolen or lost, the ruler keeps the seat but loses the bonus until one is
  back on (open question 2).
- Health never drops below 1 when the bonus comes off.

## 2. Choosing the title

When a unit is crowned, a card asks what they'll be called: the stage's list for their race, the house's last title
first. There is no "type your own". The name then reads "[Title] {House} Name", as before.

| Race | Kingdom | Town | Village | Hamlet | Camp |
| --- | --- | --- | --- | --- | --- |
| Human (and others) | King / Queen, High King / High Queen, Emperor / Empress | Lord / Lady, Duke / Duchess | Reeve, Elder | Headman / Headwoman, Elder | Chief, Elder |
| Dwarf | High Thane, Under-King / Under-Queen | Thane | Stonewarden | Stonewarden, Elder | Elder |
| Orc | Overlord, Warchief | Warlord | Big Boss | Big Boss, Chief | Chief |
| Goblin | Goblin King / Goblin Queen | Boss | Head Goblin | Head Goblin, Chief | Chief |
| Elf | High Lord / High Lady | Lord of the Wood / Lady of the Wood | Warden | Warden, Elder | Elder |
| Lizardman | Great Sire / Great Matriarch | Sire / Matriarch | Shaman | Shaman, Elder | Elder |
| Kobold | Great Father / Great Mother | Den-lord / Den-lady | Den-elder | Den-elder | Den-elder |

- A pair (Lord / Lady) gives the ruler the form for their gender.
- The chosen title is kept per house, so the heir is offered the same one first.
- One per seat stays: a realm can have a ruler of each gender (a pair, as King and Queen were), never two of one.

## 3. Ruler items beyond the crown

Not built (open question 5). The proposal: a Sceptre (gold, a gem: the ruler's people within 8 tiles fight braver,
mood +5), a Banner of the house (cloth, wood: people working near it, mood +5; FAMILY_HOUSES phase 2) and a Seal ring
(silver: needed to make another settlement swear fealty). One of each per realm, none needed to rule.

## 4. Kinds of succession

The realm picks its law of succession on its first crowning (its race's law is offered first). It can change it later
on the Realm page, at a cost: a week (7 days) of mood -10 for its people.

| Law | Who rules next (when no one of the realm holds the heir's item) | Default for |
| --- | --- | --- |
| **Bloodline** | The named heir, else the eldest child, sibling, then the house | Human, Dwarf, others |
| **Chosen heir** | Whoever the ruler named; if none, the eldest of the house | Elf |
| **Might** | The strongest grown member of the house (Attack + Strength + Defence levels) | Orc, Goblin |
| **Council** | The people choose: the grown unit with the most liking (mood, family, skills) | Lizardman, Kobold |
| **Regalia** | Whoever holds the realm's regalia (the item its last ruler was crowned with) | (a choice) |

- **The heir's item comes first under every law** (section 5). The law fills in when no one of the realm holds it.
- Might and Council only look at grown units (age 5 and up). No law ever picks a captive or a slave.
- When the ruler dies, the banner names the heir and why ("holds the heir's circlet", "by Might: the strongest") with
  **Crown as [title]**. The hour's wait after a ruler's death stays (open question 6).

## 5. The heir's item, and claims

The user (2026-10-23): the chosen heir carries an heir's item, it can be stolen, and succession honours who holds the
items, so a rival can kill a prince or princess, take the item, take the succession and take over the realm.

**The item.** An **Heir's circlet** (forge: 1 silver ingot) or, before silver, an **Heir's band** (bone crafter: 1
bones, 1 skin), from Craft new gear › Regalia. It becomes the realm's when one of its people puts it on. A realm has one:
while its heir's item is still in the world, another can't be bound ("House Ash's heir's circlet is held by House
Thorn's Grak"). It never fades on the ground.

**Who is heir.** Whoever of the realm's own grown, free people holds its heir's item (worn or carried) is the heir,
whatever the law says. "Name as heir" sets the law's choice for when no one holds it. The heir's card says "Prince" or
"Princess" (the race's word; Heir for races without one).

**How it's stolen** (what the game can do today):
- Killing the holder: everything a unit carries drops where it dies, the item too. Anyone can pick it up.
- Capturing the holder: the captor takes the heir's item along with their weapons (Captives.dm).
- It can be handed over like any bag item (drag it onto another unit).
- A ruler can't be captured (as before), so a crown is only taken from a body.

**Who can claim.** When a realm's seat falls empty (its ruler dies or steps down) and a unit of *another* realm holds
its heir's item, that unit's player has a claim on the seat. (Under the Regalia law, the realm's regalia counts the same
way, before the heir's item.) Members and vassals of the same realm can't claim each other's seats. The holder must be
grown and free (not a bound captive).

**What happens.**
1. The seat is **claimed**: the realm can't crown anyone while the claim stands, even with regalia. Both players are
   told: "Grak of House Thorn holds your heir's circlet and claims your seat."
2. The claimant's player **presses the claim** from the Realm page, within 10 minutes (else it lapses).
3. The claimed realm answers on its Realm page:
   - **Yield**: it swears fealty to the claimant's realm (becomes its vassal: allies, its people count toward the
     claimant's rank, war and peace are the liege's). The heir's item is spent (it becomes a trophy).
   - **Refuse**: war at once, no warning. The claim stands while the claimant holds the item.
4. A claim ends when:
   - the realm gets the item back (one of its people holds it): the claim is void, crowning is open again;
   - the holder dies, drops it or passes it out of the claimant's realm: the claim lapses;
   - peace is sworn between the two realms: the claim is dropped and the item spent;
   - the claimant takes the refusing realm's last banner: the fallen realm becomes the claimant's vassal (before, a
     fallen realm only sued for peace).

**Across players, for later:** a pressed claim against a player who is away waits for them (they answer when back).
There's no pickpocketing, no forging a false circlet, no claim by marriage, and the claimant's own unit doesn't sit on
the other realm's throne (the realm becomes a vassal; its own people keep their own ruler, crowned once the claim is
settled). Vassal realms have no tribute yet.

## Old saves

- A ruler crowned before this keeps the seat, the title they have and the bonus they were given, with no regalia
  needed. The card asks for the stage's item with no penalty.
- A name the old Town rank-up wrote as "{House} Lord Grak" is put back as "Lord {House} Grak".
- Existing heirs and houses don't change. A realm without a law uses its race's law.

## Open questions for the user

Answered: titles (only the list), the heir's item (built as section 5), the crown (+150 at Kingdom).

Still open (the draft's proposal is what's built):
1. **Stage bonuses:** +50 at a Camp up to +150 at a Kingdom (built), or +150 everywhere?
2. **Without the regalia:** the ruler loses only the bonus (built), or the seat?
3. **Succession laws:** all five (built), or start with fewer?
4. **The ruler items** in section 3 (sceptre, banner, seal ring): now, later, or not at all? (not built)
5. **The hour's wait** after a ruler dies: keep (built), or let the rightful heir skip it?
6. **The forge's old Gold Crown recipe** (1 gold ingot, the forge's own Craft menu) still makes the Kingdom's crown;
   the Regalia menu asks 3 gold ingots and a cut ruby. Keep both, or drop the cheap one?
7. **A claim's 10 minutes** to press, and a vassal realm as the prize: right, or should a pressed claim give more
   (coins, the land)?
