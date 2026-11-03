# The Discord link service: Player and Founder roles

A small web program for the Banners of the Deep Discord server. When someone signs in with Discord in the game's
launcher, it **adds them to the server automatically** with the **Player** role, and **Founder** too if they first
played before the public launch. The same two facts are also offered through Discord's **Linked Roles** for anyone
already in the server. It runs
on plain Node (18 or newer) on any machine, no Cloudflare, and keeps its records in one file (`links.json`).

Why and how it works: `planning/DISCORD_LINKED_ROLES.md`. Code: `worker.js` (the service) and `server.mjs` (the
web server). Tests: `node --test worker.test.mjs` (16 tests, offline, against a fake Discord).

**Secrets** go only in `link.env`, which stays on the machine and is never shared, never in chat, and never on a
command line. `links.json` holds players' Discord tokens and is private too. Both files are listed in `.gitignore`.

## Who can reach it

Discord never calls the service itself. Members' browsers open it (to connect a role), and players' launchers
report to it (after a sign-in). So:
- **Testing on this Mac:** it runs at `http://127.0.0.1:8787`, and only you, on this Mac, can use it. Discord
  allows `http://127.0.0.1` addresses, so the whole flow works for your own account. Good for a first real test.
- **For everyone:** it has to run on an always-on machine with a public `https://` address, such as a small
  rented server (the same kind of machine the online game server will need), with a web server like Caddy in front
  for HTTPS.

## Setup, once

1. **The two Discord secrets** (Discord Developer Portal, app "Banners of the Deep"):
   - **OAuth2 › Reset Secret.** Copy it into `link.env` (copy `link.env.example` to `link.env`, then
     `chmod 600 link.env`).
   - **Bot › Reset Token.** Put it in `link.env` as `DISCORD_BOT_TOKEN`: the service uses it to add signed-in players
     to the server and give their roles. Then register the two Linked Roles facts once with
     `set -a && . ./link.env && set +a && node register-metadata.mjs`. It should say "Registered: Player and Founder."
2. **The service's address.** Set `REDIRECT_URI` in `link.env` to the address plus `/callback`
   (`http://127.0.0.1:8787/callback` when testing on this Mac).
3. **Start it:** `node server.mjs`. Check: opening the address should show "Banners of the Deep link service: up."
4. **Discord portal addresses:**
   - OAuth2 › Redirects › Add Another: the address plus `/callback`, then Save.
   - General Information › Linked Roles Verification URL: the address plus `/linked-role`, then Save.
5. **The launcher.** In `mac-app/Launcher.m`, set `DMLinkService` to the address (no trailing slash), then
   rebuild the app (`python3 tools/build_app.py`). Every Discord sign-in in the game then marks the player.
6. **Let the bot add people** (Server Settings › Roles): the app's own role, "Banners of the Deep", needs
   **Create Invite** and **Manage Roles** turned on, and must sit **above Player and Founder** in the role list (drag
   it up), or Discord won't let it hand those roles out.
7. **The Linked Roles rules** (Server Settings › Roles), for members who joined some other way:
   - **Player:** Create Role, then the **Links** tab › Add requirement › Banners of the Deep › **Player** is true.
   - **Founder:** the same, with **Player** is true and **Founder** is true.
   - Post in #welcome: "Server menu › Linked Roles › Player to get your role."

When the launcher has the service address (step 5), the sign-in also asks the player "Join servers for you":
that permission is what lets the bot add them. Players who decline are simply not added.

## Playing in a web browser (added 10-30)

The game server can let browser players in directly (its web link, `reports/u4-web-1030/README.md`) and only with a
sign-in. The service does the Discord part:

- **The flow.**
  - The game server's lobby links to `<this service>/play?return=<the game server>/join`.
  - The player signs in with Discord (`identify` only), and is recorded as a player just as a launcher sign-in records
    them.
  - They go back to the game server with a sign-in token for `discord-<their Discord ID>`, good for 5 minutes, once.
- **Settings in `link.env`:**
  - `GAME_TOKEN_SECRET`: the same secret the game server reads from its `RM_WEB_SECRET_FILE`. Make one with
    `python3 -I tools/web_token.py --new-secret <file>`.
  - `GAME_URLS`: the game servers it may send players back to. It sends them nowhere else.
- **On the game server:** `RM_WEB_SIGNIN_URL=<this service>/play`.

## The launch date

Until it's set, everyone who plays is a Founder. To set it, put `FOUNDER_CUTOFF=2027-03-01T00:00:00Z` (your date)
in `link.env` and restart the service. Moving it later never takes Founder away from anyone who already has it.

## Checking it works

Sign in with Discord in the game's launcher, then in your server pick Linked Roles › Player. You should get Player
and Founder, and your Discord profile shows a "Banners of the Deep" connection with your game name.
