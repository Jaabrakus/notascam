# Admin restart notice, player cap and unit limit, 11-01

The owner's Discord account is now the overlord on the public server. The Admin page has a new **restart notice**
button. The world takes **30 players at once** for now, and a **world-wide unit limit** keeps the Mac from being
overrun.

## Done

- **Your Discord account is the owner.** The game's admin list names it next to the Mac account. The public server
  now adds names from each published build to its own copy of the list, without removing any. So you get the Admin
  button when you sign in from a browser.
- **Restart notice** (Admin page, under the search and reason boxes; Admins and the owner only):
  - Pick 1, 2, 5, 10, 15 or 30 minutes. The reason box becomes the message. Press Send notice.
  - Every player online gets a notice, a log line and a chat line at once. They're reminded at 10, 5, 2 and 1 minute
    and at 30 seconds left, then told "now".
  - Anyone who logs in during the countdown is told how long is left.
  - While it runs, the Admin page shows the time left, the message and who sent it, with a Call off button. Calling
    it off tells everyone the world goes on. Both go in the admin log.
  - It only warns. You still restart the server yourself, from Banners Server or by publishing an update.
- **Player cap: 30 at once on the public server.** The 31st person sees a "The world is full" card with a Try again
  button, and nothing of theirs loads. Staff always get in, and people already playing are never kicked. It's a
  server setting, so it can be raised after a load test.
- **Unit limit: 5,000 units in the world on the public server.** That counts everyone's people and the wild creatures
  together. At the limit, growth waits and nobody loses anyone:
  - births wait in the mother, and come about 10 seconds after there's room;
  - stolen beast eggs stay warm, unhatched;
  - no raids or armies that season;
  - no wolves, cave creatures, golems, kobold avengers or dug-up critters;
  - newcomers aren't offered a realm to join.

  A new player's starting company always comes. Each realm gets at most one quiet log line about it every 10 minutes:
  "The world is crowded: births and newcomers wait for room." Caves, caravans and anything players make aren't held.
  Counting the world costs about 3.5 ms, at most every 5 seconds, and only while the limit is on.

## Numbers

- Arena check for the restart notice and player cap: 19 of 19 passed.
- The existing admin panel check still passes in full.
- Arena check for the unit limit (the game's own birth, spawn, raid, egg and migrant code, with a small limit): 27 of 27
  passed. Under the limit everything comes; at it, nothing new does except a new player's company; after some deaths,
  the held birth arrives by itself and the rest resume.

| Check | Result |
| --- | --- |
| Your Discord account in the shipped list | owner |
| A plain player / a Moderator sends a notice | refused / refused |
| The owner sends 5 minutes | 300 s left, message kept |
| 4 min 31 s later | the 2-minute and 1-minute reminders said |
| Time up | ends by itself |
| Cap 30: the 30th / the 31st / staff | in / turned away / in |

