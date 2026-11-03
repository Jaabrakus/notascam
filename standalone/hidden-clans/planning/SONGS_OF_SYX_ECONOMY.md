# A player-run economy for Banners of the Deep, with lessons from Songs of Syx

Research notes, 2026-10-23, reworked the same day around the user's goal:

> An MMO where people control houses and small armies, and a King rules the land, like Game of Thrones. The
> players themselves should build the economy, if they want to. But that's impossible without assistance.

So in this plan **the players set the prices, taxes, tolls and trade, not the game**. The game does two
things:

1. It supplies the **reasons** to trade: food rots, things wear out, resources sit in different places.
2. It supplies **assistance**: stewards, standing orders, ledgers and contracts. That way a lord with a
   town, an army and a life outside the game can still run an economy.

The Songs of Syx research below supplies the mechanics behind both. Section 6 comes from the community wikis
and players' write-ups. Sections 7 and 8 come from **the game's own rule files** (the demo, read 2026-10-24);
where the two disagree, sections 7 and 8 are right.

## 1. Who sets what: the economy as a feudal ladder

| Rank | Who | What they control in the economy |
|---|---|---|
| **King of the land** | The player whose house holds the throne of a region (or of the whole land) | Royal tax on the great houses; tolls on the king's roads, bridges and ports; the land's laws (market peace, slavery allowed or not, which goods are banned); the royal mint; calling the banners for war |
| **Great lord** | A house sworn directly to the King, with houses sworn to them | Tax on their own sworn houses; fees at their town's market; who may hold land in their territory; sending the King's tax on |
| **House** (every player) | A town plus a small army and a hero party | What it makes; its stall prices; trade pacts with other houses; whom it swears to; whether it pays, haggles or rebels |
| **NPC towns** | The game | Only an early-game safety net: they buy cheaply and sell dearly, so players trading with each other always gets a better deal |

Each level takes a cut from the level below, **in goods carried by real caravans** (lesson 9). So a war is
about money as well as land: rebelling means you stop paying, and raiding a tax caravan both feeds you and
weakens a rival.

This fits what is already built: realms, fealty and vassals (`Realms.dm`), regalia, heirs and claims
(`Rulership.dm`), coin treasuries and player stalls (`Market.dm`), standing orders on the village board
(`Board.dm`).

## 2. Assistance: what makes a player-run economy playable

In Songs of Syx one player runs the whole economy. Here a player is also fighting, exploring and ruling, so
the economy needs help that works **while they're away**. In the Songs of Syx research, the import and
export depots that trade by rule were what made trade bearable.

- **Steward (a unit job, like Merchant).** A steward runs the house's standing economic orders while the
  player does something else or is offline. For example: "sell iron above 8, keep 40", "buy grain below 3",
  "pay our lord's tax on time" or "send 10% of ore to House Varn". This is the board's "keep at least 30
  wood" standing order, extended to trade.
- **Ledger.** A screen showing what came in and went out: taxes paid, taxes received, tolls, sales,
  purchases, and stock that rotted. Songs of Syx's treasury screen does the same.
- **Contracts on the board.** "Buy 50 iron at 8 each, delivered to Stonehold within 3 days." Any house can
  take one. The coins are held by the game (escrow) until the goods arrive, so no one can be cheated. This
  is how strangers trade with each other in an MMO.
- **Price hints.** The market screen shows what goods actually sold for nearby over the last few days. The
  players' own trades set these numbers, so players set the prices while newcomers aren't lost.
- **Tax and toll presets.** A King or lord picks "light / customary / heavy" instead of typing numbers. The
  people's mood and the vassals' loyalty react to the choice (lesson 9: taxing too hard leads to riots).
- **Banner call with supply.** When the King calls the banners, each house's steward packs rations and
  clothes for its army and sends them along (lesson 10).

## 3. Reasons to trade, from Songs of Syx

Without these, every house can make everything it needs and never has to trade.

- **Resources by region.** Iron in the hills, grain on the plains, timber in the forests, gems deep
  underground. The Daggerfall-scale world (`MMO_ARCHITECTURE.md` §11) makes this natural. A house sitting
  on iron needs a house sitting on grain.
