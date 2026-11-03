# Guest mode plan (2026-10-31)

**Decided (owner, 10-31):** "its all good" to the plan and its recommended answers, with one change: "guest can fight
players only if players attack them". Then: "players can do anything to [guests] they can regularly do but when guest
leave the units do the burn animation or a random death animation cant be kept". So:
- Players treat guests like anyone: declare war on them, fight, capture, enslave. Realms are at peace unless one declares
  war (War.dm), and a guest can't declare war, so a guest only ever fights back.
- When a guest leaves, every unit that came from them dies where it stands, even one a player enslaved: half burn
  ("Burned To Death"), the rest a random death of the game's (cold, lightning, goo, bones, heart, old age, holy fire),
  acted out by the page, then gone with what it carried. No body, no Legends line.
- Giving items needs no lock: you can only hand items to your own units already (Bag.dm `RemasterGive`).
- Guests are told by their key: it starts with "guest" as the engine keeps it ("Guest Kiwi", "guestkiwi"); no account may.

**Status (10-31 ~13:30):**
- Landed: "guest-mode-game" 13:01 (Guests.dm), "guest-mode-page" 13:07 (the banner and Leave), "guest-keep-village" 13:15
  (owner: "allow them to save progress if they play as a guest if they do the ingame sign up"), "guest-link-settings" 13:17
  (owner: "they can link their account in settings right and it saves?": Link your account in Settings). In app 146 since
  the 13:17 and 13:20 train builds; the lead checked a guest in the browser pane (banner, Leave, 0 server errors).
- Proof: tests/guest_check.dm 44/44 (arena), tests/guest_page_check.py (headless page), tests/guest_web_probe.py 7/7 on a
  scratch engine.
- Installed 13:53: the browser lobby (G1) as engine d575a1d4 = v35 + engine/web ("guest-web-engine"; probe 7/7, obey 32/32,
  clip 11/11, combat passed; undo restore-points/before-engine-guest-web-20261031-135323).
- Changed 13:47 (owner: "only allow them to name themselves anything but when they leave have a mix of death animations
  and turn to stone"): others see the name a guest typed (no "Guest", no number); leaving, about half their people turn
  to stone (a new page death: they stiffen and grey in stone dust; a "<name>, turned to stone" statue is left, not
  blocking) and the rest die one of the game's deaths ("guest-names-stone").
- 13:53 "guest-goodbye-card": Leave anyway shows "Your village is gone" with Play again / Sign in with Discord, over the web
  link's red disconnect bar (the lead's browser check).
- For players to reach it: the server needs `RM_GUEST=1` (after G1 is installed); Sign up needs `RM_WEB_SIGNIN_URL`, the
  Discord link service's /play, which is built but not hosted yet. Until then the Sign up and Link your account buttons
  stay hidden and guests see only "unless you sign up" with Leave.
- Fixed 13:25 ("guests-only-on-guest-servers"; owner: "fix it"): guests exist only on a server with `RM_GUEST=1` (a public
  browser server). The Mac app's own worlds, Host for friends and Join a friend have no guests, so a Mac or Discord name
  starting with "guest" is an ordinary player, and the Mac app never makes a guest who would need to sign up in game. Test
  worlds: `RM_GUEST=1 python3 tools/web_host.py --private-world ...`.


The owner (10-31): "i want to allow guest to play but are restricted to some races no save let them know after their
session the things they build will disappear unless account it made what other features should we lock from guest
mode". The lock list below was agreed in chat ("Yes, write the plan"); the questions at the end are still open, and
the plan uses the recommended answer for each until the owner says otherwise.

## Summary

- **A guest** is someone who joins a server from the browser with a typed name instead of signing in with Discord. Their
  key is always `Guest <name>`, so a guest can never take a real player's name or saves.
- **Guests play the core game:** gather, build, fight wild things and raids, take quests. They choose from four races
  (Human, Dwarf, Elf, Orc) and never draw a rare one.
- **Nothing a guest does is saved.** No company save, no profile (achievements, designs, settings), nothing in the
  world save. When they leave, their units, buildings, laid walls, items and claims are removed.
