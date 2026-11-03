// The real formations' layouts from the page's copy (fm_module.js fmRealPoints), the same cases and digests as
// tests/real_points_check.dm prints from the game's (Formations.dm RemasterRealPoints): the two must match line for line.
//   node tools/formations/real_points_node.js [fm_module.js]
'use strict';
const fs = require('fs'), vm = require('vm'), crypto = require('crypto'), path = require('path');
const file = process.argv[2] || path.join(__dirname, 'fm_module.js');
const text = fs.readFileSync(file, 'utf8').split('\n');
// just the layout's own functions (the module's page hooks need a browser): each from its first line to its last
const want = ['function fmSnap(', 'function fmSortBy(', 'function fmCellKey(', 'const FM_REAL=', 'function fmTake(', 'function fmRealRow(', 'function fmRealRows(', 'function fmRealPoints('];
const parts = [];
for (const w of want) {
  let i = text.findIndex(l => l.startsWith(w));
  if (i < 0) throw new Error('not in the module: ' + w);
  parts.push(text[i]);
  if (w === 'function fmRealPoints(') while (!text[i].includes('return cells.map(')) parts.push(text[++i]);
}
const ctx = {};
vm.createContext(ctx);
vm.runInContext(parts.join('\n') + '\n;this.fmRealPoints=fmRealPoints;this.FM_REAL=FM_REAL;', ctx);
const md5 = s => crypto.createHash('md5').update(s).digest('hex');
function counts(mix, n) {
  if (mix === 1) return {front: n};
  if (mix === 2) { const C = {front: 0, ranged: 0, mage: 0, any: 0}; for (let i = 0; i < n; i++) { const k = i % 20; C[k < 12 ? 'front' : k < 17 ? 'ranged' : k < 19 ? 'mage' : 'any']++ } return C }
  if (mix === 3) return {ranged: n};
  if (mix === 4) return {front: Math.floor(n / 3), ranged: Math.floor(n / 3), mage: n - 2 * Math.floor(n / 3)};
  if (mix === 6) return {mage: n};
  return {any: n};
}
const sizes = []; for (let n = 2; n <= 60; n++) sizes.push(n); sizes.push(75, 90, 91, 120, 150, 200);
const faces = [[0, 1], [1, 0], [0, -1], [-1, 0], [0.7071, 0.7071], [-0.7071, 0.7071], [0.3, 0.95], [0.95, -0.3]];
const all = []; let cases = 0;
for (const shape of ctx.FM_REAL) for (let mix = 1; mix <= 6; mix++) {
  const digest = [];
  for (const n of sizes) {
    const widths = [0]; if (['line', 'skirmish'].includes(shape) && (n === 30 || n === 60)) widths.push(5, 12);
    for (const F of faces) for (const w of widths) {
      digest.push(md5(ctx.fmRealPoints(shape, counts(mix, n), n, 100, 100, F[0], F[1], w).map(p => p[0] + ',' + p[1] + ',' + p[2]).join(';')));
      cases++;
    }
  }
  const d = md5(digest.join(';')); all.push(d);
  console.log(`${shape} mix ${mix} md5 ${d}`);
}
console.log(`all ${cases} layouts md5 ${md5(all.join(';'))}`);
