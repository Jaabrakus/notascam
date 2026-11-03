# Admin panel plan (2026-10-31)

**Decided (owner, 10-31, "Yes, all seven", and "this is a mmo there is only one server"):** all seven
recommendations, with one change: there is one server. Admins come from the server's own list, with the owner first;
the host of the server (the owner) is an Admin. Bans and mutes cover the whole server from the start, so A5's
"server-wide, later" folds into A1-A3. A world played alone (no one else can join) keeps its single player as its
Admin, for testing. Build order: A1 and A2, then A3, then A4.
**Changed (owner, 10-31 after A1-A2 landed):** "the admin is not for one player it is for me the overlord who needs to
control the game from player doing crazy shit". Admin is the overlord's (the owner's) alone: nobody gets it for hosting
or for playing alone. The staff are only those the game's `admins.txt` names (shipped with the game; the owner is
`owner kiwimango`), plus helpers the owner adds in game; only the owner adds or removes staff. A plain name counts
only on the server's own Mac in the app; anyone else is named by a Discord key. And for bans (A3): "banned players
turn into wanderers on the map": a banned player's people stay in the world as ownerless wanderers.
**Status (10-31 14:53): A4 landed** ("admin-words-a4" 14:45, "admin-clanchat-a4b" 14:53; gate compile + jscheck + hudjoin +
combat 32/32 each). Mute (already saved) now covers clan chat too (`RmModMayTalk`; world chat, unit say, emotes and
messages already read the flag). The word list: Admins add and take off words on the Admin page's Words view (staff see
it); words come out as stars in chat, unit say, emotes and messages (AntiSpam.dm `Safe_Guard`, Verbs.dm `SendMSG`),
notices, house names and unit names (`RmModFilter`: whole words in any case; "x*" for words starting with x); saved with
the world, logged. A4b: clan chat lines lost their words in every client (`<b><font>…</b>` mis-nested; the chat parser
stops there); fixed. Checks: `tests/admin_words_check.dm` 26/26, `tools/check_admin_hud.py` 20/20, `admin_check` 54/54.
Played in the browser: a listed word starred in world chat as the other player read it; a muted player's clan chat
refused. With this, A1-A4 are done; A5 (server-wide lists for many worlds, a Discord role) comes with the MMO work.
**Status (10-31 12:45):** the overlord-only change landed 12:32 ("admin-overlord-only": `game/admins.txt` ships with
`owner kiwimango`; ids via `RmModIdOf`; typed browser names never match). A3 landed 12:36 ("admin-bans-a3": ban 1 day,
7 days, or for good (Admins only), by name, Discord key and internet address; checked first at log-in; the banned player's people
become ownerless wanderers via RandomWalk, their work and notices end; banned while away = they wander at that
player's next log-in; unban = they start over) and 12:43 ("admin-ban-page": a banned player turned away sees a
Banned card with the reason and until when on their own page). Checks: `tests/admin_check.dm` 54/54 on the live
game, `tools/check_admin_hud.py` 17/17. Played in the browser: banned a player, their 3 people became wanderers, the
card showed on their way back. Left: A4 (mute in clan chat, the word list); Discord sign-in for players from
elsewhere (question 5) needs the web link, which the server-upgrades session owns.