- **Locked for guests:** trading with players, land claims, realms and rulership, alliances and clans, capturing or
  attacking players' units, world chat, pigeons and private messages, making quests, saved designs, achievements,
  hosting and admin. Each refusal says what signing in unlocks.
- **They're told:** a guest banner from the start, a warning on Leave, and a page after the session that says their
  village is gone and offers Sign in with Discord.
- **Keep my village:** a guest can sign in during the session and keep the company they built.
- About 4 to 5 days in seven steps (G1 to G7), each landed on its own.

## Who is a guest

Today the browser lobby (engine/web/RmWebServer.cs) joins a player one of two ways:

| Way in | Today | With guest mode (`RM_GUEST=1`) |
|---|---|---|
| A signed one-use link (Discord `/play`, `tools/web_token.py`) | joins as the account (`CheckToken`) | unchanged: a full player |
| A typed name, on a server without sign-in (`RM_WEB_SECRET_FILE` unset) | a full player | unchanged (a private test server) |
| A typed name, on a server with sign-in and `RM_WEB_OPEN=1` | **a full player under any name it types**, so it can load an account's saves | a guest: key `Guest <name>` |
| A typed name, on a server with sign-in and neither | refused (the Sign in page) | a guest when `RM_GUEST=1`, else refused as today |

- The engine gives every typed-name join on a sign-in server the key `Guest <name>` (NamePattern already allows
  letters, digits, spaces, `-` and `_`; the prefix fits within the 64-character key limit). The link service and
  `web_token.py` never issue an account that starts with `Guest ` (checked in `CheckToken` too). This also closes the
  impersonation hole in the third row.
- The game tells a guest by that prefix: `proc/RmIsGuest(mob/M)` = the key starts with `Guest `. No new native.
- **Where guest mode applies (recommended, question 1):** servers people join: the browser lobby now, the MMO's servers
  later. Single-player in the Mac app keeps saving as today (its own disk). "Host for friends" stays as it is: the
  host's friends keep their companies in the host's world.
- **Limits (recommended, question 5):** at most 2 guests per address at once (the engine, at `Join`), and at most 10
  guests per server (`RM_GUEST_MAX`); past either, the lobby says "Guest places are full: sign in to play."
- The lobby (`lobby.html` / `signin.html`) shows both: **Sign in with Discord** (the main button) and **Play as a guest**
  with a name field and one line: "Guests can't keep anything: your village disappears when you leave."

## What guests can do

- The core loop: gather, build (workshops, walls, floors, plans), work orders, jobs, cooking and crafting, fighting wild
  creatures and AI raids, taming, healing, swimming, ships, NPC caravan trade (coins into their own treasury).
- Take quests from the board, hand them in and get rewards (which vanish with them).
- Local talk (Say to the units near them).
- Settings change for the session; the page keeps them in the browser's own storage.

## What's locked, and where it hooks in

Every refusal is one notice: "Guests can't <do this>. Sign in with Discord to <do it> and keep your village." One
proc gives the reason: `Player/proc/RmGuestLock(what)` returns "" or that text.

