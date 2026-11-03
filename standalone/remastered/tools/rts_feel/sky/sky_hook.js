// The sky job's page probe (rts-feel, 2026-10-25), injected into a test copy's page by tools/rts_feel/real_feel.py --only
// sky. On the notice SKYPROBE|N|x,y (ZZSky.dm: the flyers' middle): the level the view shows, whether the HUD says the
// Sky is yours, the level row's Sky button (shown, and where on screen), an open-sky spot to click a few tiles off the
// flyers (where the pick says sky and no HUD covers it), the last pings and the notice. Sent back as rm=skyprobe.
(function () {
  // every ping drawn (they go 0.72 s after: RF.pings is refiltered each frame), by kind, in order
  const seen = new WeakSet(), log = window.skyPings = [];
  (function watch() { try { for (const p of RF.pings || []) if (!seen.has(p)) { seen.add(p); log.push(p.k); if (log.length > 40) log.shift() } } catch (e) {} requestAnimationFrame(watch) })();
  // what the page sends the game that matters here (clicks, level changes), with when
  const sends = window.skySends = [], s0 = window.send;
  window.send = function (a, v) { if (a === 'click3d' || a === 'layer' || a === 'box3d' || a === 'flylevel') { sends.push([Math.round(performance.now()), a, String(v)]); if (sends.length > 30) sends.shift() } return s0.apply(this, arguments) };
  function vis(e) { if (!e || e.hidden) return null; const b = e.getBoundingClientRect(); return b.width > 2 && b.height > 2 ? [Math.round(b.x + b.width / 2), Math.round(b.y + b.height / 2)] : null }
  function probe(serial, fx, fy) {
    const z = (() => { const w = document.documentElement.getBoundingClientRect().width; return w ? w / innerWidth : 1 })();
    const out = { serial, w: innerWidth * z, h: innerHeight * z, v3z: V3.z, sky: !!(model && model.sky), notice: String(model && model.notice || ''),
      skyBtn: null, skyShown: false, spot: null, pings: log.slice(-8), tag: ($('tag3d') && !$('tag3d').hidden) ? $('tag3d').textContent : '',
      sends: sends.slice(-10), notes: notes.slice(-6), cam: [+V3.cx.toFixed(2), +V3.cy.toFixed(2), +V3.tcx.toFixed(2), +V3.tcy.toFixed(2)], at: Math.round(performance.now()) };
    const b = document.querySelector('#layers button[data-value="3"]'); out.skyShown = !!(b && !b.hidden); out.skyBtn = vis(b);
    if (V3.on && V3.vp && V3.z === 3) {
      const c = $('world3d'), r = c.getBoundingClientRect();
      // a few tiles off the camera's own target (where the view looks: never off screen), nearest first
      const cx = Math.round(V3.tcx), cy = Math.round(V3.tcy), cand = [];
      for (let dx = -8; dx <= 8; dx++) for (let dy = -6; dy <= 6; dy++) if (Math.max(Math.abs(dx), Math.abs(dy)) >= 3) cand.push([dx, dy]);
      cand.sort((a, b) => Math.hypot(a[0], a[1]) - Math.hypot(b[0], b[1]));
      for (const [dx, dy] of cand) {
        const x = cx + dx, y = cy + dy, K = v3kindAt(x, y); if (K && K.kind !== 'void') continue;
        if (Math.max(Math.abs(x - fx), Math.abs(y - fy)) < 3) continue;   // not on the flyers themselves
        const p = v3project([x, 0.02, -y]); if (!p) continue;
        const t = v3pickTile(p[0], p[1]); if (!t || !t.sky || t.x !== x || t.y !== y || v3pickThing(p[0], p[1])) continue;
        const X = Math.round(r.left + p[0]), Y = Math.round(r.top + p[1]), e = document.elementFromPoint(X, Y);
        if (!(e === c || e && e.closest && e.closest('#world3d'))) continue;
        out.spot = [X, Y, x, y]; break
      }
    }
    send('skyprobe', JSON.stringify(out))
  }
  const notes = window.skyNotes = [];   // the game's notices, in order (a probe's own notice replaces the one before it)
  const prev = window.updateHUD;
  window.updateHUD = function (raw) {
    prev(raw);
    try {
      const n = String(model && model.notice || '');
      if (n && !n.startsWith('SKYPROBE|') && notes[notes.length - 1] !== n) { notes.push(n); if (notes.length > 12) notes.shift() }
      if (n.startsWith('SKYPROBE|') && n !== window.skyLast) { window.skyLast = n; const p = n.split('|'), xy = p[2].split(',').map(Number); setTimeout(() => probe(p[1], xy[0], xy[1]), 400) }
    } catch (e) { send('skyprobe', JSON.stringify({ error: String(e) })) }
  };
})();
