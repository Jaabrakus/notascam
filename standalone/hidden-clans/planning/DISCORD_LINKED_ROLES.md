# Discord Linked Roles: verified Player and Founder (plan, 2026-10-24)

The user: "Plan Linked Roles first: verified Player and Founder roles in my Discord server."

Linked Roles let a Discord server give a role only to members whose account an app has verified. Here the app is
"Banners of the Deep" (Discord application YOUR_DISCORD_CLIENT_ID, the one the launcher's sign-in uses), and it
tells Discord two facts about each member: **has played the game** and **is a Founder**. The server then has a
**Player** role and a **Founder** role that members claim themselves and can't fake.

## What a member sees

1. In your server they open the server menu, then **Linked Roles**, and pick **Player** (or click a "Get the
   Player role" link you post in #welcome).
2. Discord asks them to connect **Banners of the Deep**. A page from our link service opens, they approve with
   Discord, and it says "Connected".
3. If they've played, Discord gives them **Player** at once, and **Founder** too if they qualify. Their profile
   shows a "Banners of the Deep" connection with their game name.
4. Someone who hasn't played yet gets "You haven't played yet. Download the game, sign in with Discord, then
   come back." The role follows by itself the next time they connect.

## How the pieces fit

```
 Launcher (player's Mac)          Link service (small, always online)            Discord
 ──────────────────────          ─────────────────────────────────            ───────
 Sign in with Discord ──token──▶ POST /played: checks the token with
                                 Discord (/users/@me), records
                                 {discord_id, game_name, first_played}
                                                                      ◀─ member clicks the role in your server
                                 GET /linked-role ─▶ Discord approve page
                                 GET /callback: code ─▶ tokens
                                 PUT role-connection {player, founder} ─▶ Discord gives the roles
```

- **The launcher** already signs players in. One addition: right after sign-in, while it still holds the
  Discord token, it sends that token to the link service's `/played`. The service never trusts a name the
  launcher sends; it asks Discord who the token belongs to. Nothing else in the game changes.
- **The link service** is a small web program with three addresses (`/played`, `/linked-role`, `/callback`) and
  a tiny store with one record per Discord ID (first played, game name, Founder, and the member's Discord refresh
  token so it can update their roles later). Recommended host: **Cloudflare Workers** with Workers KV. It's free at
  this size, gives HTTPS and a `*.workers.dev` address with no domain needed, and keeps the secrets out of the
  code. Any small host would do.
- **Discord** stores the two facts (role-connection metadata) and gives the roles.

## The two facts (role-connection metadata)

Registered once with Discord (`PUT /applications/{app id}/role-connections/metadata`, with the bot token):

| key | type | Player role rule | Founder role rule |
|---|---|---|---|
| `played` | boolean | must be true | must be true |
| `founder` | boolean | | must be true |

Up to 5 facts are allowed. Room is left for later ones: `house_rank` (Lord, King) as a number, `days_played`, or a
house ID.

**Who is a Founder: your call.** Options:
- **(a) Played before a date** you choose, for example the public launch. The simplest, and fair.
- **(b) The first N players** (say the first 500 to play).
- **(c) A list you keep** (friends, testers, early supporters), on top of (a) or (b).

Whichever you pick, Founder is decided once, when someone first plays, and never taken away.

**Chosen (user, 2026-10-24): (a).** Founder = anyone who first plays before the public launch date. The date is still to come from the user; the service reads it from a setting (`FOUNDER_CUTOFF`), so it can be set or moved without a code change, and anyone who played before it keeps Founder.

## What you do (these need your accounts and secrets, so I can't do them)

1. **Make the Cloudflare account** (free), or pick another host.
2. **Make the two secrets in the Discord portal**, and paste them into the host's secret settings yourself, never in
   chat:
   - **OAuth2 › Reset Secret** gives the client secret, which the service needs to finish connections.
   - **Bot › Reset Token** gives the bot token, which is used once to register the two facts.
3. **In your server** (Server Settings › Roles): create **Player** and **Founder**, then in each role's
   **Links** tab add the "Banners of the Deep" requirement shown in the table above. I can walk you through it
   or do it in the browser pane while you're signed in.
4. **Choose the Founder rule** (a, b or c above) and the cutoff date or number.

## What I build

1. **The link service:** one Worker script and its KV store, the `/linked-role` start page, the `/callback`
   that finishes the connection and pushes the facts, and `/played` for the launcher. It refuses anything it
   can't confirm with Discord, and asks for only `identify role_connections.write`.
2. **A one-time setup script** that registers the two facts with Discord.
3. **The launcher addition:** after sign-in, report "played" to the service, then forget the token.
4. **Discord portal settings:** the Linked Roles Verification URL (General Information) and the service's
   `/callback` as a second redirect (OAuth2). I can set these in the browser pane.
5. **Tests:** the service against Discord's real API with a test account (you approving once), plus offline
   checks of every refusal path (wrong state, expired code, unknown player, someone else's token).

## Order

1. You: host account and Founder rule.
2. Me: service, setup script, launcher addition, portal settings. You paste the two secrets.
3. You or me: create the two roles and link them.
4. Test together: you connect from the server and get Player (and Founder).

## Later, on the same service

- **House and rank roles:** "Lord", "King", "House Stonehold" roles that follow the game's politics
  (the `house_rank` fact, or the bot giving house roles).
- **The bot in the server:** news, siege announcements, "who's online".
- **Online game servers checking sign-ins:** the same service can vouch for players when the game is hosted.

Related: memory `discord-login` (app ID, redirect, Public Client), `mac-app/Launcher.m` (the sign-in).

## Built (2026-10-24)

`services/discord-link/`: `worker.js` (the service), `wrangler.toml` (settings), `register-metadata.mjs` (one-time facts registration), `worker.test.mjs` (10 offline tests against a fake Discord, all passing: refusals of missing, unknown and other-app tokens; Founder before and after the cutoff and never taken away; the one-use state tied to the browser; connecting before or after playing; expired-token refresh; a wrong secret pushes nothing), `README.md` (setup steps). The launcher reports "played" after each Discord sign-in once `DMLinkService` in `mac-app/Launcher.m` holds the deployed address. Not deployed yet: it waits for the Cloudflare account, the two secrets and the server roles (README steps 1-8).

## Hosting changed (user, 2026-10-24: "dont use cloudflare")

No Cloudflare. The same service runs as a plain Node web server (`services/discord-link/server.mjs`) on any machine, with its records in one private JSON file (`links.json`) and its settings and secret in `link.env` (never shared). Testing on the user's Mac works at `http://127.0.0.1:8787` (only for the user, on that Mac). Everyone needs an always-on machine with a public https address, the same kind the online game server will need. 12 offline tests pass, including real HTTP requests to the Node server and the records file surviving a restart. Setup: `services/discord-link/README.md`. Where it is hosted for everyone is still to choose.