- **Storage that slows rot instead of stopping it** (lesson 4). Today nothing on a stockpile ever rots.
  Change it so food on the ground rots at the full rate, on a stockpile at half rate, and in a cellar or
  with salt much slower. Raw food should keep longer than cooked food. A surplus must then be sold before
  it spoils.
- **Goods that wear out** (lesson 7). Clothes and tools wear, furniture breaks, ale gets drunk. Armies wear
  through gear fastest. This keeps up steady demand.
- **Labour as the real cost** (lesson 3). Houses that specialise do better than houses that make everything,
  which is what makes vassals worth having.

## 4. Where Banners of the Deep stood on 2026-10-23

| Area | Kin & Stone now | Code |
|---|---|---|
| Prices | Fixed value per item kind (ore 4, gold ingot 30, gems 25...) | `Trade.dm` `RemasterTradeValue` |
| Outside trade | An NPC caravan every 2 days with fixed wares and prices | `Trade.dm` |
| Coins | A treasury for each realm; merchant stalls sell at a markup of 50–300% chosen by the player | `Market.dm` |
| Standing orders | "Keep at least N of X" work orders on the village board | `Board.dm` |
| Storage | Main stockpile plus filtered zones; nothing on a store ever rots | `Zones.dm`, `FoodSupply.dm` |
| Transport | Haulers, mine carts on rails that wait until full | `Delivery.dm`, `Carts.dm` |
| Between realms | Migrants, fealty, vassals, war, claims to the throne | `Realms.dm`, `Rulership.dm` |
| Needs | Hunger, sleep, rooms; moods are built but switched off | `Moods.dm`, `Rooms.dm` |

## 5. Suggested order

1. **Storage slows rot**, raw food keeps longer than cooked. It's small and self-contained, and gives the
   first reason to trade.
2. **Steward job plus trade standing orders**, built on the board's standing orders and the merchant stall.
   This is the assistance the rest depends on.
3. **Tribute in goods by caravan** between vassals and lords, with tax presets and a loyalty reaction. This
   is where the feudal ladder starts to matter.
4. **Ledger screen.**
5. **Contracts with escrow**, and price hints from real trades.
6. **King's powers**: royal tax, road tolls, laws of the market, the mint. This needs the land-wide throne in
   the MMO world.
7. **Resources by region and goods that wear out**, built alongside the world generation work.
8. **Coin sinks** before a persistent world goes live: tolls, upkeep, mercenary wages, regalia. Songs of Syx
   players grumble about inflation, and in an MMO coins that never leave pile up for ever.

## 6. How Songs of Syx's economy works (the research)

**1. Prices move.** Each settlement has its own price for every good, set by how rare and valuable it is
there. Where trade connects the world, prices tend to even out. Flooding a market can make a good nearly
worthless.

**2. Trade has friction.** Trading with a faction needs a trade agreement, paid in money or goods. Tariffs
are charged both ways as a percentage of the price, and each item also costs something to move. Buy and
sell prices differ, so buying to resell rarely pays. Factions that like you give better prices, and trade
stops if their opinion of you drops far enough. Import and export depots then trade automatically.

**3. Labour is the real currency.** The best player guide values everything in worker-days. Compare an
import bill with the workers that making the good yourself would tie up. Import if the freed workers can
earn more elsewhere.

**4. Storage quality decides spoilage.** Goods on the ground decay at the full rate, a hauler's store cuts
decay by 25% and a warehouse by 50%. Grain keeps well while bread spoils quickly, so players keep big grain
stores and put a bakery in each neighbourhood.

**5. Logistics is a cost you can see.** Haulers are small one-good stores placed outside workshops, and
warehouses hold many goods but need upkeep. Bulk transport waits for a minimum load, so it only pays over
long distances. A building's "workload" shows when its storage is full or its workers spend their time
walking.

**6. Needs, expectations and population.** Happiness is how far needs are met compared with what citizens
expect. Mostly it comes from being able to reach services. Each race has its own favourite foods. Unhappy
citizens leave and happy cities draw immigrants.

**7. Goods that wear out.** Clothes wear out, and one player worked out that 200 citizens get through about
1,280 garments a year. Furniture needs twice its weight in wood.

**8. Social classes.** The population is split into nobles (named by the player to run things), citizens,
children and slaves. Citizens stay because they are loyal and happy, slaves only while they submit.

