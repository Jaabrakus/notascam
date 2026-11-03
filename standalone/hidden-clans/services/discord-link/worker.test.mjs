// Offline tests for the link service against a fake Discord and an in-memory KV:  node --test worker.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import worker, { isFounder, roleConnection, gameToken } from './worker.js';

const APP = 'YOUR_DISCORD_CLIENT_ID';
function kv() {
  const m = new Map();
  return { m, async get(k, t) { const v = m.get(k); return v === undefined ? null : (t === 'json' ? JSON.parse(v) : v); },
    async put(k, v) { m.set(k, v); }, async delete(k) { m.delete(k); } };
}
// A fake Discord: tokens map to users and apps; it records every role-connection push.
function fakeDiscord({ tokens = {}, codes = {}, refresh = {}, members = new Set() } = {}) {
  const pushes = [], joins = [], roleAdds = [];
  const f = async (url, init = {}) => {
    const path = url.replace('https://discord.com/api/v10', ''); const auth = (init.headers || {}).Authorization || '';
    const bearer = auth.startsWith('Bearer ') ? auth.slice(7) : null;
    if (path === '/oauth2/@me') {
      const t = tokens[bearer]; if (!t) return new Response('{}', { status: 401 });
      return Response.json({ application: { id: t.app }, scopes: t.scopes || ['identify'], user: { id: t.id, username: t.username } });
    }
    if (path === '/users/@me') { const t = tokens[bearer]; return t ? Response.json({ id: t.id, username: t.username }) : new Response('{}', { status: 401 }); }
    if (path === '/oauth2/token') {
      const b = new URLSearchParams(init.body.toString());
      if (b.get('client_secret') !== 'shh') return new Response('{}', { status: 401 });
      if (b.get('grant_type') === 'authorization_code' && codes[b.get('code')]) return Response.json(codes[b.get('code')]);
      if (b.get('grant_type') === 'refresh_token' && refresh[b.get('refresh_token')]) return Response.json(refresh[b.get('refresh_token')]);
      return new Response('{}', { status: 400 });
    }
    if (path === '/guilds/G1/roles') {
      if (auth !== 'Bot bot-secret') return new Response('{}', { status: 401 });
      return Response.json([{ id: 'R0', name: '@everyone' }, { id: 'RP', name: 'Player' }, { id: 'RF', name: 'Founder' }]);
    }
    let m = path.match(/^\/guilds\/G1\/members\/(\d+)$/);
    if (m && init.method === 'PUT') {
      if (auth !== 'Bot bot-secret') return new Response('{}', { status: 401 });
      const body = JSON.parse(init.body); joins.push({ id: m[1], ...body });
      if (!tokens[body.access_token] || !(tokens[body.access_token].scopes || []).includes('guilds.join')) return new Response('{}', { status: 403 });
      if (members.has(m[1])) return new Response(null, { status: 204 });
      members.add(m[1]); return new Response('{}', { status: 201 });
    }
    m = path.match(/^\/guilds\/G1\/members\/(\d+)\/roles\/(\w+)$/);
    if (m && init.method === 'PUT') { roleAdds.push(m.slice(1)); return new Response(null, { status: 204 }); }
    if (path === `/users/@me/applications/${APP}/role-connection` && init.method === 'PUT') {
      pushes.push({ token: bearer, body: JSON.parse(init.body) }); return Response.json({});
    }
    return new Response('{}', { status: 404 });
  };
  f.pushes = pushes; f.joins = joins; f.roleAdds = roleAdds; return f;
}
function env(over = {}) {
  return { DISCORD_CLIENT_ID: APP, DISCORD_CLIENT_SECRET: 'shh', REDIRECT_URI: 'https://link.test/callback', FOUNDER_CUTOFF: '', LINKS: kv(), ...over };
}
const req = (path, init) => new Request('https://link.test' + path, init);
const played = (token, body = { game_name: 'kiwimango' }) =>
  req('/played', { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: JSON.stringify(body) });

test('played: refuses no token, unknown tokens and other apps', async () => {
  const e = env({ FETCH: fakeDiscord({ tokens: { other: { app: '999', id: '7', username: 'x' } } }) });
  assert.equal((await worker.fetch(played(null), e)).status, 401);
  assert.equal((await worker.fetch(played('nope'), e)).status, 401);
  assert.equal((await worker.fetch(played('other'), e)).status, 403);
  assert.equal(e.LINKS.m.size, 0);
});