| Locked | Why | Where (today's code) |
|---|---|---|
| Rare races and races beyond the four | the owner's ask; rare odds come from achievements | Restart.dm `Restart()` (the menu list); Rarity.dm `RemasterRareDraw` returns none for guests |
| Trading with players: buying or selling at a player's Market stall, the Merchant job | no muling loot to an account | HUD.dm `RemasterTouchCommand` "market"; Market.dm (buyer and seller both checked) |
| Giving: handing items to another player's unit, carrying their units, picking up items in their land | same | Bag.dm `RemasterGive` (the receiving unit's owner), TargetActions.dm `carryunit`, Zones.dm `RemasterMayCollect` / `RemasterClaimed` |
| Land claims (the Claim banner) | a guest's claim blocks others' digging, then vanishes | Claims.dm (banner placement), the Build menu entry hidden |
| Realms: joining one, swearing fealty, accepting a guest | politics with someone who'll vanish | Realms.dm `RemasterRealmCommand` join / fealty (both directions) |
| Rulership: crowning, laws, heir's item, claims on seats | same | Rulership.dm, Succession.dm, Items/Crowning.dm `AddLeader` |
| Alliances and clans: add ally, create or join a clan, clan chat | same | Actions.dm table (`allyadd`, `allyremove`, `createclan`, `clanchat`) through SelectedActions.dm `RemasterCuratedActionReason` |
| Fighting players: guest units can't attack, capture, enslave or siege a player's units or walls, and players' units leave guests alone | free griefing with nothing at stake (question 3) | Attack.dm target checks, Capture.dm / Subdue.dm / Captives.dm, Siege.dm, War.dm; the same rule as allies (`RemasterAlliedKeys`) so attack orders skip them |
| World chat, pigeons (kingdom chat), private messages | spam from throwaway names | Actions.dm `say`, `worldchat`, `msg`; Chat.dm / ChatGroup.dm |
| Making quests (posting work or rewards) | rewards from someone who'll vanish | Quests.dm `RmQuestCommand` post / postform (take, giveup and handin stay) |
| Saved designs | written to the profile | PlanPieces.dm `RmDesigns` save |
| Achievements | written to the profile, raise rare odds | Rarity.dm `RemasterRecordAchievement` (also Progress.dm's caller) |
| Save now | nothing to save | HUD.dm "savenow" |
| Hosting, Admin, the host's settings (difficulty, fog) | not theirs | `RemasterDifficultyCommand`, Fog, Moderation.dm (staff list already) |
| Legends of the world | a guest's deeds don't enter the world's history | Creatures/Death.dm (the `Legends` line) |

Two further limits (question 5): a guest company has at most 30 units (births, migrants and tamed beasts stop there),
and no offline guards: their units leave with them.

## Nothing saved

- `mob/Login` / `Player` load: guests skip `Load()` and `LoadUnits()`, so a guest always starts fresh.
- Saves.dm `SaveUnits`: skips guests (no `units/Guest <name>_save.sav`, no `players/` file), and `RmWorldInfo` leaves
  them out of world-info.json, so the launcher list never shows them.
- Profile (Rarity.dm `RemasterProfilePath` and its users in Audio.dm, PlanPieces.dm): never opened for a guest.
- World save (WorldSave.dm `RemasterSaveWorld`): items, workshops, banners, siege engines and runes whose owner key
  starts with `Guest ` are not written; laid blocks with `remaster_laid_by` a guest are written as the ground they were
  built on. So a server restart can't keep anything a guest made, even if it stops mid-session.
- At world load, anything still owned by a `Guest ` key (a crash between save and logout) is removed.

## When a guest leaves

`Player/Logout()` for a guest (after OfflineGuards' Logout, which then has nothing to keep):
- their units are removed (carried items with them, captives they held set free), their DigAt marks, orders, zones,
  plans, construction sites and blueprints cleared (the same set as Restart.dm's start over, `RmStartOverWork`);
- workshops, items and banners they own, and the blocks they laid (Plans.dm `RmBuilt` with `remaster_laid_by`), are
  removed; the natural ground under built walls stays;
- **terrain they changed stays** (dug tunnels, felled trees, mined rock), like any wild damage (question 4);
- the Player mob is deleted, so the name is free again.

Removing a big guest village could take a tick or two: spread over ticks like the autosave (`RmSaveUnitsSpread`), at
most ~8 ms a tick.

## Telling them

- **From the start:** the HUD's top bar shows "Playing as a guest" with **Sign in to keep your village** (opens the
  Discord sign-in, then Keep my village below). The first time each session, a card explains what guests can't do.
- **On Leave:** a Leave button in the HUD for guests. It warns "Your village, its people and everything you built will
  disappear." with **Sign in and keep it** and **Leave anyway**. Closing the browser tab without it only gets the
  browser's own "Leave site?" prompt (browsers don't show our words there).
- **After the session:** engine/web/ended.html for a guest says "Your village is gone. Guests can't keep what they
  build. Sign in with Discord next time and your village stays." with the Sign in link and Join again.
- Chat and the Who list show guests as "Kiwi (guest)".

## Keep my village

Signing in mid-session (the banner's link, or Leave's **Sign in and keep it**):
1. the Discord sign-in comes back with a token; the engine moves the browser's link from `Guest Kiwi` to the account
   (one connection, the same page; no reload of the world);
2. if the account has **no company in this world**, the guest's company becomes the account's: units, workshops,
   items, banners, laid blocks and the treasury move to the account's key (`ChangeOwnership`, owner keys), and from
   then on it saves like any company;
3. if the account already has a company here (one company per player per world), the guest gets a choice: keep the
   account's company (the guest village goes as on Leave) or start the account over with the guest village (question
   6). Default: keep the account's.