**9. Taxing regions in goods.** A cut of what conquered regions produce is shipped to your import depots.
Taxing costs admin points and the region's loyalty, and taxing too hard leads to riots.

**10. Armies need supply lines.** Armies in the field are fed by supply depots that send caravans with
rations and clothes.

**11. Money inflates.** Denarii lose value over time.

### What not to copy

- **Logistics that only pays off at 10,000 citizens.** Banners of the Deep houses are small and orders are
  single-click, so haulers and carts should just work.
- **Fiddly sliders for everything.** Players warn that raising rations above 1 can cause sudden famine.
  Use presets and stewards instead of making lords fine-tune numbers.

## 7. What the game's own files say (read 2026-10-24)

The user installed the **Songs of Syx Demo** (Steam,
`~/Library/Application Support/Steam/steamapps/common/Songs of Syx Demo`). Its rules are plain-text files in
`SongsOfSyxMac.app/Contents/Resources/base/data.zip`, under `data/assets/init/` (457 files). These are the
real numbers, not the wiki's. It's the demo, so some late-game content may be missing.

**Prices aren't in the files.** There's no price list. Only a few goods carry a modifier (bread ×1.1, meat ×1.2,
wine ×1.1), and a grain or wood price cap. The game works prices out in its code from what each good costs to
make, which supports section 5, item 5: prices should come from what things cost to make and from real trades, not from a fixed table.

### Spoilage: each good's decay rate (relative)

| Rots fast | Middling | Keeps | Almost never |
|---|---|---|---|
| bread 1.0, fish 1.0, meat 0.75 | fruit 0.5, vegetables 0.5, livestock 0.5, mushrooms 0.25, beer 0.2, herbs 0.2 | wood, grain, leather, clothes, wine, clay 0.1; fabric, metal, tools, weapons, armour, **rations** 0.05; furniture 0.02 | stone, ore, coal, jewellery 0.01; gems 0.001 |

The game is built around three things here:
- **Bread rots 10 times faster than grain**, which is why players store grain and bake near the homes.
- **Rations (0.05) keep 20 times longer than bread**, so they're what armies march on.
- **Ore, stone and gems keep for ever**, so they're good for stockpiling and trade.

### Production: what one worker makes in a day

| Gathering | Per worker-day | Farms and animals | Per worker-day |
|---|---|---|---|
| Woodcutter | 4 wood | Grain farm | 4 grain |
| Stone mine | 4.5 stone | Vegetables / fruit | 2.1 (orchard 2.45 fruit) |
| Coal mine | 4 coal | Cotton | 3 |
| Ore mine | 1.5 ore | Mushrooms | 1.1 |
| Clay pit | 1.5 clay | Herbs / spices | 0.25 |
| Gem mine | 0.2 gems | Fishery | 1.4 fish |
| Sithilon (rare) | 0.1 | Hunter | 2.2 meat + 1.4 leather |

Mines are scarce in the same way: ore turns up on 50% of mountain tiles but only 5% of open ground, and gems
on 15% of mountain tiles. Stone comes three times faster than ore, and ore seven times faster than gems.
Banners of the Deep' new vein rules (surface iron is rare, rare ores are deep) follow the same pattern.

**Workshops**, per worker-day:

| Workshop | In | Out |
|---|---|---|
| Bakery | 6 grain + 1 wood (or 0.5 coal) | 6 bread |
| Charcoal burner | 2 wood | 6 coal |
| Smelter | 1.25 ore + 1.25 coal | 0.5 metal |
| Smithy | 0.4 metal + 2 coal | 2 tools, or 0.5 sword, or 0.25 plate armour |
| Carpenter | 2 wood | 0.5 furniture |
| Mason | 2 stone | 0.5 cut stone |
| Tailor | 4 leather (or 4 fabric) | 3 clothes |
| Weaver | 2 cotton | 2 fabric |
| Brewery | 2 grain + 0.25 pottery + 0.5 coal | 2.5 beer (fruit gives 2.25 wine) |
| Ration maker | 3 meat (or fish) + 0.125 herbs | 3 rations |
| Bowyer | 4 wood + 1 leather | 0.4 bow |