test('played: records the first sign-in once; Founder before launch', async () => {
  const e = env({ FETCH: fakeDiscord({ tokens: { t: { app: APP, id: '42', username: 'kiwi.mango' } } }) });
  const r = await worker.fetch(played('t', { game_name: 'kiwi mango!' }), e);
  assert.equal(r.status, 200); assert.deepEqual(await r.json(), { ok: true, founder: true, joined: 'not asked' });
  const rec = JSON.parse(e.LINKS.m.get('player:42'));
  assert.equal(rec.game_name, 'kiwimango'); assert.equal(rec.founder, true);
  const first = rec.first_played;
  e.FOUNDER_CUTOFF = '2000-01-01T00:00:00Z';             // a later launch-date change never takes Founder away
  await worker.fetch(played('t'), e);
  const again = JSON.parse(e.LINKS.m.get('player:42'));
  assert.equal(again.first_played, first); assert.equal(again.founder, true);
});

test('founder rule: before the cutoff yes, after it no, no cutoff yes', () => {
  assert.equal(isFounder({ FOUNDER_CUTOFF: '' }, new Date()), true);
  assert.equal(isFounder({ FOUNDER_CUTOFF: '2027-03-01T00:00:00Z' }, new Date('2027-02-28T23:59:00Z')), true);
  assert.equal(isFounder({ FOUNDER_CUTOFF: '2027-03-01T00:00:00Z' }, new Date('2027-03-01T00:00:01Z')), false);
});

test('played after the cutoff: a player, not a Founder', async () => {
  const e = env({ FOUNDER_CUTOFF: '2000-01-01T00:00:00Z', FETCH: fakeDiscord({ tokens: { t: { app: APP, id: '5', username: 'late' } } }) });
  assert.deepEqual(await (await worker.fetch(played('t'), e)).json(), { ok: true, founder: false, joined: 'not asked' });
});

test('linked-role: redirects to Discord with a state kept in KV and in a cookie', async () => {
  const e = env(); const r = await worker.fetch(req('/linked-role'), e);
  assert.equal(r.status, 302);
  const loc = new URL(r.headers.get('Location'));
  assert.equal(loc.origin + loc.pathname, 'https://discord.com/oauth2/authorize');
  assert.equal(loc.searchParams.get('scope'), 'identify role_connections.write');
  assert.equal(loc.searchParams.get('redirect_uri'), 'https://link.test/callback');
  const state = loc.searchParams.get('state');
  assert.ok(e.STATES.has(state));                   // in memory, not in the records file (public hosting, 10-31)
  assert.ok(![...e.LINKS.m.keys()].some(k => k.startsWith('state:')));
  assert.match(r.headers.get('Set-Cookie'), new RegExp(`botd_state=${state};.*HttpOnly; Secure`));
});

async function startLink(e) {
  const r = await worker.fetch(req('/linked-role'), e);
  return new URL(r.headers.get('Location')).searchParams.get('state');
}
const cb = (state, code, cookieState = state) => req(`/callback?code=${code}&state=${state}`, { headers: cookieState ? { Cookie: `botd_state=${cookieState}` } : {} });

test('callback: refuses a missing cookie, someone else\'s state and a reused state', async () => {
  const d = fakeDiscord({ tokens: { a1: { app: APP, id: '42', username: 'k' } }, codes: { c1: { access_token: 'a1', refresh_token: 'r1', expires_in: 600 } } });
  const e = env({ FETCH: d });
  const s = await startLink(e);
  assert.equal((await worker.fetch(cb(s, 'c1', null), e)).status, 400);
  assert.equal((await worker.fetch(cb(s, 'c1', 'deadbeef'), e)).status, 400);
  assert.equal((await worker.fetch(cb(s, 'c1'), e)).status, 200);
  assert.equal((await worker.fetch(cb(s, 'c1'), e)).status, 400);   // one use only
  assert.equal(d.pushes.length, 1);
});

