#!/usr/bin/env node
// The Discord link service as a plain Node web server (the user, 2026-10-24: "dont use cloudflare"). It runs the
// same worker.js on any machine with Node 18+, a rented server or this Mac, keeping its records in one JSON file.
//
//   node server.mjs        settings come from the environment, or from link.env next to this file (see README):
//     DISCORD_CLIENT_ID      the Banners of the Deep app (default YOUR_DISCORD_CLIENT_ID)
//     DISCORD_CLIENT_SECRET  OAuth2 › Reset Secret (keep it in link.env, which is never shared)
//     REDIRECT_URI           this service's public address + /callback (Discord sends members back there)
//     FOUNDER_CUTOFF         the public launch date, ISO; empty = before launch
//     DISCORD_BOT_TOKEN      Bot › Reset Token (in link.env only): adds signed-in players to the community server
//     DISCORD_GUILD_ID       the community server (default: Banners of the Deep, 1563514591156375645)
//     GAME_TOKEN_SECRET      the game server's sign-in secret (in link.env only): /play signs browser players in
//     GAME_URLS              the game servers /play may send players back to, comma-separated; empty: /play is off
//     PORT                  default 8787;  HOST default 127.0.0.1 (put a web server with HTTPS in front)
//     DATA_FILE              default links.json next to this file
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import worker from './worker.js';

const here = path.dirname(fileURLToPath(import.meta.url));

// link.env: KEY=value lines, read before the environment so the environment wins
function loadEnvFile(file) {
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/);
    if (m && !line.trim().startsWith('#')) out[m[1]] = m[2].replace(/^"(.*)"$/, '$1');
  }
  return out;
}

// The store worker.js expects (get/put/delete, values as strings, optional expiry), kept in one JSON file and
// written whole on each change (atomically, readable only by this user). Small: one record per Discord account.
export function fileStore(file) {
  let data = {};
  try { data = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (err) { if (err.code !== 'ENOENT') throw err; }   // a file that can't be read is never started over (it holds every player)
  const save = () => {
    const tmp = file + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(data), { mode: 0o600 });
    fs.renameSync(tmp, file);
  };
  const live = k => { const e = data[k]; if (!e) return null; if (e.exp && Date.now() > e.exp) { delete data[k]; return null; } return e; };
  return {
    async get(k, type) { const e = live(k); return e ? (type === 'json' ? JSON.parse(e.v) : e.v) : null; },
    async put(k, v, opts = {}) { data[k] = { v: String(v), exp: opts.expirationTtl ? Date.now() + opts.expirationTtl * 1000 : 0 }; save(); },
    async delete(k) { delete data[k]; save(); },
  };
}

export function makeEnv(settings) {
  return {
    DISCORD_CLIENT_ID: settings.DISCORD_CLIENT_ID || 'YOUR_DISCORD_CLIENT_ID',
    DISCORD_CLIENT_SECRET: settings.DISCORD_CLIENT_SECRET || '',
    REDIRECT_URI: settings.REDIRECT_URI || '',
    FOUNDER_CUTOFF: settings.FOUNDER_CUTOFF || '',
    DISCORD_BOT_TOKEN: settings.DISCORD_BOT_TOKEN || '',
    DISCORD_GUILD_ID: settings.DISCORD_GUILD_ID || '1563514591156375645',
    GAME_TOKEN_SECRET: settings.GAME_TOKEN_SECRET || '',
    GAME_URLS: settings.GAME_URLS || '',
    LINKS: fileStore(settings.DATA_FILE || path.join(here, 'links.json')),
  };
}

export function serve(env, port, host) {
  const server = http.createServer(async (req, res) => {
    // any error here answers 400 and the service carries on (an unhandled one would end it, and the world with it)
    try {
      const chunks = [];
      let size = 0;
      for await (const c of req) { chunks.push(c); size += c.length; if (size > 65536) { res.writeHead(413).end(); return; } }
      // worker.js reads only the path and the query: the URL is built on a fixed base, never from the visitor's Host
      const request = new Request(new URL(req.url, 'http://link.local'), {
        method: req.method, headers: req.headers, body: ['GET', 'HEAD'].includes(req.method) ? undefined : Buffer.concat(chunks) });
      const response = await worker.fetch(request, env);
      const headers = {};
      response.headers.forEach((v, k) => { headers[k] = k === 'set-cookie' ? response.headers.getSetCookie() : v; });
      res.writeHead(response.status, headers);
      res.end(Buffer.from(await response.arrayBuffer()));
    } catch (err) {
      console.error(`link service: ${req.method} ${(req.url || '').split('?')[0]}: ${err.message}`);   // never the query or headers
      try { if (!res.headersSent) res.writeHead(400); res.end(); } catch (_) { /* the visitor is gone */ }
    }
  });
  server.requestTimeout = 15000;   // slow senders don't hold a request open
  server.headersTimeout = 10000;
  server.maxConnections = 256;
  return new Promise(ok => server.listen(port, host, () => ok(server)));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const settings = { ...loadEnvFile(path.join(here, 'link.env')), ...process.env };
  const env = makeEnv(settings);
  if (!env.DISCORD_CLIENT_SECRET || !env.REDIRECT_URI) console.warn('link service: DISCORD_CLIENT_SECRET or REDIRECT_URI is not set yet (README); members can\'t connect until both are.');
  const port = Number(settings.PORT || 8787), host = settings.HOST || '127.0.0.1';
  await serve(env, port, host);
  console.log(`Banners of the Deep link service on http://${host}:${port}`);
}
