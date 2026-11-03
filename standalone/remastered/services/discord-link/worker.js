// Banners of the Deep: the Discord link service, 2026-10-24. Plan: planning/DISCORD_LINKED_ROLES.md. It gives members
// of the game's Discord server two verified facts for Linked Roles: `played` (has played the game) and `founder`
// (first played before the public launch). Written against the web-standard fetch API; server.mjs runs it as a plain
// Node web server on any machine (not Cloudflare: the user's choice), with its records in one JSON file.
//
//   POST /played        the launcher, right after a Discord sign-in: "Authorization: Bearer <the player's token>",
//                       body {"game_name": "..."}. The token is checked with Discord (it must be this app's); the
//                       first time, the player is recorded and Founder decided.
//   GET  /linked-role   a server member starts the connection (Discord opens this from the server's Linked Roles).
//   GET  /callback      Discord sends them back; the service pushes {played, founder} to Discord, which gives roles.
//   GET  /play?return=<a game server's /join>   a player in a web browser signs in with Discord to play on that game
//                       server (its web link, engine/web); /callback records them as a player and sends them back
//                       with a sign-in token the server checks (one use, 5 minutes; the format: tools/web_token.py).
//   GET  /              a one-line health page.
//
// Settings (server.mjs reads them from link.env or the environment): DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET,
// REDIRECT_URI (this service's /callback), FOUNDER_CUTOFF (an ISO date; empty = before launch, so everyone who plays
// now is a Founder), DISCORD_BOT_TOKEN and DISCORD_GUILD_ID (to add players to the community server on sign-in),
// GAME_TOKEN_SECRET (the game server's sign-in secret, its RM_WEB_SECRET_FILE) and GAME_URLS (the game servers /play may
// send players back to, comma-separated, e.g. https://play.example.com). Records, one per Discord ID, in the store env.LINKS:
//   player:<id>  {first_played, game_name, founder}      tokens:<id>  {access, refresh, expires_at}
//   state:<s>    short-lived, one per sign-in attempt ("1", or {"play": the game server's /join} for /play)
// No Discord password is ever seen; tokens are only used for this app's role connection.

const API = 'https://discord.com/api/v10';
const PLATFORM = 'Banners of the Deep';
const STATE_TTL = 600;   // seconds a sign-in attempt may take
const GAME_TOKEN_TTL = 300;   // seconds the game server's sign-in token is good for (it joins once)
// Public hosting (10-31, security review): sign-in attempts are kept in memory, not in the records file (anyone can
// start one), at most STATES_MAX at once; /played calls Discord at most PLAYED_PER_S times a second, and does a
// player's server join and role push at most once a COOLDOWN_MS, so a flood can't get this machine banned by Discord.
const STATES_MAX = 5000;
const PLAYED_PER_S = 5;
const COOLDOWN_MS = 60000;
const DISCORD_TIMEOUT_MS = 10000;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (request.method === 'POST' && url.pathname === '/played') return await played(request, env);
      if (request.method === 'GET' && url.pathname === '/linked-role') return await linkedRole(env);
      if (request.method === 'GET' && url.pathname === '/callback') return noStore(await callback(request, url, env));
      if (request.method === 'GET' && url.pathname === '/play') return await playStart(url, env);
      if (request.method === 'GET' && url.pathname === '/') return text('Banners of the Deep link service: up.');
      return text('Not found.', 404);
    } catch (err) {
      return page('Something went wrong', 'The link service hit an error. Try again in a minute.', 500);
    }
  },
};

// --- the launcher reports a sign-in ---
async function played(request, env) {
  const auth = request.headers.get('Authorization') || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
  if (!token) return json({ ok: false, error: 'no token' }, 401);
  if (!takeToken(env)) return json({ ok: false, error: 'busy, try again shortly' }, 429);
  // /oauth2/@me says which application the token was issued to: only our own app's tokens count, so a token from
  // some other Discord app can't mark anyone as a player.
  const me = await discord(env, '/oauth2/@me', { headers: { Authorization: `Bearer ${token}` } });
  if (!me.ok) return json({ ok: false, error: 'token not accepted by Discord' }, 401);
  const info = await me.json();
  if (!info.application || info.application.id !== env.DISCORD_CLIENT_ID || !info.user || !info.user.id)
    return json({ ok: false, error: 'not a Banners of the Deep sign-in' }, 403);
  let body = {};
  try { body = await request.json(); } catch (_) { /* the game name is optional */ }
  const record = await recordPlayer(env, info.user.id, gameName(body.game_name));
  if (!coolDown(env, info.user.id)) return json({ ok: true, founder: record.founder, joined: 'recently' });
  await pushIfConnected(env, info.user.id, record, info.user.username);
  const joined = (info.scopes || []).includes('guilds.join') ? await joinServer(env, info.user.id, token, record) : 'not asked';
  return json({ ok: true, founder: record.founder, joined });
}