test('callback: a player gets played+founder; someone who never played gets played=0', async () => {
  const d = fakeDiscord({
    tokens: { t: { app: APP, id: '42', username: 'kiwi' }, a1: { app: APP, id: '42', username: 'kiwi' }, a2: { app: APP, id: '9', username: 'new' } },
    codes: { c1: { access_token: 'a1', refresh_token: 'r1', expires_in: 600 }, c2: { access_token: 'a2', refresh_token: 'r2', expires_in: 600 } } });
  const e = env({ FETCH: d });
  await worker.fetch(played('t'), e);
  let r = await worker.fetch(cb(await startLink(e), 'c1'), e);
  assert.match(await r.text(), /linked, and you&#39;re a Founder|linked, and you're a Founder/);
  assert.deepEqual(d.pushes[0].body, { platform_name: 'Banners of the Deep', platform_username: 'kiwimango', metadata: { played: 1, founder: 1 } });
  r = await worker.fetch(cb(await startLink(e), 'c2'), e);
  assert.match(await r.text(), /haven.t played yet/);
  assert.deepEqual(d.pushes[1].body.metadata, { played: 0, founder: 0 });
});

test('played after connecting: pushes the update, refreshing an expired token first', async () => {
  const d = fakeDiscord({
    tokens: { t: { app: APP, id: '9', username: 'new' }, a2: { app: APP, id: '9', username: 'new' } },
    codes: { c2: { access_token: 'a2', refresh_token: 'r2', expires_in: 0 } },
    refresh: { r2: { access_token: 'a3', refresh_token: 'r3', expires_in: 600 } } });
  const e = env({ FETCH: d });
  await worker.fetch(cb(await startLink(e), 'c2'), e);            // connected before playing: played 0
  await worker.fetch(played('t'), e);                             // then plays: the roles follow by themselves
  assert.equal(d.pushes.length, 2);
  assert.equal(d.pushes[1].token, 'a3');
  assert.deepEqual(d.pushes[1].body.metadata, { played: 1, founder: 1 });
  assert.equal(JSON.parse(e.LINKS.m.get('tokens:9')).refresh, 'r3');
});

test('a wrong client secret or a cancelled sign-in never pushes anything', async () => {
  const d = fakeDiscord({ codes: { c1: { access_token: 'a1', refresh_token: 'r1', expires_in: 600 } } });
  const e = env({ FETCH: d, DISCORD_CLIENT_SECRET: 'wrong' });
  assert.equal((await worker.fetch(cb(await startLink(e), 'c1'), e)).status, 400);
  const cancelled = await worker.fetch(req('/callback?error=access_denied&state=x'), e);
  assert.match(await cancelled.text(), /cancelled/);
  assert.equal(d.pushes.length, 0);
});

test('roleConnection shape and unknown paths', async () => {
  assert.deepEqual(roleConnection(null, 'k'), { platform_name: 'Banners of the Deep', platform_username: 'k', metadata: { played: 0, founder: 0 } });
  assert.equal((await worker.fetch(req('/nope'), env())).status, 404);
  assert.equal((await worker.fetch(req('/'), env())).status, 200);
});

// --- the plain Node server (server.mjs): the same service on a real socket, records in a file ---
import { fileStore, serve } from './server.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('file store: survives a restart, expires short-lived keys, file readable only by its owner', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'botd-link-')); const f = path.join(dir, 'links.json');
  const a = fileStore(f);
  await a.put('player:1', JSON.stringify({ founder: true })); await a.put('state:x', '1', { expirationTtl: 1 });
  const b = fileStore(f);
  assert.deepEqual(await b.get('player:1', 'json'), { founder: true });
  assert.equal((fs.statSync(f).mode & 0o777).toString(8), '600');
  await new Promise(r => setTimeout(r, 1100));
  assert.equal(await b.get('state:x'), null);
  fs.rmSync(dir, { recursive: true });
});

test('node server: real HTTP requests reach the service', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'botd-link-'));
  const e = env({ LINKS: fileStore(path.join(dir, 'links.json')), FETCH: fakeDiscord({ tokens: { t: { app: APP, id: '42', username: 'k' } } }) });
  const server = await serve(e, 0, '127.0.0.1'); const port = server.address().port;
  try {
    assert.equal(await (await fetch(`http://127.0.0.1:${port}/`)).text(), 'Banners of the Deep link service: up.');
    const r = await fetch(`http://127.0.0.1:${port}/linked-role`, { redirect: 'manual' });
    assert.equal(r.status, 302); assert.match(r.headers.get('location'), /^https:\/\/discord\.com\/oauth2\/authorize\?/);
    const p = await fetch(`http://127.0.0.1:${port}/played`, { method: 'POST', headers: { Authorization: 'Bearer t', 'Content-Type': 'application/json' }, body: '{"game_name":"kiwimango"}' });
    assert.deepEqual(await p.json(), { ok: true, founder: true, joined: 'not asked' });
    assert.ok(JSON.parse(fs.readFileSync(path.join(dir, 'links.json'), 'utf8'))['player:42']);
  } finally { server.close(); fs.rmSync(dir, { recursive: true }); }
});

