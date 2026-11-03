# How-to-play video, and the guide live, 11-01

The first-steps guide and the online count went live at 12:41. Players got a 2-minute countdown first, the first
update to use it. Then came a 2:34 how-to-play video: a new village played through the guide in the browser, with
captions.

## Done

- **Live** (the owner: "Publish, 2-min countdown"):
  - `publish --countdown 2` reached the game 4 s later. Everyone online saw "The world restarts in 2 minutes: New: a
    first-steps guide and players online".
  - The world restarted on 8a7db52 exactly 2 minutes after the notice. The site and Discord sign-in answered 200, and
    the new server log had no errors.
- **The video** (the owner: "Browser, in the background", "~3 min, fuller tour"):
  - Played in headless Google Chrome with its own temporary profile, so the owner's screen and Chrome were never
    touched. WebGL ran on the M4 through Metal, and the page's screencast was written at 30 fps.
  - Every action was a real mouse move, click or key through the HUD, on a fresh guest village in a public-mode test
    world.
  - Headless Chrome draws no pointer, so the page drew one, with a gold ring on each click. Captions, the title card and
    the end card are drawn in the page in the game's own lettering.
  - The tour: title card, front page and Play, the race picker, the first company, the arrival story, then the guide's
    seven steps (with the chopping, building and crafting waits sped up). Then World chat, the Village, Realm and Army
    tabs, the map, zooming out, and an end card with the address.
  - Of four takes, take 2 played cleanly. Take 3 never found open ground for the carpentry; the recorder now uses the
    game's own placement check. In take 4 a poison spore plant next to the carpentry kept hurting the dwarf, so the
    craft never finished: the brutal world is real. The title card, front page and end card were re-recorded on their
    own and joined to take 2.
- **Installed:** ffmpeg 9.0.2 with Homebrew (the owner's OK).

## Numbers

| Check | Result |
| --- | --- |
| Countdown notice to restart | 12:38:57 to 12:40:59 |
| Video | 2:34, 1920x1080, 30 fps, H.264, 44 MB |
| Files | reports/howto-video-1101: record.py (the take), cut.py (the edit), howto-play.mp4 |
