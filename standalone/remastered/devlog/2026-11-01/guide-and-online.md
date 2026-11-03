# First-steps guide, players online, top bar look back, 11-01

New players now get a guide: one step at a time at the top left, with the button to press ringed in gold and a pin on
the map showing what to click. The top bar has its old look again, and on the public server it shows how many people
are playing.

## Done

- **Top bar look back** (the owner: "i liked the orignl look but it was overlapping that is all"):
  - The earlier fix stretched the bar to the menu's width and height and moved the goal tracker. All of that is undone.
  - The bar keeps its own size and place. Only its widest is now cut to stop 16 px before the menu, which grows with
    its buttons (Admin, badges).
- **Players online** (the owner: "show a status of how many people are online"):
  - A green dot and "N online" in the top bar, on the public server and on hosted worlds.
  - Its tooltip says how many the world has room for (30 on the public server).
  - Counted at most every 5 seconds for everyone, so 30 players don't each count every update.
- **The guide** (the owner: "we needa video or a tutorial of the game", then "Both, guide first"):
  - The first goals as seven steps: meet your company, first order, bring in supplies, light a campfire, build a
    carpentry, craft something, set a guard.
  - Each step says what to do in a line or two. The button to press gets a pulsing gold ring, and the guide scrolls a
    long panel to it once.
  - On the map, a pin shows what to click: one of your people, the nearest tree, your carpentry. When it's out of
    view, the pin waits at the screen's edge pointing the way, and a click on it takes the camera there.
  - Steps tick off with the same milestones as the Guide (F3) list, which first-minute tracking already logs.
  - **Skip guide** hides it. The Guide (F3) button brings it back.
  - The campfire uses Work › Build at the selected builder (one click). The carpentry uses Work › Place a workshop and
    a click on open ground: at the builder's own spot it fails next to the campfire ("Needs open space, at least two
    tiles from another workshop").
  - The arrival story and the Guide list now point at these paths; the old "Place › Workshops" text was stale.
  - A lone rare creature (Dragon, Spider queen...) keeps its own first steps, with no guide.

- **Fixed while playing it through** (a fresh guest Human village on a public-mode test world, every step through the
  HUD):
  - The arrival story note sat over the goal tracker's last lines: the HUD code that centres cards below the notices
    kept resetting its place. It now leaves the story note alone, so the note sits under the guide.
  - The ring didn't show in the browser pane while it pulsed its opacity. It now pulses its glow.
  - The ring showed over the loading screen. It now waits until the game is up.
  - The tree pin went to the screen's edge when the tree was in view on the left. It now checks whether the map or a
    panel is under it.
  - Clicking the carpentry's half where the builder stood selected the builder. The pin goes to the free half.
  - Skip guide sits inside the card, which opens the Guide when clicked, so Skip did nothing. It has its own click now.
  - Skip guide is logged for first-minute tracking ("guide-skip").
- **First-minute report fixed**: on the server the RMFIRST lines go to the world's ErrorLog.txt, not the server logs the
  report read, so it always said "No first-minute lines yet". It reads both now and lists the guide's steps.

## Numbers

| Check | Result |
| --- | --- |
| Player-cap arena check, with 4 new online-count checks | all passed |
| The guide, played through in the browser | all 7 steps ticked off; "Guide done", then the next-rank tracker |
| Top bar at 1440x900 | ends 16 px before the menu, 48 px tall as before, nothing cut off |
| Online count on the public-mode test world | "● 1 online", tooltip "room for 30" |
| First-minute arena check | passed |
| App build with all of it | 8a7db52 (not published yet) |