// --- joining the community server on sign-in (option 2) ---
const joinEnv = d => env({ FETCH: d, DISCORD_BOT_TOKEN: 'bot-secret', DISCORD_GUILD_ID: 'G1' });

test('join: a new player who allowed it is added with Player and Founder', async () => {
  const d = fakeDiscord({ tokens: { t: { app: APP, id: '42', username: 'k', scopes: ['identify', 'guilds.join'] } } });
  const r = await (await worker.fetch(played('t'), joinEnv(d))).json();
  assert.equal(r.joined, 'joined');
  assert.deepEqual(d.joins[0], { id: '42', access_token: 't', roles: ['RP', 'RF'] });
});

test('join: a player who is already a member gets the missing roles instead', async () => {
  const d = fakeDiscord({ members: new Set(['42']), tokens: { t: { app: APP, id: '42', username: 'k', scopes: ['identify', 'guilds.join'] } } });
  const r = await (await worker.fetch(played('t'), joinEnv(d))).json();
  assert.equal(r.joined, 'already a member');
  assert.deepEqual(d.roleAdds, [['42', 'RP'], ['42', 'RF']]);
});

test('join: after the launch date only Player; nothing without consent or without the bot set up', async () => {
  let d = fakeDiscord({ tokens: { t: { app: APP, id: '5', username: 'late', scopes: ['identify', 'guilds.join'] } } });
  const e = joinEnv(d); e.FOUNDER_CUTOFF = '2000-01-01T00:00:00Z';
  await worker.fetch(played('t'), e);
  assert.deepEqual(d.joins[0].roles, ['RP']);
  d = fakeDiscord({ tokens: { t: { app: APP, id: '6', username: 'shy' } } });          // signed in without guilds.join
  assert.equal((await (await worker.fetch(played('t'), joinEnv(d))).json()).joined, 'not asked');
  assert.equal(d.joins.length, 0);
  d = fakeDiscord({ tokens: { t: { app: APP, id: '7', username: 'k', scopes: ['identify', 'guilds.join'] } } });
  assert.equal((await (await worker.fetch(played('t'), env({ FETCH: d }))).json()).joined, 'not set up');
  assert.equal(d.joins.length, 0);
});

test('join: a wrong bot token fails quietly; the player is still recorded', async () => {
  const d = fakeDiscord({ tokens: { t: { app: APP, id: '8', username: 'k', scopes: ['identify', 'guilds.join'] } } });
  const e = env({ FETCH: d, DISCORD_BOT_TOKEN: 'wrong', DISCORD_GUILD_ID: 'G1' });
  const r = await (await worker.fetch(played('t'), e)).json();
  assert.equal(r.ok, true); assert.equal(r.joined, 'failed');
  assert.ok(e.LINKS.m.has('player:8'));
});

// --- /play: a browser player signs in with Discord to play on a game server (engine/web) ---
const GAME = { GAME_TOKEN_SECRET: 'g'.repeat(64), GAME_URLS: 'http://127.0.0.1:12481, https://play.example.com' };
// the game server's check (RmWebServer.CheckToken): "1.<payload>.<sig>", HMAC-SHA256 with the shared secret
function checkGameToken(token, secret) {
  const [v, payload, sig] = token.split('.');
  const want = createHmac('sha256', secret).update(`${v}.${payload}`).digest('base64url');
  return v === '1' && sig === want ? JSON.parse(Buffer.from(payload, 'base64url').toString()) : null;
}

test('play: only back to one of the game servers, at its /join', async () => {
  const e = env(GAME);
  for (const back of [null, 'https://evil.example.com/join', 'http://127.0.0.1:12481/c/abc/', 'not a url'])
    assert.equal((await worker.fetch(req('/play' + (back ? '?return=' + encodeURIComponent(back) : '')), e)).status, 400, String(back));
  const off = env();   // no game servers set up
  assert.equal((await worker.fetch(req('/play?return=' + encodeURIComponent('http://127.0.0.1:12481/join')), off)).status, 400);
});