// --- the community server: a player who signs in is added to it, with their roles (the user, 2026-10-24: "option
// 2", fully automatic). Discord only allows this for a bot in that server with Create Invite (and Manage Roles to give
// roles), using the player's own sign-in token with the guilds.join permission they approved. The bot token lives only
// here, never in the launcher. Roles are found by name ("Player", "Founder") so no IDs need copying.
async function joinServer(env, id, token, record) {
  if (!env.DISCORD_BOT_TOKEN || !env.DISCORD_GUILD_ID) return 'not set up';
  const bot = { Authorization: `Bot ${env.DISCORD_BOT_TOKEN}`, 'Content-Type': 'application/json' };
  const roles = await roleIds(env, record);
  const r = await discord(env, `/guilds/${env.DISCORD_GUILD_ID}/members/${id}`, { method: 'PUT', headers: bot,
    body: JSON.stringify({ access_token: token, roles }) });
  if (r.status === 201) return 'joined';                 // new member, roles given with the join
  if (r.status !== 204) return 'failed';
  // already a member: the join sets no roles then, so give any they're missing
  for (const role of roles)
    await discord(env, `/guilds/${env.DISCORD_GUILD_ID}/members/${id}/roles/${role}`, { method: 'PUT', headers: bot });
  return 'already a member';
}

async function roleIds(env, record) {
  const want = ['Player'].concat(record && record.founder ? ['Founder'] : []);
  const r = await discord(env, `/guilds/${env.DISCORD_GUILD_ID}/roles`, { headers: { Authorization: `Bot ${env.DISCORD_BOT_TOKEN}` } });
  if (!r.ok) return [];
  const all = await r.json();
  return want.map(n => (all.find(x => x.name === n) || {}).id).filter(Boolean);
}

// The first sign-in is recorded once; Founder is decided then and never taken away.
async function recordPlayer(env, id, name, now = new Date()) {
  const key = `player:${id}`;
  const old = await env.LINKS.get(key, 'json');
  if (old) {
    if (name && old.game_name !== name) { old.game_name = name; await env.LINKS.put(key, JSON.stringify(old)); }
    return old;
  }
  const record = { first_played: now.toISOString(), game_name: name || '', founder: isFounder(env, now) };
  await env.LINKS.put(key, JSON.stringify(record));
  return record;
}

export function isFounder(env, when) {
  const cutoff = (env.FOUNDER_CUTOFF || '').trim();
  if (!cutoff) return true;                       // no launch date yet: everyone playing now plays before launch
  const at = Date.parse(cutoff);
  return Number.isNaN(at) ? true : when.getTime() < at;
}

function gameName(raw) {
  return typeof raw === 'string' ? raw.replace(/[^A-Za-z0-9_]/g, '').slice(0, 32) : '';
}

// --- a server member connects ---
async function linkedRole(env) {
  return authorize(env, '1', { scope: 'identify role_connections.write', prompt: 'consent' });
}

// --- a player in a web browser signs in to play on a game server (its web link, engine/web) ---
async function playStart(url, env) {
  const back = gameReturn(url.searchParams.get('return'), env);
  if (!back) return page('Can\'t sign in here', 'This sign-in link doesn\'t lead to one of our game servers.', 400);
  return authorize(env, JSON.stringify({ play: back }), { scope: 'identify' });
}

// The game server's /join the player came from, if it is one of GAME_URLS: never anywhere else (a sign-in link can't
// be made to hand someone's token to another site).
function gameReturn(raw, env) {
  if (!raw || !env.GAME_TOKEN_SECRET || env.GAME_TOKEN_SECRET.length < 32 || !env.GAME_URLS) return null;   // the game wants 32+
  let u;
  try { u = new URL(raw); } catch (_) { return null; }
  if (u.username || u.password) return null;
  const allowed = env.GAME_URLS.split(',').map(s => { try { return new URL(s.trim()).origin; } catch (_) { return null; } });
  if (!allowed.includes(u.origin) || u.pathname !== '/join') return null;
  // rebuilt from its parts, without any token or name of the visitor's (the server reads query names in any case)
  const q = new URLSearchParams([...u.searchParams].filter(([k]) => !['token', 'name'].includes(k.toLowerCase())));
  return u.origin + '/join' + (q.toString() ? '?' + q : '');
}

