# Banners of the Deep: how to join a friend's world from your browser

Nothing to install. You need three things from the person hosting:

1. **The lobby address**, something like `http://192.168.1.20:8080/` (on their Wi‑Fi) or
   `http://100.101.102.103:8080/` (over Tailscale).
2. **The world password** they chose when they clicked *Host for friends*.
3. **A computer with a desktop browser**: Chrome, Edge, Safari or Firefox, any recent version.
   A keyboard and mouse matter: the game is played with clicks, right-clicks, drags and keys.
   Phones and tablets are not supported yet.

## Joining

1. Open the lobby address in your browser.
2. Type a **name** (letters, digits and `_` only, up to 24) and the **password**, then
   *Enter the world*. The page says "Joining the world…" for a few seconds while the host's
   Mac starts your game client, then the game appears.
3. Your name is how the world knows you: use the same name next time to come back to
   your own people.
4. First time in, a card asks which people you will lead: pick one. You start with three of them.

## Playing

- **Click** a unit (or its face in the Company list) to select it; **drag** a box for several.
- **Click** ground, a tree, rock or an item to walk, chop, mine or pick up. **A** then click:
  attack. **Space** pauses. **F3** opens the in-game guide with every control.
- **Right-drag** moves the camera, **middle-drag** turns it, the **wheel** zooms; **N / Top / Iso / Chase**
  on the minimap panel reset it.
- Questions from the game (a race to choose, a yes/no) pop up as a card in the middle
  of the page; answer there. **Esc** closes cards.

## If something goes wrong

- **"Connection to the game lost. Reconnecting…"** at the top: the page lost the host for a
  moment; it reconnects by itself. If it does not, reload the page: your game client keeps
  running on the host's Mac for about a minute and a half, and you come back where you were.
  After a reload the title screen can stay up for 10–20 seconds on a big world while the
  land is sent again; your people keep working meanwhile.
- **The lobby page does not load**: ask the host whether the lobby is running
  (`tools/web_host.py`) and whether you are on the same network or Tailscale.
- **"Your game client did not start"**: the host's Mac is out of room; ask them to check
  `reports/web-host/`.
- **Wrong password twice**: the world turns you away; join again with the right one.

## For the host

1. In the app, choose **Host for friends** and set a password.
2. Double-click **Host on the Web.command** (next to the app in `standalone/remastered/`).
   A Terminal window opens and prints lines like `Friends open:  http://192.168.86.30:8080/`.
   Leave that window open while friends play; Ctrl+C (or closing it) ends their games.
3. Give friends that address and the password.

(The same thing from a Terminal: `cd standalone/remastered && python3 tools/web_host.py`.) Each friend's browser also talks
to a port from 12200 up on your Mac, so if you port-forward, forward 8080 and 12200–12299;
with Tailscale nothing needs forwarding. Your own game and saves are untouched by web players:
they get their own name and their own people in your world.