test('play: identify only; the player is recorded and sent back with a token the game server takes, once', async () => {
  const d = fakeDiscord({ tokens: { a1: { app: APP, id: '42', username: 'kiwi' } }, codes: { c1: { access_token: 'a1', refresh_token: 'r1', expires_in: 600 } } });
  const e = env({ FETCH: d, ...GAME });
  const r = await worker.fetch(req('/play?return=' + encodeURIComponent('http://127.0.0.1:12481/join?overlay')), e);
  assert.equal(r.status, 302);
  const loc = new URL(r.headers.get('Location'));
  assert.equal(loc.searchParams.get('scope'), 'identify');
  const state = loc.searchParams.get('state');
  assert.match(r.headers.get('Set-Cookie'), new RegExp(`botd_state=${state};`));
  const back = await worker.fetch(cb(state, 'c1'), e);
  assert.equal(back.status, 302);
  const to = new URL(back.headers.get('Location'));
  assert.equal(to.origin + to.pathname, 'http://127.0.0.1:12481/join');
  assert.equal(to.searchParams.has('overlay'), true);
  const claims = checkGameToken(to.searchParams.get('token'), GAME.GAME_TOKEN_SECRET);
  assert.equal(claims.key, 'discord-42');
  const left = claims.exp - Date.now() / 1000;
  assert.ok(left > 290 && left <= 300, String(left));
  assert.ok(e.LINKS.m.has('player:42'));        // a player now, as a launcher sign-in makes one
  assert.ok(!e.LINKS.m.has('tokens:42'));       // nothing kept of their Discord sign-in
  assert.equal(d.pushes.length, 0);
  assert.equal((await worker.fetch(cb(state, 'c1'), e)).status, 400);   // the state once only
});

test('gameToken matches the game server and tools/web_token.py', async () => {
  // the same token tools/web_token.py makes for key "Pane", exp 1793413163, secret "g"*64 (a fixed vector)
  const token = await gameToken('g'.repeat(64), 'Pane', 1793413163);
  assert.deepEqual(checkGameToken(token, 'g'.repeat(64)), { key: 'Pane', exp: 1793413163 });
  assert.equal(token, '1.eyJrZXkiOiJQYW5lIiwiZXhwIjoxNzkzNDEzMTYzfQ.r7MFJqsvq0zhCnC_-GQR12YY0hSy8IE0T0ZNFVo3pd4');
});


// --- public hosting (10-31 security review) ---
test('play: no user info in the return address; a visitor\'s own token or name is dropped from it', async () => {
  const d = fakeDiscord({ tokens: { a1: { app: APP, id: '42', username: 'kiwi' } }, codes: { c1: { access_token: 'a1', refresh_token: 'r1', expires_in: 600 } } });
  const e = env({ FETCH: d, ...GAME });
  assert.equal((await worker.fetch(req('/play?return=' + encodeURIComponent('https://x:y@play.example.com/join')), e)).status, 400);
  const r = await worker.fetch(req('/play?return=' + encodeURIComponent('https://play.example.com/join?overlay&TOKEN=forged&Name=bob')), e);
  const state = new URL(r.headers.get('Location')).searchParams.get('state');
  const back = await worker.fetch(cb(state, 'c1'), e);
  const to = new URL(back.headers.get('Location'));
  assert.deepEqual([...to.searchParams.keys()].sort(), ['overlay', 'token']);
  assert.equal(checkGameToken(to.searchParams.get('token'), GAME.GAME_TOKEN_SECRET).key, 'discord-42');
  assert.equal(back.headers.get('Cache-Control'), 'no-store');
  assert.equal(back.headers.get('Referrer-Policy'), 'no-referrer');
  assert.match(back.headers.get('Set-Cookie'), /botd_state=; Path=\/callback; Max-Age=0/);
  assert.equal((await worker.fetch(req('/play?return=' + encodeURIComponent('https://play.example.com/join')), env({ ...GAME, GAME_TOKEN_SECRET: 'short' }))).status, 400);
});

test('played: a flood is turned away before it reaches Discord; one join and role push a player a minute', async () => {
  const d = fakeDiscord({ tokens: { t: { app: APP, id: '42', username: 'k', scopes: ['identify', 'guilds.join'] } } });
  const e = joinEnv(d);
  const answers = [];
  for (let i = 0; i < 14; i++) answers.push((await worker.fetch(played('t'), e)).status);
  assert.ok(answers.includes(429), answers.join(','));
  assert.equal(d.joins.length, 1);   // the rest within the minute: recorded, not joined again
});

test('sign-in attempts stay out of the records file and are capped', async () => {
  const e = env();
  for (let i = 0; i < 3; i++) await worker.fetch(req('/linked-role'), e);
  assert.equal(e.STATES.size, 3);
  assert.equal([...e.LINKS.m.keys()].filter(k => k.startsWith('state:')).length, 0);
});
