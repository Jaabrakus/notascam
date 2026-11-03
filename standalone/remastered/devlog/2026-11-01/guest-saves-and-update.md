# Guest saves, HUD fixes, update countdowns, 11-01

Guests now keep their village: it's saved in their browser and comes back after a server restart. The browser no
longer offers super speed on the public server, the top bar and menu snap into place, and future updates can warn
players with a countdown. All of it went live at 11:18.

## Done

- **Guest villages saved in the browser** (the owner: "allow people to keep there stuff in guest mode save on browser
  if we can keep it simple for now"):
  - The browser keeps a private code. The server keeps the village under a name made from that code, so it survives
    restarts.
  - **Leave** says "Your village is saved". **Play** in the same browser brings the village back.
  - **The fix before release** (the owner: "we got a error it didnt reload that char"): a village handed back to its
    browser drew no people. The server still thought the old browser had their pictures, item icons, ground and
    models, so it never sent them again. Logging in now clears those lists. Sounds, fonts and 3D gear already went by
    browser.
- **No super speed in the browser** (the owner: "Yes, hide them"): on the public server the speed buttons are hidden.
  The server already refused speed changes there.
- **HUD snapping** (the owner: "some of the hud doesnt snape perfectly"):
  - The top bar lines up with the menu again.
  - The tips and news sit by the command bar's real edge, not an empty box's.
  - Checked at 1440x900, 1280x800 and 1100x700.
  - Two minified lines had lost code to a `//` comment. Both are fixed, and a scan of the HUD sources found no others.
- **Update countdowns** (the owner: "add a countdown to people playing when we are ready"):
  - `public_host.py publish --countdown N` (0, 1, 2, 3, 5, 10, 15 or 30 minutes; 2 by default) tells the running
    world first. Players get the in-game restart countdown, and the update goes in as it ends.
  - The launcher's **Update** button uses 2 minutes. **Go Public** uses none.
  - This works from this build on. The old build couldn't pass the notice on, so this update went in without a
    warning (the owner's call: "Publish, no warning").

## Numbers

| Check | Result |
| --- | --- |
| Arena checks (guest, guest keep, admin, restart cap, chat, bugs, first minute, unit limit, no first house) | 9 of 9 |
| Browser test: Play, Leave, Play again in the same browser | village back, every file 200 or 304 (404s before the fix) |
| Live build | 1eb8324 → 9c12f3d at 11:18 |