From those numbers, **one suit of plate armour costs about 12 worker-days**: about 2.7 for the ore, 3.2
smelting, 4 at the smithy and about 2 burning charcoal. A sword costs about 5, and a set of clothes about 1.5.
That's the scale of effort a slow, grindy game wants, and the scale of what a raid takes from someone.

### Livestock (pastures, per worker-day)

| Animal | Gives |
|---|---|
| Auroch (cattle) | 0.56 meat + 0.56 leather |
| Entelodont (pig-like) | 1.12 meat |
| Globdien (fowl) | 1.05 eggs + 0.35 meat |
| Onx (wool beast) | 1.8 cotton (wool) + 0.7 meat |

Each pasture also breeds about 0.09 livestock a day. Animals have a climate (aurochs don't live in hot
lands), graze, and can pull caravans. An auroch slaughtered gives 0.8 meat and 0.5 leather.

### Races: what each eats, and what it's good at

| Race | Eats | Drinks | Works better or worse at |
|---|---|---|---|
| Human | bread, meat, mushrooms, eggs | anything | farms ×1.1; learning ×2 |
| Dondorian (dwarf-like) | meat, fish, mushrooms | **beer only** | mines ×1.15, workshops ×1.2, smithy and jewellery ×1.25; farms ×0.75 |
| Tilapi (elf-like) | meat, fruit, eggs | **wine only** | orchards and woodcutting ×1.4, hunting and bows ×1.2; mines ×0.75 |
| Cretonian (farmers) | vegetables, bread, fruit | anything | farms and orchards ×1.25; workshops ×0.8 |
| Garthimi (goblin-like) | meat, fish | — | mines ×1.25, hunting ×1.2, hauling ×1.25; farms ×0.75 |
| Cantor (brute) | eggs, meat, fish | anything | mines, workshops, refining, woodcutting ×2; farms ×0.6 |
| Argonosh (reptile) | meat, fish, eggs | anything | soldiers ×1; hauling ×0.5 |

Races also differ in how fast they breed and how readily they migrate in. For example, Dondorians' growth is
0.02 against Garthimi's 0.2.

### Needs and the world

- **Needs** grow at their own rates per day: hunger 0.5, thirst 0.2, shopping 0.15, doctor 0.1, temple
  0.05, and so on. Each is met by reaching a service building (tavern, well, bath, shrine, market). How
  happy a city is, and how big it can grow, follows how well needs are met, raised to the power 2.55, so
  half-met needs give far less than half the people.
- **Time:** 4 days a season, so a year is 16 days.
- **Trade:** moving goods costs 5% of their value per tile (`TRADE_COST_PER_TILE 0.05`). A conquered
  region pays half its production as tribute (`REGION_TRIBUTE_AMOUNT 0.5`).

## 8. What Banners of the Deep should take from the files

1. **Rot rates for the storage-rot change** (section 5, item 1). Use the relative rates above: bread, fish
   and meat fast, fruit and vegetables middling, grain and wood slow, ore and stone hardly at all. Halve
   them on a stockpile and quarter them in a cellar room. Make **rations** the slow-rotting food armies and
   hero parties carry, which fits the banner call in section 2.
2. **Race work bonuses and food likes.** Give our seven races the same kind of profile, so houses of
   different races want to trade with each other:
   - **Dwarves:** mines, smithing and jewellery; ale, meat and mushrooms; poor farmers.
   - **Elves:** woodcutting, orchards, bows and hunting; wine and fruit; poor miners.
   - **Humans:** farms and learning; eat most things.
   - **Orcs:** heavy work in mines and workshops; poor farmers.
   - **Goblins and Kobolds:** mining, hauling and hunting.
   - **Lizardmen:** fishing; fish, meat and eggs.
3. **A worker-day price yardstick.** When prices start to move (section 5, item 5), seed each good's starting price
   with how many worker-days it takes to make, using the table above: plate armour about 12, a sword about 5,
   clothes about 1.5. Then let player trades move it.
4. **Livestock, when we add it:** three animals are enough.
   - Cattle give meat and leather, and pull carts and caravans.
   - Sheep give wool and meat.
   - Hens give eggs.
   Each needs a fenced pasture on fertile ground, and outputs follow the per-worker-day table. This fits with
   the fertility work that's still paused.
