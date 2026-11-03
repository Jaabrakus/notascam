#!/usr/bin/env node
// Renders every sound in game/Interface/audio.js (the same synth code the HUD runs) to WAV and measures it:
// peak and short-term loudness, before and after the engine's per-sound gain, clipping, timing.
//   node tools/render_audio.js [outdir]      (default reports/polish-2026-10-22/audio/samples)
// Writes <outdir>/*.wav (first take of each sound, voices, music notes, a 40 s music-and-ambience demo) and
// <outdir>/levels.json. Exit status 1 when anything clips or a sound is silent.
'use strict';
const fs = require('fs'), path = require('path');
const BASE = path.resolve(__dirname, '..');
const S = require(path.join(BASE, 'game/Interface/audio.js'));
const out = path.resolve(process.argv[2] || path.join(BASE, 'reports/polish-2026-10-22/audio/samples'));
fs.mkdirSync(out, { recursive: true });
for (const f of fs.readdirSync(out)) if (f.endsWith('.wav')) fs.unlinkSync(path.join(out, f));

function wav(file, R, maxSec) {
  const ch = R.ch.length, n = Math.min(R.ch[0].length, Math.round((maxSec || 1e9) * R.sr));
  const b = Buffer.alloc(44 + n * ch * 2);
  b.write('RIFF', 0); b.writeUInt32LE(36 + n * ch * 2, 4); b.write('WAVE', 8); b.write('fmt ', 12);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(ch, 22); b.writeUInt32LE(R.sr, 24);
  b.writeUInt32LE(R.sr * ch * 2, 28); b.writeUInt16LE(ch * 2, 32); b.writeUInt16LE(16, 34); b.write('data', 36); b.writeUInt32LE(n * ch * 2, 40);
  let o = 44;
  for (let i = 0; i < n; i++) for (let c = 0; c < ch; c++) { const v = Math.max(-1, Math.min(1, R.ch[c][i])); b.writeInt16LE(Math.round(v * 32767), o); o += 2 }
  fs.writeFileSync(path.join(out, file), b);
}
const db = v => v > 0 ? Math.round(20 * Math.log10(v) * 10) / 10 : -120;
function measure(R) {
  let pk = 0, st = 0, sum = 0, cnt = 0;
  for (const a of R.ch) { pk = Math.max(pk, S.peakOf(a)); st = Math.max(st, S.stRMS(a, R.sr)); for (const x of a) sum += x * x; cnt += a.length }
  return { peak: db(pk), loud: db(st), rms: db(Math.sqrt(sum / Math.max(1, cnt))), sec: Math.round(R.ch[0].length / R.sr * 100) / 100, nan: R.ch.some(a => a.some(x => !isFinite(x))) };
}
const rows = [], problems = [];
function check(name, R, gain, cat, ms) {
  const m = measure(R); m.name = name; m.cat = cat; m.ms = Math.round(ms * 10) / 10;
  m.mix = Math.round((m.loud + 20 * Math.log10(gain || 1)) * 10) / 10;   // loudness after the engine's per-sound gain
  if (m.nan) problems.push(name + ': NaN/Infinity');
  if (m.peak > -0.9) problems.push(name + ': clips (' + m.peak + ' dBFS)');
  if (m.loud < -50) problems.push(name + ': silent (' + m.loud + ' dBFS)');
  rows.push(m); return m;
}
const t0 = Date.now();
for (const name in S.SND) {
  const d = S.SND[name];
  for (let v = 0; v < d.vars; v++) {
    const a = process.hrtime.bigint(); const R = S.render(name, v); const ms = Number(process.hrtime.bigint() - a) / 1e6;
    check(name + (d.vars > 1 ? '#' + v : ''), R, d.gain, d.cat, ms);
    if (v === 0) wav(name + '.wav', R, d.loop ? 4 : 6);
  }
}
const races = ['Human', 'Dwarf', 'Elf', 'Orc', 'Goblin', 'Kobold', 'Lizardman', 'Frogman', 'Zombie', 'Vampire', 'Skeleton', 'Dragon', 'Spider'];
const kinds = Object.keys(S.VPLAN);
for (const race of races) for (const kind of kinds) for (const g of (['Skeleton', 'Spider', 'Dragon'].includes(race) ? ['m'] : ['m', 'f'])) for (let v = 0; v < 4; v++) {
  const a = process.hrtime.bigint(); const R = S.renderVoice(race, g, kind, v); const ms = Number(process.hrtime.bigint() - a) / 1e6;
  check('vo.' + race.toLowerCase() + '.' + g + '.' + kind + '#' + v, R, 0.9, 'vo', ms);
  if (v === 0 && (g === 'm' || ['select', 'move', 'attack'].includes(kind))) wav('vo-' + race.toLowerCase() + '-' + g + '-' + kind + '.wav', R);
}
// music: instrument notes and a short demo phrase, mixed offline the way the engine schedules them
const inst = [['lute', [62]], ['lute', [74]], ['harp', [57]], ['harp', [69]], ['flute', [74, 1]], ['pad', [[50, 53, 57], 6]], ['drone', [38, 8]]];
for (const [k, args] of inst) { const a = process.hrtime.bigint(); const R = S.renderInst(k, args); const ms = Number(process.hrtime.bigint() - a) / 1e6; check('mus.' + k + JSON.stringify(args), R, 1, 'mus', ms); wav('mus-' + k + '-' + JSON.stringify(args).replace(/[^0-9]+/g, '_') + '.wav', R) }
{
  const sr = 32000, L = 40, mixd = [new Float32Array(L * sr), new Float32Array(L * sr)];
  const add = (R, at, g, pan) => { const s = Math.round(at * sr); for (let c = 0; c < 2; c++) { const src = R.ch[Math.min(c, R.ch.length - 1)], pg = R.ch.length > 1 ? 1 : (c ? Math.sqrt(0.5 + pan / 2) : Math.sqrt(0.5 - pan / 2)); for (let i = 0; i < src.length && s + i < mixd[c].length; i++) mixd[c][s + i] += src[i] * g * pg } };
  const beat = 60 / 66, bar = beat * 4, root = 62, prog = [[0, 3, 7], [-2, 2, 5], [0, 3, 7], [5, 9, 12]];
  for (let b = 0; b < 8; b++) {
    const at = 1 + b * bar, ch = prog[b % 4], amp = Math.min(1, (b + 1) / 2) * (b === 7 ? 0.7 : 1);
    if (b % 2 === 0) add(S.renderInst('pad', [ch.map(x => root + x - 12), bar * 2 + 1.5]), at, 0.5 * amp, 0);
    const pat = [0, 1, 2, 1, 0, 1, 2, 1];
    pat.forEach((i, k) => add(S.renderInst('lute', [root + ch[i]]), at + k * beat / 2, (k % 2 ? 0.28 : 0.36) * amp, (k % 3 - 1) * 0.3));
    if (b === 3 || b === 5) [[2, 1], [3, 0.5], [4, 1.5], [2, 1]].reduce((tt, [deg, d]) => { add(S.renderInst('flute', [root + 12 + [0, 2, 3, 5, 7, 9, 10][deg], d * beat]), tt, 0.22 * amp, 0.1); return tt + d * beat }, at + beat);
  }
  // music at its default volume (35) over ambience at its default (50), both through the engine's square-law curve
  const mus = 0.35 * 0.35, amb = 0.5 * 0.5;
  for (const c of mixd) for (let i = 0; i < c.length; i++) c[i] *= mus;
  const wind = S.render('bed.wind', 0), leaves = S.render('bed.leaves', 0);
  for (const [R, g] of [[wind, 0.55 * 0.5], [leaves, 0.6 * 0.4]]) for (let c = 0; c < 2; c++) { const s = R.ch[c]; for (let i = 0; i < mixd[c].length; i++) mixd[c][i] += s[Math.floor(i * R.sr / sr) % s.length] * g * amb }
  const R = { sr, ch: mixd }; check('demo.music+ambience', R, 1, 'mus', 0);   // levels only: mix-scene.wav (tools/check_audio_mix.py) is the one to hear
}
// a 30 s scene at the default volumes: ambience, a dwarf selected and sent off, chopping, the Sound panel, a skirmish
// with war drums, a level-up, music over it all (offline: no reverb, which the engine adds)
{
  const sr = 44100, L = 30, mixd = [new Float32Array(L * sr), new Float32Array(L * sr)];
  const vol = { fx: 0.8, ui: 0.55, vo: 0.75, amb: 0.5, mus: 0.35 }, master = 0.7 * 0.7;
  const add = (R, at, g, pan) => { pan = pan || 0; const s = Math.round(at * sr), ratio = R.sr / sr; for (let c = 0; c < 2; c++) { const src = R.ch[Math.min(c, R.ch.length - 1)], pg = R.ch.length > 1 ? 1 : (c ? Math.sqrt(0.5 + pan / 2) : Math.sqrt(0.5 - pan / 2)); const n = Math.floor(src.length / ratio); for (let i = 0; i < n && s + i < mixd[c].length; i++) mixd[c][s + i] += src[Math.floor(i * ratio)] * g * pg } };
  const snd = (name, at, g, pan, v) => { const d = S.SND[name]; add(S.render(name, v || 0), at, d.gain * (g || 1) * vol[d.cat] * vol[d.cat], pan) };
  const vo = (race, kind, at, g, pan, v) => add(S.renderVoice(race, 'm', kind, v || 0), at, 0.9 * (g || 1) * vol.vo * vol.vo, pan);
  for (const [name, g] of [['bed.wind', 0.6], ['bed.leaves', 0.6], ['bed.insects', 0.3]]) { const R = S.render(name, 0), loopN = R.ch[0].length; const RR = { sr: R.sr, ch: R.ch.map(a => { const o = new Float32Array(Math.ceil(L * R.sr)); for (let i = 0; i < o.length; i++) o[i] = a[i % loopN]; return o }) }; add(RR, 0, S.SND[name].gain * g * vol.amb * vol.amb) }
  [[2.5, -0.6, 0], [9.5, 0.5, 1], [17, -0.3, 2], [25, 0.6, 3]].forEach(([t, pan, v]) => snd('bird.song', t, 0.9 * 0.5, pan, v));
  snd('ui.click', 1.0); vo('Dwarf', 'select', 1.05);
  snd('cmd.work', 2.2); vo('Dwarf', 'work', 2.25);
  for (let k = 0; k < 6; k++) snd('chop', 3.4 + k * 0.95, 0.7, 0.25, k % 5);
  snd('tree.fall', 9.2, 0.75, 0.25);
  snd('ui.open', 11.0); snd('ui.tab', 11.8); snd('ui.hover', 12.3); snd('ui.hover', 12.6, 1, 0, 1); snd('ui.close', 13.2);
  snd('ui.click', 14.0); vo('Orc', 'select', 14.05); snd('cmd.attack', 14.8); vo('Orc', 'attack', 14.85);
  const fight = [['swing.heavy', 'hit.flesh'], ['swing.light', 'parry'], ['swing.heavy', 'hit.armor'], ['swing.light', 'hit.flesh'], ['swing.heavy', 'block'], ['swing.light', 'hit.big']];
  fight.forEach(([sw, hit], k) => { const t = 16 + k * 0.62, pan = (k % 2 ? 0.3 : -0.2); snd(sw, t, 0.8, pan, k % 4); snd(hit, t + 0.07, 0.8, pan, k % 3) });
  snd('hit.flesh', 19.9, 0.8, 0.3); snd('death.fall', 20.05, 0.8, 0.3); vo('Human', 'death', 20.1, 0.7, 0.3);
  for (let k = 0; k < 32; k++) { const D = [['drum.taiko', 1], null, ['drum.frame', 0.5], ['drum.frame', 0.35], ['drum.taiko', 0.8], ['drum.frame', 0.5], null, ['drum.frame', 0.6]][k % 8]; if (D) snd(D[0], 16 + k * 60 / 96 / 2, D[1] * Math.min(1, (32 - k) / 10), 0, k % 3) }
  snd('ui.levelup', 23.5);
  const beat = 60 / 68, bar = beat * 4, root = 62, prog = [[0, 3, 7], [-2, 2, 5], [0, 3, 7], [5, 9, 12]], mg = vol.mus * vol.mus;
  for (let b = 0; b < 7; b++) { const at = 2 + b * bar, ch = prog[b % 4], amp = Math.min(1, (b + 1) / 2) * (b === 6 ? 0.7 : 1);
    if (b % 2 === 0) add(S.renderInst('pad', [ch.map(x => root + x - 12), bar * 2 + 1.5]), at, 0.5 * amp * mg, 0);
    [0, 1, 2, 1, 0, 1, 2, 1].forEach((i, k) => add(S.renderInst('lute', [root + ch[i]]), at + k * beat / 2, (k % 2 ? 0.28 : 0.36) * amp * mg, (k % 3 - 1) * 0.3)) }
  for (const c of mixd) for (let i = 0; i < c.length; i++) c[i] = Math.tanh(c[i] * master * 1.4) / 1.4;   // a soft stand-in for the engine's compressor
  const R = { sr, ch: mixd }; check('demo.scene', R, 1, 'mus', 0);   // levels only, as above
}
// loudness spread inside each category (after per-sound gain), first takes only
const cats = {};
for (const r of rows) { if (/#[1-9]$/.test(r.name) || r.name.startsWith('demo')) continue; (cats[r.cat] = cats[r.cat] || []).push(r.mix) }
const spread = {}; for (const c in cats) { const a = cats[c].sort((x, y) => x - y); spread[c] = { n: a.length, min: a[0], median: a[Math.floor(a.length / 2)], max: a[a.length - 1] } }
const slow = rows.filter(r => r.ms > 60).map(r => r.name + ' ' + r.ms + ' ms');
const result = { passed: problems.length === 0, rendered: rows.length, seconds: (Date.now() - t0) / 1000, problems, spread, slow, rows };
fs.writeFileSync(path.join(out, 'levels.json'), JSON.stringify(result, null, 1) + '\n');
console.log(JSON.stringify({ passed: result.passed, rendered: result.rendered, seconds: result.seconds, problems: problems.slice(0, 20), spread, slow: slow.slice(0, 20) }, null, 1));
process.exit(result.passed ? 0 : 1);