**Status (10-31 12:30, A1-A2):** A1-A2 landed ("admin-panel-a12" 12:21; gate compile + jscheck + hudjoin + combat 32/32; arena
test `tests/admin_check.dm` 40/40; page check `tools/check_admin_hud.py` 15/15; `tests/quest_check.dm` still 58/58).
`R/Moderation.dm`: staff from the host, `admins.txt` and those an Admin adds (keys compared as ckeys); the Admin page;
reports; the log `admin-log.txt` (this engine's text2file adds its own CR LF line break). Played in the browser pane:
a staff player reported another realm's player from the near card, saw it in Reports, muted and kicked them; the log
shows both. Not yet: bans (A3), mute in clan chat and a word list (A4). Reaches the app with the next build.

The owner asked (10-31, during the quest maker build): "for all the quest we also need to make have admin controls or
admins can delete it or and etc a admin list or panel for this this is a big one we need admin controls ban players
look at reports and etc".

## Summary

- **Who is an admin:** the host of a world, plus anyone the host adds from the panel. On a big public server, a list the
  owner keeps (the owner's Discord account first). Two levels: **Admin** (everything) and **Moderator** (quests,
  reports, mute, kick, short bans).
- **One Admin button** on the menu, seen only by admins, with four tabs: **Quests**, **Players**, **Reports**, **Log**.
- **Quests:** every notice in the world, with search and filters. Take one down (the reward goes back to its maker),
  hide its words, or stop a player from posting.
- **Players:** everyone online and everyone known to the world. Message, mute, kick, ban (1 day, 7 days or forever,
  with a reason), unban, go to them.
- **Reports:** players can report a notice or a player (a Report button on the quest card and on another player's
  unit card). Admins see a queue with what was reported, a copy of it, who sent it and when, and close it or act on it.
- **Log:** every admin action, saved, which no admin can change. The owner and the host can always read it.
- **Bans stick only if names are real.** Today anyone can type any name. Browser players who come through a Discord
  link are the only ones whose identity is checked. So bans use the name, the Discord account where there is one, and
  the internet address. Question 5 asks whether public servers should require Discord sign-in.
- **Cost on the server:** almost nothing. The panel's data is sent only while it is open, and a ban check at login is
  one look-up.
- **Work:** about 4 to 5 days in five steps. The first one (quest moderation, mute and kick, the log) takes about 1.5
  days.

## What is there today

Read on 10-31 (paths under `game/Code/`):

| Need | Today |
|---|---|
| Who is an admin | **Nobody.** `Login.dm:55-63` gives the 2006 admin commands to whoever's key is `world.host`. The engine sets `world.host` to "" and never fills it, so it never matches |
| Admin commands | About 40 old verbs in `Admin.dm` (lock down, mute, warp, summon, edit, delete, announce, smite, reboot...). **None can be reached:** they need the old verb panel or command bar, which Remastered hides. Browser players can only send keys bound in the skin |
| Kick, ban | **Neither exists.** No ban list, no check at login |
| Mute | An in-memory `Muted` flag, lost at restart; clan chat ignores it (`Verbs.dm:1166`) |
| Reports | **None.** The hidden `Reportabug` verb writes to `Logs/Bugs.html`, and nothing in the HUD reaches it |
| Moderation log | **None.** The old "Admin Log" and "Chat Log" menu items have no code behind them |
| Word filter | Almost none: `AntiSpam.dm` blocks two strings plus line breaks and HTML |
| The host | `RemasterIsHost()` (`Remastered/Joining.dm:61`): the player whose name matches the `host-name` file the launcher writes. Host-only today: fog of war, the Hosting box, speed when others are on |
| Identity | Names are typed, not checked (the server runs with `auth.mode=0`). Mac players' names come from the launcher (the Discord name if linked, else the Mac account name). Browser players arriving by a signed Discord link get the key `discord-<id>`; the others type a name. The only other signal is the internet address (`client.address`) |
| Admin web page or console | None. The engine's web link and `tools/web_host.py` serve only the game page, joining and a health check |
| Quests to moderate | Since 10-31 11:49: `Remastered/Quests.dm` (quest maker Q1-Q2) |

## 1. Who is an admin

- **The host is always an Admin** of the world they host (`RemasterIsHost`). In single player that is you.
- **The admin list** is saved with the world: names, each with a level (Admin or Moderator), and a Discord id when the
  player has one. Admins add and remove people from the Players tab. Only an Admin can add an Admin.
- **The owner's own list on a public server:** a small `admins.txt` in the server's folder that the game reads at
  start. It holds the owner's Discord account, so the owner is an Admin on every world the server runs, hosted or not.
  Later this can come from a Discord role instead (`planning/DISCORD_LINKED_ROLES.md` already sets up linked roles).
- Admin checks happen on the server, for every command. The page only hides the button.

## 2. The panel

An **Admin** button on the menu (a shield icon), only for admins. It opens a page like Army or Quests, with four tabs.

**Quests**
- Every notice in the world: open, taken down, done and ended, newest first. Search by maker, title or words.
- Each row shows the maker, the title, the reward, how many took it, its state and its report count.
- Actions:
  - **Take down:** ends the notice. The reward goes back to its maker, and handed-in goods go back to the takers,
    exactly as when a notice runs out of time. The journal says "taken down by an admin".
  - **Hide the words:** blanks the maker's text, for a rude notice that is otherwise fine.
  - **Stop posting:** the maker can't post notices for 1 day, 7 days or until lifted.
  - **Go to:** moves the camera to the notice board.

**Players**
- Everyone online, then everyone the world knows (from its saves), with race, company size, last seen, admin level,
  Discord-linked or not, and how many reports.
- Actions:
  - **Message:** a notice only they see.
  - **Mute:** no chat and no notices, for a time.
  - **Kick:** disconnects them; they can come back.
  - **Ban:** 1 day, 7 days or forever, with a reason.
  - **Unban.**
  - **Go to:** the camera goes to their people.
  - **Make Moderator or Admin.**
- An admin can't act on another admin of the same or higher level, or on the host.

**Reports**
- The queue: what was reported (a notice or a player), who sent it, when, the reason they picked, and a copy of what
  they saw (the notice's words and reward, the player's name and house) at that moment.
- Actions: **Close**, **Close and act** (opens the Quests or Players tab on that target), and a note.
- Open reports show a count on the Admin button.

**Log**
- One line per admin action: who, what, on whom, why, when. It is saved and can't be changed or deleted from the
  game. Filter by admin or by target.

## 3. Reports from players

- A **Report** button on the quest card, and on another player's unit card (the Interact tab).
- The player picks a reason: rude words, scam or false notice, griefing, cheating or other. They can add a line.
- A player can send at most 5 reports an hour, and one per target a day, so the queue isn't flooded.
- The report keeps a copy of what was reported. Ending or editing the notice later doesn't change the copy.

## 4. Bans, kicks and identity

- **A ban** stores the name, the Discord id if the player has one, and the internet address of their last
  connection, with the reason, who banned them and until when.
- **At login** (and at the join password for friends' worlds), a match on any of the three refuses the player. They
  see the reason and the end date.
- **Kick** disconnects the player now. Their people stay in the world, as when anyone logs off.
- **The weak spot:** native players' names are not checked, so a banned player can come back under a new name from a
  new address. Discord sign-in fixes that, which is question 5.
- Admins see a player's address only as "same as player X" or "new", never the number itself, to keep players'
  privacy.

## 5. Mute and the word list

- Mute is saved and covers every way of talking: chat, unit say, emotes, clan chat (which ignores mute today) and
  posting notices.
- **A word list** in the panel (Admin only): words that come out as stars. It applies to chat, notices, house names
  and unit names.

## What is saved, and where

| What | Where |
|---|---|
| Admin list, bans, mutes, posting bans, reports, word list | The world save, as one JSON text, like the quests (`WorldSave.dm`) |
| The admin log | Its own file in the world folder, `admin-log.txt`, one line per action, only ever added to |
| The owner's list for a public server | `admins.txt` in the server folder, edited by hand |

For the MMO (many worlds on one server), bans and the owner's admins move to the server's folder, so a ban covers
every world on that server. That comes with the regions and many-players work.

## Server cost

| Part | Cost |
|---|---|
| The panel's lists | Built only while the panel is open, about 2-10 KB a send, rebuilt only on a change |
| The ban check | One look-up per login |
| Reports, log | A few hundred bytes each |
| Admin checks on commands | One look-up per admin command |

## Phases

Each one lands through `land_polish.py` with an arena test and a browser-pane play-test.

| Step | What lands | Days |
|---|---|---|
| **A1** | The admin list (host + added), the Admin button and page, the Quests tab (take down, hide words, stop posting, go to), Players tab (message, mute, kick, go to, make moderator), the Log | 1.5 |
| **A2** | Report buttons (quest card, unit card), the Reports tab and queue, limits | 1 |
| **A3** | Bans: ban, unban, the check at login and at the join password | 1 |
| **A4** | Saved mute everywhere (clan chat too), the word list | 0.5-1 |
| **A5** | Later, with many players: the server's own admin list and bans, a Discord role for admins | with the MMO work |

## Questions for the owner

1. **Who are admins:** the host of each world plus anyone the host adds, and on a public server a list you keep
   (your Discord account first)? *Recommendation: yes.*
2. **Two levels:** Admin (everything) and Moderator (quests, reports, mute, kick, bans up to 7 days)?
   *Recommendation: yes.*
3. **A notice taken down by an admin:** does the reward always go back to its maker, or may an admin keep it from a
   scammer? *Recommendation: always back to the maker. Bans deal with scammers.*
4. **Bans:** by name, Discord account and internet address; 1 day, 7 days or forever, with a reason the banned player
   sees? *Recommendation: yes.*
5. **Discord sign-in for public servers,** so a ban sticks (today names are typed, not checked)? Friends' worlds
   would stay as they are. *Recommendation: yes for public servers.*
6. **The old 2006 admin commands** (warp, summon, heal, announce, edit anything, smite, reboot): bring a few into
   the panel? *Recommendation: only Announce and Go to for now; nothing that edits the world.*
7. **Order:** A1 and A2 first (quest moderation, mute and kick, reports, the log), then A3 bans?
   *Recommendation: yes.*