// sign-in attempts, in memory (per service): swept as new ones come, never more than STATES_MAX
function states(env) {
  return env.STATES || (env.STATES = new Map());
}
function putState(env, state, saved) {
  const m = states(env), now = Date.now();
  for (const [k, v] of m) { if (v.exp > now) break; m.delete(k); }   // oldest first (insertion order)
  if (m.size >= STATES_MAX) return false;
  m.set(state, { saved, exp: now + STATE_TTL * 1000 });
  return true;
}
function takeState(env, state) {
  const m = states(env), e = m.get(state);
  m.delete(state);
  return e && e.exp > Date.now() ? e.saved : null;
}

async function authorize(env, saved, params) {
  const state = randomHex(16);
  if (!putState(env, state, saved)) return page('Busy', 'Too many people are signing in right now. Try again in a minute.', 503);
  const q = new URLSearchParams({ client_id: env.DISCORD_CLIENT_ID, redirect_uri: env.REDIRECT_URI, response_type: 'code', state, ...params });
  return new Response(null, { status: 302, headers: {
    Location: `https://discord.com/oauth2/authorize?${q}`,
    // the state is tied to this browser too, so a link someone else started can't be finished here
    'Set-Cookie': `botd_state=${state}; Path=/callback; Max-Age=${STATE_TTL}; HttpOnly; Secure; SameSite=Lax`,
  } });
}

// The game server's sign-in token (engine/web RmWebServer.CheckToken, tools/web_token.py): "1.<payload>.<signature>",
// the payload base64url JSON {key, exp}, the signature base64url HMAC-SHA256 of "1.<payload>" with the shared secret.
export async function gameToken(secret, key, exp) {
  const enc = new TextEncoder();
  const signed = '1.' + b64url(enc.encode(JSON.stringify({ key, exp })));
  const k = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return signed + '.' + b64url(new Uint8Array(await crypto.subtle.sign('HMAC', k, enc.encode(signed))));
}

async function callback(request, url, env) {
  const code = url.searchParams.get('code'), state = url.searchParams.get('state') || '';
  if (url.searchParams.get('error')) return page('Not connected', 'The connection was cancelled. You can start again from the server\'s Linked Roles.');
  const cookie = (request.headers.get('Cookie') || '').match(/(?:^|;\s*)botd_state=([0-9a-f]+)/);
  if (!code || !state || !cookie || cookie[1] !== state)
    return page('Not connected', 'This link has expired or wasn\'t started here. Start again from the server\'s Linked Roles.', 400);
  const saved = takeState(env, state);   // once only
  if (!saved)
    return page('Not connected', 'This link has expired or wasn\'t started here. Start again from the server\'s Linked Roles.', 400);
  const play = saved.startsWith('{') ? JSON.parse(saved).play : null;
  const tok = await discord(env, '/oauth2/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ client_id: env.DISCORD_CLIENT_ID, client_secret: env.DISCORD_CLIENT_SECRET,
      grant_type: 'authorization_code', code, redirect_uri: env.REDIRECT_URI }) });
  if (!tok.ok) return page('Not connected', 'Discord didn\'t accept the connection. Start again from the server\'s Linked Roles.', 400);
  const t = await tok.json();
  const userRes = await discord(env, '/users/@me', { headers: { Authorization: `Bearer ${t.access_token}` } });
  if (!userRes.ok) return page('Not connected', 'Discord didn\'t say who you are. Try again.', 400);
  const user = await userRes.json();
  if (!user || !/^\d{1,20}$/.test(String(user.id))) return page('Not connected', 'Discord didn\'t say who you are. Try again.', 400);
  if (play) {
    // signed in to play: a player like a launcher sign-in (/played), then back to the game server with its token
    const record = await recordPlayer(env, user.id, '');
    await pushIfConnected(env, user.id, record, user.username);
    const back = new URL(play);
    back.searchParams.set('token', await gameToken(env.GAME_TOKEN_SECRET, `discord-${user.id}`, Math.floor(Date.now() / 1000) + GAME_TOKEN_TTL));
    return new Response(null, { status: 302, headers: { Location: back.toString() } });
  }
  await saveTokens(env, user.id, t);
  const record = await env.LINKS.get(`player:${user.id}`, 'json');
  await pushRoleConnection(env, t.access_token, record, user.username);
  return record
    ? page('Connected', `Your Banners of the Deep account is linked${record.founder ? ', and you\'re a Founder' : ''}. Your roles appear in the server in a moment.`)
    : page('Connected, but not played yet', 'Your account is linked, but you haven\'t played yet. Download the game, sign in with Discord in its launcher, and your Player role follows by itself.');
}