## Steps

| Step | What | Where | Days |
|---|---|---|---|
| G1 | Guest joins: `RM_GUEST`, the `Guest ` key, the caps, the lobby's two ways in | engine/web (RmWebServer.cs, lobby.html, signin.html), services/discord-link (never issue `Guest ` accounts) | 0.5 |
| G2 | Nothing saved: `RmIsGuest`, races, no load, no save, no profile, world save and world load skip guests | Restart.dm, Rarity.dm, Login.dm, Saves.dm, WorldSave.dm, Audio.dm, PlanPieces.dm | 0.5 |
| G3 | The locks: `RmGuestLock` in the HUD dispatcher, the action gate and each feature's own check | HUD.dm, SelectedActions.dm, Market.dm, Realms.dm, Claims.dm, Rulership.dm, Attack.dm, Capture.dm, Siege.dm, Chat.dm, Quests.dm | 1 |
| G4 | Leaving: removal at logout, spread over ticks | QoL.dm / OfflineGuards.dm Logout, WorldSave.dm | 0.5-1 |
| G5 | Telling them: banner, first-time card, Leave, ended page, "(guest)" names | art/hud/src (top bar, card), engine/web/ended.html, Chat.dm | 0.5 |
| G6 | Keep my village: sign-in mid-session, ownership moved | engine/web (relink), Realms.dm/Claims.dm owner keys, a new Guests.dm | 0.5-1 |
| G7 | Checks (below) and a browser-pane play-test | tests/, tools/ | 0.5 |

All the game's guest rules go in one new file, `game/Code/Remastered/Guests.dm`, with small calls from the files above.
Engine changes (G1, G6) are in engine/web only; the native version doesn't change. The quest-maker session is changing
Quests.dm and Moderation.dm (bans) now: the Quests.dm lock is one line at `RmQuestCommand`'s post, landed after theirs.

## Checks

- **Arena test** (`tests/guest_check.dm`, the obey arena): a `Guest ` player gets only the four races; every lock in the
  table refuses with its notice and changes nothing; a player's attack order skips guest units and a guest's skips
  players'; SaveUnits writes no guest file and world-info.json has no guest; the world save holds none of the guest's
  items, workshops, banners or laid blocks; Logout removes all of it and frees the name; a world loaded with a guest's
  leftovers removes them.
- **Keep my village** in the arena: the company moves to the account and saves; with an account company already there,
  the default keeps the account's.
- **Web probe** (`reports/u4-web-1030/tests/u4_web_probe.py` style): the lobby's two ways in, the `Guest ` key, a typed
  name equal to an account joins as a guest (not the account), the caps, the ended page, the relink after sign-in.
- **Browser pane** (owner 10-30: play-test in the browser pane): join as a guest, build a hut, try a locked thing, Leave,
  see the ended page; join again and find nothing left.
- The usual gates when landing: compile, combat, settings.

## Open questions for the owner

1. **Where guest mode applies:** only servers people join (the browser lobby now, the MMO later), or also single-player
   in the Mac app? *Recommended: servers only; single-player on your own Mac keeps saving.*
2. **Which races:** *Recommended: Human, Dwarf, Elf, Orc,* the four everyone knows from 2006.
3. **Fighting players:** can guests fight players at all? *Recommended: no, both ways; guests still face wild
   creatures and AI raids.*
4. **Terrain a guest changed** (dug tunnels, felled trees): stays like wild damage, or is put back? *Recommended:
   stays.* Putting it back means remembering every tile they touched.
5. **Caps:** 30 units a guest company, 10 guests a server, 2 per address? *Recommended as written.*
6. **Keep my village when the account already has a company in that world:** *Recommended: keep the account's; the
   guest village goes.*