5. **Fuel as a real input.** The game's metal chain runs on coal: it smelts with coal and smiths with coal,
   and charcoal comes from wood. If Banners of the Deep' forge and smelter don't burn fuel yet, adding charcoal
   would tie forests to weapon making, which makes a tended forest worth even more.
6. **Distance costs.** Five percent of value per tile is the game's carry cost. For Banners of the Deep' caravans,
   the price hints in section 2 should show the same: goods carried far cost more, and road tolls add on top.
7. **Tribute size.** The game takes half a region's production. That's the "heavy" end. For Banners of the Deep'
   tax presets, roughly light = 10%, customary = 20%, heavy = 35–50%, with loyalty falling faster the
   heavier it is.

### Already done since this plan was written (2026-10-23)

- Living resources: trees and living vein blocks, tending, and veins scarce at the surface.
- The resource sack.
- Mine carts riding lifts between levels.
- Gathering pop-ups and log lines.

## 9. Automation: how Songs of Syx runs a city, and how Banners of the Deep runs a village (2026-10-24)

The user asked to look at this before building more: "what I like is maybe how they do automation".

### How Banners of the Deep works today: you run the people

Everything starts from **a unit**. You select it and give it something to do.

| Tool | What it does | Where |
|---|---|---|
| **Direct orders** | Click a tree, rock, item or place; Shift queues more | Orders tab |
| **Roles** | A unit becomes a woodcutter, miner, hauler, farmer, hunter, cook, builder, doctor, gravedigger, merchant or board worker, and works **within 6 tiles of its work area** | Work tab, per selected unit |
| **Production queue** | Each click queues **one** item at the carpentry. The worker must carry the wood and reach the workshop | Work tab |
| **Bulletin board** | One-off work orders (chop 20 wood, mine 10 stone, collect food, make an item), taken by board workers | Village › Board |
| **Standing orders** | "Keep at least 30 wood": posts board orders by itself when stock drops | Village › Board |
| **Construction tasks** | Paint a plan; builders fetch material and build; with none, a board order is posted | Build tab |
| **Stores** | Stockpile plus filtered zones; haulers carry; carts on rails | Work tab |
| **While you were away** | The same jobs catch up for up to 8 hours | — |

It's capable, but every worker is set up one at a time. Each item made is a click. Nothing says what the
village makes or uses per day. A workshop doesn't "make furniture" on its own: a person queued to make one
piece does.

### How Songs of Syx works: you run the workplaces

Everything starts from **a place**.

1. **You build a workplace**, such as a farm, mine, woodcutter's camp, bakery or smithy, and furnish it. Its
   furniture decides how many people can work there (each workbench says how many workers, how much
   storage and how much speed it adds), and its size decides the output (a farm is so many tiles of
   field).
2. **You choose what it makes, once.** A smithy makes tools, or swords, or plate armour. It keeps on making
   it for as long as it has inputs. There's no per-item clicking.
3. **People staff it by themselves.** You set how many workers the place may have, and the realm's free
   workforce fills those slots, nearest first. You never pick the individual.
4. **Goods move by themselves.** A workplace fetches its inputs from nearby storage and keeps its output in
   its own storage. Haulers and warehouses pull from it, and warehouses can be told which goods to keep and
   where to fetch from.
5. **Every place shows its numbers:** workers, inputs and outputs per day, how full its storage is, and how
   busy it is ("workload"). A goods screen adds up what the whole city makes and uses each day.
6. **Services run themselves too.** People walk to the tavern, well, market or temple when their needs call.

The player's job becomes deciding what should exist and how many people each place gets, not ordering
anyone about.

### What Banners of the Deep should take: workplaces with jobs, beside direct control

Banners of the Deep is an RTS with heroes and armies, so direct control stays: you can still grab any unit and
send it anywhere. What's missing is the Songs of Syx layer for everyone you aren't watching:

1. **Workplaces.** Any workshop already in the game (carpentry, forge, smelter, kitchen, leatherworks...)
   counts, plus work zones painted on the land: **a woodlot, a quarry or mine face, a field, a fishing
   spot**, and later a pasture. Each has a number of **worker slots**, at first 1 per workstation, or so
   many tiles of zone per worker.