// --- keeping Discord up to date ---
async function saveTokens(env, id, t) {
  await env.LINKS.put(`tokens:${id}`, JSON.stringify({ access: t.access_token, refresh: t.refresh_token,
    expires_at: Date.now() + (t.expires_in || 0) * 1000 }));
}

async function pushIfConnected(env, id, record, username) {
  const saved = await env.LINKS.get(`tokens:${id}`, 'json');
  if (!saved) return;                             // never connected from the server: nothing to update yet
  let access = saved.access;
  if (Date.now() > saved.expires_at - 60000) {
    const r = await discord(env, '/oauth2/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ client_id: env.DISCORD_CLIENT_ID, client_secret: env.DISCORD_CLIENT_SECRET,
        grant_type: 'refresh_token', refresh_token: saved.refresh }) });
    if (!r.ok) return;                            // the member revoked it: they reconnect from the server
    const t = await r.json(); await saveTokens(env, id, t); access = t.access_token;
  }
  await pushRoleConnection(env, access, record, username);
}

export function roleConnection(record, username) {
  return { platform_name: PLATFORM, platform_username: (record && record.game_name) || username || '',
    metadata: { played: record ? 1 : 0, founder: record && record.founder ? 1 : 0 } };
}

async function pushRoleConnection(env, access, record, username) {
  return discord(env, `/users/@me/applications/${env.DISCORD_CLIENT_ID}/role-connection`, { method: 'PUT',
    headers: { Authorization: `Bearer ${access}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(roleConnection(record, username)) });
}

// --- small helpers ---
function discord(env, path, init = {}) { return (env.FETCH || fetch)(API + path, { signal: AbortSignal.timeout(DISCORD_TIMEOUT_MS), ...init }); }
// /played: a bucket of PLAYED_PER_S a second (per service), and one join and role push a player a COOLDOWN_MS
function takeToken(env) {
  const b = env.PLAYED_BUCKET || (env.PLAYED_BUCKET = { n: PLAYED_PER_S * 2, at: Date.now() });
  const now = Date.now();
  b.n = Math.min(PLAYED_PER_S * 2, b.n + (now - b.at) / 1000 * PLAYED_PER_S); b.at = now;
  if (b.n < 1) return false;
  b.n -= 1; return true;
}
function coolDown(env, id) {
  const m = env.COOLDOWNS || (env.COOLDOWNS = new Map()), now = Date.now();
  if (m.size > 10000) for (const [k, t] of m) if (now - t > COOLDOWN_MS) m.delete(k);
  if (now - (m.get(id) || 0) < COOLDOWN_MS) return false;
  m.set(id, now); return true;
}
// the callback's answers carry a sign-in token or a state: never cached, never sent on as a referrer; its cookie goes
function noStore(r) {
  r.headers.set('Cache-Control', 'no-store'); r.headers.set('Referrer-Policy', 'no-referrer');
  r.headers.append('Set-Cookie', 'botd_state=; Path=/callback; Max-Age=0; HttpOnly; Secure; SameSite=Lax');
  return r;
}
function b64url(bytes) { let s = ''; for (const b of bytes) s += String.fromCharCode(b); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
function randomHex(n) { return [...crypto.getRandomValues(new Uint8Array(n))].map(b => b.toString(16).padStart(2, '0')).join(''); }
function json(obj, status = 200) { return new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json' } }); }
function text(s, status = 200) { return new Response(s, { status, headers: { 'Content-Type': 'text/plain; charset=utf-8' } }); }
function page(title, message, status = 200) {
  const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  return new Response(`<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Banners of the Deep</title>
<body style="margin:0;background:#16110c;color:#eee2c4;font:17px -apple-system,Segoe UI,sans-serif;text-align:center;padding:18vh 16px">
<h1 style="color:#f2d27a;font:40px Georgia,serif;margin:0 0 6px">Banners of the Deep</h1><h2 style="font-weight:600;margin:0 0 14px">${esc(title)}</h2>
<p style="max-width:34em;margin:0 auto">${esc(message)}</p></body>`, { status, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}
