// The chop hitch probe (rts-feel, 2026-10-25), injected into a test copy's page by tools/rts_feel/real_feel.py --only chop.
// On the notice CHOPGO|N|<grove tiles> (ZZChop.dm): every display frame's interval for 35 s, with what ran in it (the
// server's messages to the page, v3frame, the HUD's render functions, texture work, the WebGL uploads and shader
// compiles), while it orders all the units to chop (at 5 s) and, as they walk, half of them to a second grove (8.5 s)
// and the other half to a third (11.5 s). Sends the frames over 33 ms and the frame stats back as rm=chopres (chunks).
(function () {
  const RC = window.RFC = { rec: false, frames: [], cur: null, depth: 0, clicks: [], t0: 0, epoch0: 0 };
  const now = () => performance.now();
  function wrap(obj, name, label, bytes) {
    const o = obj && obj[name];
    if (typeof o !== 'function' || o.__rfc) return;
    const w = function () {
      if (!RC.rec || !RC.cur) return o.apply(this, arguments);
      const a = now(); RC.depth++;
      try { return o.apply(this, arguments); }
      finally {
        RC.depth--;
        const d = now() - a, c = RC.cur.calls[label] || (RC.cur.calls[label] = [0, 0, 0, 0]);
        c[0]++; c[1] += d; if (d > c[2]) c[2] = d;
        if (bytes && typeof arguments[0] === 'string') c[3] += arguments[0].length;
        if (RC.depth === 0) RC.cur.top += d;
      }
    };
    w.__rfc = 1; obj[name] = w;
  }
  function wrapAll() {
    ['updateHUD', 'update3D', 'move3D', 'gather3d', 'key3d', 'rmSlots3D', 'nearKey', 'rfCamTo'].forEach(n => wrap(window, n, n, true));
    ['v3frame', 'v3applyTerrain', 'v3tex', 'v3texFromCanvas', 'v3texUpload', 'toast'].forEach(n => wrap(window, n, n));
    Object.keys(window).filter(n => /^render[A-Z]/.test(n)).forEach(n => wrap(window, n, n));
    for (const P of [window.WebGLRenderingContext && WebGLRenderingContext.prototype, window.WebGL2RenderingContext && WebGL2RenderingContext.prototype])
      if (P) ['texImage2D', 'texSubImage2D', 'bufferData', 'bufferSubData', 'compileShader', 'linkProgram', 'generateMipmap'].forEach(n => wrap(P, n, 'gl.' + n));
  }
  function frame() {
    if (!RC.rec) return;
    const p = now(), f = RC.cur;
    f.dt = p - f.t; RC.frames.push(f);
    RC.cur = { t: p, calls: {}, top: 0 };
    if (p - RC.t0 < 35000) requestAnimationFrame(frame); else finish();
  }
  function pick(list, n) { return list.slice(0, n); }
  function finish() {
    RC.rec = false;
    const F = RC.frames, T = x => Math.round(x - RC.t0);
    const dts = F.map(f => f.dt).sort((a, b) => a - b), q = p => +(dts[Math.min(dts.length - 1, Math.floor(p * dts.length))] || 0).toFixed(1);
    const win = (a, b) => { const W = F.filter(f => f.t - RC.t0 >= a && f.t - RC.t0 < b); return { frames: W.length, over33: W.filter(f => f.dt > 33).length, over50: W.filter(f => f.dt > 50).length, over100: W.filter(f => f.dt > 100).length, worst: Math.round(Math.max(0, ...W.map(f => f.dt))) }; };
    const slow = F.filter(f => f.dt > 33).map(f => {
      const calls = Object.entries(f.calls).sort((a, b) => b[1][1] - a[1][1]).map(([k, c]) => [k, c[0], Math.round(c[1]), Math.round(c[2]), c[3]]);
      return [T(f.t), Math.round(f.dt), Math.round(f.top), pick(calls, 6)];
    });
    // what ran in the whole 35 s, for the totals
    const tot = {};
    for (const f of F) for (const [k, c] of Object.entries(f.calls)) { const t = tot[k] || (tot[k] = [0, 0, 0, 0]); t[0] += c[0]; t[1] += c[1]; if (c[2] > t[2]) t[2] = c[2]; t[3] += c[3]; }
    const out = { serial: RC.serial, epoch0: RC.epoch0, clicks: RC.clicks, frames: F.length, fps: +(F.length / 35).toFixed(1),
      p50: q(0.5), p95: q(0.95), p99: q(0.99), worst: Math.round(dts[dts.length - 1] || 0),
      idle: win(0, 5000), orders: win(5000, 15000), arriving: win(15000, 35000),
      totals: Object.fromEntries(Object.entries(tot).sort((a, b) => b[1][1] - a[1][1]).slice(0, 25).map(([k, t]) => [k, [t[0], Math.round(t[1]), Math.round(t[2]), t[3]]])),
      slow: pick(slow, 70), slowCount: slow.length };
    const s = JSON.stringify(out), n = Math.ceil(s.length / 3000);
    for (let i = 0; i < n; i++) setTimeout(() => send('chopres', `${RC.serial}|${i + 1}|${n}|` + s.slice(i * 3000, (i + 1) * 3000)), 60 * i);
  }
  function go(serial, groves) {
    if (RC.rec) return;
    wrapAll();
    RC.serial = serial; RC.frames = []; RC.clicks = []; RC.t0 = now(); RC.epoch0 = Date.now();
    RC.cur = { t: RC.t0, calls: {}, top: 0 }; RC.rec = true; requestAnimationFrame(frame);
    const G = groves.map(g => g.split(',').map(Number));
    const mine = () => arr(model.units).filter(u => u.z === V3.z).map(u => u.ref);
    const order = (refs, g, at) => {
      setTimeout(() => { RC.clicks.push(['select', Math.round(now() - RC.t0), refs.length]); send('selectmany', refs.join('|')); }, at);
      setTimeout(() => { RC.clicks.push(['chop', Math.round(now() - RC.t0), g[0], g[1]]); send('click3d', g[0] + '|' + g[1] + '||0|0'); }, at + 400);
    };
    const all = mine(), half = Math.ceil(all.length / 2);
    order(all, G[0], 5000);
    order(all.slice(0, half), G[1], 8500);
    order(all.slice(half), G[2], 11500);
  }
  const prev = window.updateHUD;
  window.updateHUD = function (raw) {
    prev(raw);
    try {
      const n = String(model && model.notice || '');
      if (n.startsWith('CHOPGO|') && n !== window.rfChopLast) {
        window.rfChopLast = n;
        const p = n.split('|');
        setTimeout(() => go(p[1], p[2].split(';')), 50);
      }
    } catch (e) { send('chopres', '0|1|1|' + JSON.stringify({ error: String(e) })); }
  };
})();