2. **A standing product** per workplace, chosen once: "the carpentry makes furniture". Add a **stop at**
   number ("until there are 20 on the stockpile"), so it never floods the store. This takes over from
   per-click queues; the Board stays for one-off jobs.
3. **Automatic staffing.** Villagers without a role fill open slots, nearest first. A realm priority list
   (food first, then wood, then tools...) decides who goes where when there aren't enough hands. A unit you
   give a direct order to leaves its slot until the order is done, then goes back.
4. **Inputs and outputs that move by themselves.** A workplace's worker fetches its inputs from the nearest
   store that has them, and puts its output in the nearest store or cart stop. The parts already exist:
   delivery, haulers, carts and the sack.
5. **One Industry screen.** Each workplace shows its workers, product, inputs and outputs per day, and why
   it's idle ("no wood", "store full", "no workers"). A village total of made against used per day goes
   on top. Songs of Syx's goods screen is the model, and it's also what the steward and ledger in section 2
   build on.
6. **Living resources fit straight in.** A woodlot zone follows the realm's tend setting, so a tended forest
   becomes a steady, staffed timber camp. A mine zone on a living vein block leaves its last ore.

### What not to copy

- Songs of Syx has **no direct control** of people. Banners of the Deep keeps it, because heroes, armies and
  emergencies need it.
- Its cities run to thousands, and a Banners of the Deep house is a few dozen people, so slots, zones and the
  Industry screen should stay small and simple. Presets beat sliders.

### Suggested first step

**Workplaces for the crafting stations, plus a woodlot zone.** A workshop gets a product, a "stop at"
number and worker slots, staffed automatically by villagers without a role. A woodlot is a painted zone
with slots, following the tend setting. Show both on a first Industry list. Mines, fields and pastures
follow the same pattern after that.

## Sources

- [Logistics, Songs of Syx Wiki](https://songsofsyx.wiki.gg/wiki/Logistics)
- [Hauler, Songs of Syx Wiki](https://songsofsyx.wiki.gg/wiki/Hauler)
- [Trading, Songs of Syx Wiki](https://songsofsyx.com/wiki/index.php/Trading)
- [Citizens, Songs of Syx Wiki](https://songsofsyx.com/wiki/index.php/Citizens)
- [Subjects, Songs of Syx Wiki](https://songsofsyx.com/wiki/index.php/Subjects)
- [Tax, Songs of Syx Wiki](https://songsofsyx.com/wiki/index.php/Tax)
- [Food, Songs of Syx Wiki](https://songsofsyx.wiki.gg/wiki/Food) and [songsofsyx.com Food](https://songsofsyx.com/wiki/index.php/Food)
- [Furniture](https://songsofsyx.com/wiki/index.php/Furniture), [Clothes](https://songsofsyx.com/wiki/index.php/Clothes)
- [Refining, Songs of Syx Wiki](https://songsofsyx.wiki.gg/wiki/Refining)
- [Opinion, fan wiki](https://songs-of-syx.fandom.com/wiki/Opinion)
- [Import it, or make it yourself? (alttab.wiki)](https://alttab.wiki/posts/sos-import-or-produce/)
- [The World and Beyond, developer devlog](https://songsofsyx.itch.io/songs-of-syx/devlog/157425/the-world-and-beyond)
- Steam discussions: [warehouse setups](https://steamcommunity.com/app/1162750/discussions/0/768556945317687253/),
  [long-distance transport](https://steamcommunity.com/app/1162750/discussions/0/768556945317562967/),
  [inflation](https://steamcommunity.com/app/1162750/discussions/0/4510921146057354604/),
  [trade agreements V68](https://steamcommunity.com/app/1162750/discussions/0/604146450928105568/),
  [workload](https://steamcommunity.com/app/1162750/discussions/0/2934616148071933256),
  [food stockpiles](https://steamcommunity.com/app/1162750/discussions/0/4352242595081964150),
  [famine collapse](https://steamcommunity.com/app/1162750/discussions/0/3759977946668483866),
  [farm labour](https://steamcommunity.com/app/1162750/discussions/0/4360123163643589584/?ctp=2),
  [clothes per year](https://steamcommunity.com/app/1162750/discussions/0/3806155532863394974)
