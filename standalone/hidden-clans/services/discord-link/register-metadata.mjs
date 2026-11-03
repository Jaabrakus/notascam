#!/usr/bin/env node
// One-time setup: tell Discord which facts the Banners of the Deep app gives for Linked Roles (README step 5).
// Run with the bot token in the environment, never on the command line:
//   DISCORD_BOT_TOKEN=... node register-metadata.mjs          (read it from a prompt: see README)
const APP = process.env.DISCORD_CLIENT_ID || 'YOUR_DISCORD_CLIENT_ID';
const TOKEN = process.env.DISCORD_BOT_TOKEN;
if (!TOKEN) { console.error('Set DISCORD_BOT_TOKEN first (README step 5).'); process.exit(1); }
// type 7 = boolean_equal: "this fact must be true"
export const METADATA = [
  { key: 'played', name: 'Player', description: 'Has played Banners of the Deep', type: 7 },
  { key: 'founder', name: 'Founder', description: 'Played before the public launch', type: 7 },
];
const r = await fetch(`https://discord.com/api/v10/applications/${APP}/role-connections/metadata`, {
  method: 'PUT', headers: { Authorization: `Bot ${TOKEN}`, 'Content-Type': 'application/json' }, body: JSON.stringify(METADATA) });
console.log(r.ok ? 'Registered: Player and Founder.' : `Discord said ${r.status}: ${await r.text()}`);
process.exit(r.ok ? 0 : 1);
