#!/usr/bin/env python3
"""Builds Kin & Stone's recorded sounds into game/Interface/sounds/ (the server sends every .m4a there with the HUD page,
Audio.dm; Interface/audio.js plays them):
  - our war drum kit, snd-wd.<drum>-<n>.m4a: giant drums, bass drums, hand drums, timpani, a roll, cymbal and gong from VSCO 2
    (CC0), which audio.js plays as battle drums (its own patterns, live, heavier as the fight grows);
  - the ambience bed, amb-forest.m4a: the user's "forest dungeon2.mp3", cut to a seamless loop on its beat;
  - CREDITS.md.
    python3 tools/build_audio_assets.py <downloads-dir> [<out-dir>] [--fx] [--ui] [--music]
<downloads-dir> holds the packs as fetched: vsco/files (VSCO 2 Community Edition subset), user/ (the user's own finds), and for
the optional sets weapons/x1,x2 (OpenGameArt "Medieval sound effects - Weapon impacts"), kenney-rpg/x, kenney-impact/x, music/.
--fx adds recorded effects, --ui interface sounds and stingers, --music music tracks: all tried on 2026-10-23 and turned down
by the user (the game plays its original WAVs for fights), kept here in case.
Decoding and encoding use macOS afconvert; processing is numpy."""
import re, shutil, subprocess, sys, tempfile, wave
from pathlib import Path
import numpy as np

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
WITH_FX, WITH_UI, WITH_MUSIC = '--fx' in sys.argv, '--ui' in sys.argv, '--music' in sys.argv
SRC = Path(ARGS[0])
OUT = Path(ARGS[1]) if len(ARGS) > 1 else Path(__file__).resolve().parents[1]/'game/Interface/sounds'
SR = 48000
TMP = Path(tempfile.mkdtemp(prefix='kas-'))


def load(path, sr=SR, mono=True):
    """Any file afconvert reads (wav, mp3, flac, ogg) -> float32 array [n] or [n,2]."""
    out = TMP/'dec.wav'
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', f'LEI16@{sr}', '-c', '1' if mono else '2', str(path), str(out)], check=True, capture_output=True)
    with open(out, 'rb') as f: data = f.read()
    # find the data chunk ourselves (afconvert may write a WAVE_FORMAT_EXTENSIBLE header)
    i = data.find(b'data'); n = int.from_bytes(data[i+4:i+8], 'little')
    a = np.frombuffer(data[i+8:i+8+n], dtype='<i2').astype(np.float32) / 32768
    return a if mono else a.reshape(-1, 2)


def save_m4a(a, name, sr=SR, kbps=96):
    a = np.clip(a, -1, 1)
    ch = 1 if a.ndim == 1 else a.shape[1]
    w = TMP/'enc.wav'
    with wave.open(str(w), 'wb') as f:
        f.setnchannels(ch); f.setsampwidth(2); f.setframerate(sr); f.writeframes((a * 32767).astype('<i2').tobytes())
    dst = OUT/name; dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', str(kbps * 1000), str(w), str(dst)], check=True, capture_output=True)
    return dst


def env(a, ms=5):
    k = max(1, int(SR * ms / 1000)); return np.convolve(np.abs(a), np.ones(k) / k, mode='same')


def st_rms(a):
    w = int(0.05 * SR); x = a if a.ndim == 1 else a.mean(1)
    if len(x) < w: return float(np.sqrt((x ** 2).mean()) + 1e-9)
    c = np.convolve(x ** 2, np.ones(w) / w, mode='valid'); return float(np.sqrt(c.max()) + 1e-9)


def finish(a, lvl=0.7, fade_out=0.03):
    """Trim silence, even loudness (lvl 1 = -12 dBFS short-term RMS, as the synth), peaks under -1 dBFS."""
    e = env(a); top = e.max() + 1e-9
    on = np.argmax(e > top * 0.02); off = len(e) - np.argmax(e[::-1] > top * 0.003)
    a = a[max(0, on - int(0.004 * SR)):off].copy()
    g = 0.25 * lvl / st_rms(a); pk = np.abs(a).max()
    if pk * g > 0.89: g = 0.89 / pk
    a *= g
    n = min(len(a), int(fade_out * SR)); a[-n:] *= np.linspace(1, 0, n)
    return a


def slices(a, max_len=1.6, floor_db=-32, ring_db=-58):
    """Split a take with several hits into the hits: a hit starts where the level jumps above floor_db (from the take's
    loudest), and runs on through its ring until it fades under ring_db for 80 ms, or the next hit starts."""
    e = env(a, 3); top = e.max(); thr = top * 10 ** (floor_db / 20); low = top * 10 ** (ring_db / 20)
    hits, i, n, q = [], 0, len(a), int(0.08 * SR)
    while i < n:
        j = np.argmax(e[i:] > thr)
        if e[i + j] <= thr: break
        s = i + j; k = s + int(0.02 * SR); quiet = 0; dipped = False
        while k < n and k - s < max_len * SR:
            if e[k] < thr * 0.3: dipped = True
            if dipped and e[k] > thr: break           # the next hit
            quiet = quiet + 1 if e[k] < low else 0
            if quiet > q: break
            k += 1
        hits.append(a[max(0, s - int(0.003 * SR)):k]); i = k
    return hits


manifest = {'sounds': {}, 'music': {}}
credits = {}


def put(name, arrays, lvl=0.7, kbps=96, credit=None):
    if name.startswith(('ui.', 'cmd.', 'drum.')):
        if not WITH_UI: return
    elif not name.startswith('wd.') and not WITH_FX: return
    files = []
    for k, a in enumerate(arrays):
        a = finish(a, lvl)
        f = f'snd-{name}-{k}.m4a'; save_m4a(a, f, kbps=kbps); files.append(f)
    manifest['sounds'][name] = files
    for c in ([credit] if isinstance(credit, str) else credit or []): credits.setdefault(c, []).append(name)
    print(f'{name}: {len(files)} takes')


def pitch(a, semis):
    """Lower (or raise) a recording by resampling: heavier and slower down, lighter up."""
    if not semis: return a
    r = 2 ** (semis / 12); idx = np.arange(0, len(a) - 1, r); return np.interp(idx, np.arange(len(a)), a).astype(np.float32)


def find(pack, pattern):
    return sorted(p for p in (SRC/pack).rglob('*') if p.is_file() and re.search(pattern, p.name))


OGA_W = 'Medieval sound effects - Weapon impacts, Ben Jaszczak & Brian Nelson (OpenGameArt, CC0)'
KEN_R = 'RPG Audio, Kenney (kenney.nl, CC0)'
KEN_I = 'Impact Sounds, Kenney (kenney.nl, CC0)'
VSCO = 'VSCO 2 Community Edition, Versilian Studios (CC0)'

# --- combat: real steel, sliced from the clash takes; the best (loudest, cleanest) hits of each kind ---
def best_hits(pattern, n, max_len=1.1):
    pool = []
    for f in find('weapons', pattern):
        for h in slices(load(f), max_len=max_len):
            if len(h) > 0.12 * SR: pool.append((np.abs(h).max() / (st_rms(h) + 1e-9), st_rms(h), h))
    pool.sort(key=lambda x: -(x[1] * min(1.0, len(x[2]) / (0.6 * SR))))   # loud ones that ring on first
    return [h for _, _, h in pool[:n]]
put('parry', best_hits(r'(Norse Sword|Sabre|Katana|Seax|Dagger).*Blade on Blade', 8), 0.75, credit=OGA_W)
put('block', best_hits(r'Haft on (Haft|Blade)|Blade on Haft', 6), 0.75, credit=OGA_W)
put('hit.armor', best_hits(r'^Mace .*Blade', 6, 0.8), 0.72, credit=OGA_W)
put('cmd.attack', [load(f) for f in find('kenney-rpg', r'^drawKnife\d')], 0.55, credit=KEN_R)

# --- bodies, wood, stone and goods (Kenney) ---
put('hit.flesh', [load(f) for f in find('kenney-impact', r'impactPunch_(heavy|medium)_00[0-3]')], 0.72, credit=KEN_I)
put('hit.big', [load(f) for f in find('kenney-impact', r'impactPunch_heavy_00[0-4]')], 0.82, credit=KEN_I)
put('death.fall', [load(f) for f in find('kenney-impact', r'impactSoft_medium_00[0-4]')], 0.75, credit=KEN_I)
put('arrow.hit', [load(f) for f in find('kenney-impact', r'impactWood_medium_00[0-3]|impactPlank_medium_00[0-1]')], 0.6, credit=KEN_I)
put('chop', [load(f) for f in find('kenney-rpg', r'^chop\.ogg')] + [load(f) for f in find('kenney-impact', r'impactWood_heavy_00[0-4]')], 0.65, credit=KEN_R)
put('mine', [load(f) for f in find('kenney-impact', r'impactMining_00[0-4]')], 0.65, credit=KEN_I)
put('mine.ore', [load(f) for f in find('kenney-impact', r'impactMetal_light_00[0-3]')], 0.62, credit=KEN_I)
put('build', [load(f) for f in find('kenney-impact', r'impactPlank_medium_00[0-4]')], 0.62, credit=KEN_I)
put('built', [load(f) for f in find('kenney-impact', r'impactWood_heavy_00[0-2]')], 0.6, credit=KEN_I)
put('built.wood', [load(f) for f in find('kenney-impact', r'impactPlank_medium_00[2-4]')], 0.6, credit=KEN_I)
put('craft.anvil', [load(f) for f in find('kenney-impact', r'impactMetal_heavy_00[0-4]')], 0.62, credit=KEN_I)
put('craft.tinker', [load(f) for f in find('kenney-impact', r'impactTin_medium_00[0-3]')], 0.55, credit=KEN_I)
put('dig', [load(f) for f in find('kenney-impact', r'footstep_snow_00[0-3]')], 0.6, credit=KEN_I)
put('door', [load(f) for f in find('kenney-rpg', r'^door(Open|Close)_\d')], 0.55, credit=KEN_R)
put('drop', [load(f) for f in find('kenney-rpg', r'^dropLeather|^bookPlace\d')], 0.55, credit=KEN_R)
put('pickup', [load(f) for f in find('kenney-rpg', r'^handleSmallLeather|^clothBelt')], 0.5, credit=KEN_R)
put('ui.coins', [load(f) for f in find('kenney-rpg', r'^handleCoins')], 0.5, credit=KEN_R)
put('ui.equip', [load(f) for f in find('kenney-rpg', r'^beltHandle|^metalClick')], 0.5, credit=KEN_R)
put('ui.bagpick', [load(f) for f in find('kenney-rpg', r'^handleSmallLeather')], 0.45, credit=KEN_R)
put('ui.bagdrop', [load(f) for f in find('kenney-rpg', r'^dropLeather')], 0.45, credit=KEN_R)
put('ui.open', [load(f) for f in find('kenney-rpg', r'^bookOpen')], 0.55, credit=KEN_R)
put('ui.close', [load(f) for f in find('kenney-rpg', r'^bookClose')], 0.5, credit=KEN_R)
put('ui.tab', [load(f) for f in find('kenney-rpg', r'^bookFlip\d')], 0.5, credit=KEN_R)
put('ui.place', [load(f) for f in find('kenney-impact', r'impactWood_medium_00[0-2]')], 0.55, credit=KEN_I)


# --- composites: several recordings layered (and slowed for weight) where no one take is the thing ---
def layer(parts, length):
    """parts: (start s, recording, gain, semitones)."""
    out = np.zeros(int(length * SR), np.float32)
    for t, a, g, s in parts:
        a = pitch(a, s); i = int(t * SR); e = min(len(out), i + len(a)); out[i:e] += a[:e - i] * g
    return out


K = lambda pack, pat: [load(f) for f in find(pack, pat)]
wood_h, soft_h, mining = K('kenney-impact', r'impactWood_heavy'), K('kenney-impact', r'impactSoft_heavy'), K('kenney-impact', r'impactMining')
punch_h, plank, creak = K('kenney-impact', r'impactPunch_heavy'), K('kenney-impact', r'impactPlank_medium'), K('kenney-rpg', r'^creak\d')
put('ko', soft_h[:4], 0.7, credit=KEN_I)
# a tree: the trunk creaks and gives, then lands with a heavy, bouncing thud
put('tree.fall', [layer([(0, creak[k], 0.9, -4), (0.55, creak[(k + 1) % 3], 0.7, -6), (1.25, wood_h[k], 1.0, -5), (1.27, soft_h[k], 0.9, -8),
                         (1.55, wood_h[k + 2], 0.45, -3), (1.75, plank[k], 0.3, -2)], 3.0) for k in range(3)], 0.75, credit=[KEN_R, KEN_I])
# a rock or ore lump splitting off: pick strikes running into a crumble
put('rock.break', [layer([(0, mining[k], 1.0, -2), (0.07, mining[(k + 2) % 5], 0.8, -4), (0.16, mining[(k + 4) % 5], 0.6, -6),
                          (0.02, soft_h[k], 0.6, -7)], 1.4) for k in range(3)], 0.75, credit=KEN_I)
put('siege.launch', [layer([(0, creak[k], 0.8, -5), (0.3, wood_h[k], 1.0, -7), (0.32, plank[k], 0.5, -3)], 1.6) for k in range(2)], 0.7, credit=[KEN_R, KEN_I])
put('siege.impact', [layer([(0, mining[k], 1.0, -5), (0.01, soft_h[k], 1.0, -9), (0.03, wood_h[k], 0.7, -4), (0.12, mining[k + 1], 0.5, -7)], 1.8) for k in range(3)], 0.85, credit=KEN_I)
put('ram.hit', [layer([(0, wood_h[k], 1.0, -6), (0.0, plank[k], 0.6, -4), (0.01, soft_h[k], 0.8, -7)], 1.4) for k in range(3)], 0.8, credit=KEN_I)
put('slam', [layer([(0, soft_h[k], 1.0, -7), (0.0, punch_h[k], 0.8, -6), (0.02, mining[k], 0.5, -6)], 1.4) for k in range(3)], 0.85, credit=KEN_I)
put('spell.frost', [layer([(0, g, 1.0, 0)], 1.2) for g in K('kenney-impact', r'impactGlass_(light|medium)_00[0-1]')], 0.6, credit=KEN_I)


# --- orchestra: stingers composed from the VSCO notes (pitch moved by resampling where a note is missing) ---
def note(pattern, semis=0.0, dur=None, att=0.0):
    f = find('vsco', pattern)[0]; a = load(f)
    if semis:
        r = 2 ** (semis / 12); idx = np.arange(0, len(a) - 1, r); a = np.interp(idx, np.arange(len(a)), a).astype(np.float32)
    if dur:
        a = a[:int(dur * SR)].copy(); n = min(len(a), int(0.3 * SR)); a[-n:] *= np.linspace(1, 0, n) ** 2   # a cut note fades, never clips off
    if att:
        n = int(att * SR); a[:n] *= np.linspace(0, 1, n)
    return a


def mixdown(parts, length):
    out = np.zeros(int(length * SR), np.float32)
    for t, a, g in parts:
        s = int(t * SR); e = min(len(out), s + len(a)); out[s:e] += a[:e - s] * g
    return out


def tail(a, sec):
    n = min(len(a), int(sec * SR)); a = a.copy(); a[-n:] *= np.linspace(1, 0, n) ** 2; return a


harp = {k: f'KSHarp_{k}_mf' for k in ['A2', 'E3', 'A4', 'C5', 'E5']}
# level-up: a rising harp run through A major (C5 -> C#5 by a semitone) with a glockenspiel glissando on top
run = [('A2', 0), ('E3', 0), ('A4', -5), ('A4', 0), ('C5', 1), ('E5', 0), ('A4', 12), ('C5', 13)]
lv = mixdown([(k * 0.07, note(harp[n], s, 2.2), 0.8) for k, (n, s) in enumerate(run)] + [(0.18, note(r'glock_fx_up_chromatic_slow_01', 0, 2.0), 0.35)], 3.0)
put('ui.levelup', [tail(lv, 1.0)], 0.55, credit=VSCO)
# a birth: three soft harp notes
put('ui.birth', [tail(mixdown([(0, note(harp['E5'], 0, 1.8), 0.8), (0.16, note(harp['C5'], 1, 1.8), 0.7), (0.32, note(harp['A4'], 0, 2.2), 0.8)], 2.6), 0.8)], 0.45, credit=VSCO)
# milestone: a horn call (D-A-D) over a timpani hit and a crash
hornD2, hornA2 = r'MOHorn_sus_D2_v3', r'MOHorn_sus_A2_v3'
ms = mixdown([(0, note(hornD2, 0, 0.5, 0.02), 0.9), (0.45, note(hornA2, 0, 0.45, 0.02), 0.9), (0.9, note(hornD2, 12, 1.6, 0.03), 0.8),
              (0.9, note(r'Timpani2_Hit_v3', 0, 2.0), 0.7), (0.9, note(r'crash_hit_ff_loose', 0, 2.5), 0.35)], 3.2)
put('ui.milestone', [tail(ms, 0.9)], 0.6, credit=VSCO)
# alert (raiders): a low war horn twice, with giant drum hits and a timpani roll
al = mixdown([(0, note(hornD2, -5, 1.2, 0.12), 1.0), (1.25, note(hornD2, 0, 1.6, 0.1), 1.0), (0, note(r'EthnicLargeMallet_hit_ff_1', 0, 1.5), 0.9),
              (1.25, note(r'EthnicLargeMallet_hit_ff_2', 0, 1.5), 0.9), (1.9, note(r'EthnicLargeMallet_hit_f_1', 0, 1.5), 0.8), (0.4, note(r'Timpani2_Roll_v5', 0, 2.5, 0.6), 0.4)], 3.6)
put('ui.alert', [tail(al, 0.8)], 0.65, credit=VSCO)
# arrival: a timpani roll swelling into an open horn fifth and a soft bell
ar = mixdown([(0, note(r'Timpani2_Roll_v5', 0, 2.2, 1.2), 0.7), (1.6, note(hornD2, 0, 2.6, 0.6), 0.75), (1.75, note(hornA2, 0, 2.4, 0.6), 0.6),
              (2.1, note(r'fx1_short_r02_main', 0, 2.0), 0.3)], 4.6)
put('ui.arrive', [tail(ar, 1.5)], 0.5, credit=VSCO)
# notifications, a death toll, the dawn bell, holy magic
put('ui.notify', [note(r'fx1_short_r01_main', 0, 1.6), note(r'glock_medium_C6', 0, 1.4)], 0.42, credit=VSCO)
put('ui.warn', [tail(note(r'gong_hit_ff', 0, 3.5), 1.5)], 0.5, credit=VSCO)
put('bell.village', [tail(mixdown([(0, note(r'fx1_short_r02_main', 0, 2.5), 1), (1.3, note(r'fx1_short_r02_main', -2, 2.5), 0.9), (2.6, note(r'fx1_short_r02_main', 0, 3), 0.9)], 5.6), 1.5)], 0.5, credit=VSCO)
put('spell.dark', [tail(mixdown([(0, note(r'gong_hit_ff', -12, 3.0), 0.9), (0.05, note(r'trem_A2', -5, 1.8, 0.15), 0.5)], 3.2), 1.4)], 0.6, credit=VSCO)
put('spell.astral', [tail(mixdown([(0, note(r'glock_fx_up_chromatic_slow_01', 5, 1.4), 0.6), (0.12, note(r'fx1_short_r01_main', 5, 1.6), 0.5)], 1.8), 0.6)], 0.55, credit=VSCO)
put('spell.holy', [tail(mixdown([(0, note(r'glock_fx_up_chromatic_slow_01', 0, 1.6), 0.6), (0.2, note(r'fx1_short_r01_main', 0, 1.8), 0.6)], 2.0), 0.6)], 0.6, credit=VSCO)
# war drums under battle music: giant drum and bass drum hits
put('drum.taiko', [note(f) for f in [r'EthnicLargeMallet_hit_ff_1', r'EthnicLargeMallet_hit_ff_2', r'bdrum_ff_1', r'bdrum3_fff_1']], 0.6, credit=VSCO)
put('drum.frame', [note(f) for f in [r'EthnicLargeHand_hit_f_1', r'EthnicLargeHand_hit_f_2', r'EthnicLargeHand_hit_f_4', r'EthnicLargeHand_hit_ff_1']], 0.5, credit=VSCO)

# --- our war drums: one-shots for audio.js's battle-drum patterns. Each kind levelled alike (the patterns set the dynamics);
# a few takes pitched a touch for round-robin variety; long rings cut with a fade ---
def take(pattern, semis=0.0, dur=None):
    a = note(pattern, semis, dur)
    return a
put('wd.boom', [take(r'EthnicLargeMallet_hit_ff_1'), take(r'EthnicLargeMallet_hit_ff_2'), take(r'EthnicLargeMallet_hit_f_1'),
                take(r'EthnicLargeMallet_hit_ff_1', -1.5), take(r'EthnicLargeMallet_hit_ff_2', -2.5), take(r'EthnicLargeMallet_hit_f_1', -1)], 0.8, credit=VSCO)
put('wd.soft', [take(r'EthnicLargeMallet_hit_mf_1'), take(r'EthnicLargeMallet_hit_pp_1'), take(r'EthnicLargeMallet_hit_mf_1', -1.5)], 0.6, credit=VSCO)
put('wd.low', [take(r'bdrum3_fff_1', 0, 2.6), take(r'bdrum_fff_1', 0, 2.6), take(r'bdrum_ff_1', -2, 2.6), take(r'bdrum_f_1', 0, 2.6)], 0.8, credit=VSCO)
put('wd.hand', [take(r'EthnicLargeHand_hit_ff_1'), take(r'EthnicLargeHand_hit_f_4'), take(r'EthnicLargeHand_hit_f_1'), take(r'EthnicLargeHand_hit_f_2'),
                take(r'EthnicLargeHand_hit_ff_1', 1), take(r'EthnicLargeHand_hit_f_4', -1)], 0.65, credit=VSCO)
put('wd.timp', [take(r'Timpani1_Hit', 0, 2.4), take(r'Timpani2_Hit', 0, 2.4), take(r'Timpani3_Hit', 0, 2.4), take(r'Timpani4_Hit', 0, 2.0)], 0.7, credit=VSCO)   # low to high
roll = note(r'Timpani2_Roll_v5', 0, 2.6); n = len(roll); roll *= np.linspace(0.15, 1, n) ** 1.6   # a swell into the next downbeat
put('wd.roll', [roll], 0.7, credit=VSCO)
put('wd.crash', [note(r'crash_hit_ff_loose', 0, 2.6)], 0.55, credit=VSCO)
put('wd.gong', [note(r'gong_hit_ff', -5, 4.5), note(r'gong_hit_ff', -8, 4.5)], 0.55, credit=VSCO)

# --- the ambience bed: the user's forest track (110 bpm, 3-bar phrases), cut to ten phrases and looped on that beat ---
FOREST = SRC/'user'/'forest dungeon2.mp3'
if FOREST.exists():
    a = load(FOREST, 44100, mono=False)
    L = int(round(10 * 12 * 60 / 110 * 44100)); F = int(0.3 * 44100)   # 65.45 s; the track itself fades out after 66 s
    assert len(a) > L + F, 'forest track shorter than expected'
    w = np.linspace(0, 1, F)[:, None]
    loop = a[:L].copy(); loop[:F] = a[:F] * w + a[L:L + F] * (1 - w)   # the tail runs on into the start: seamless
    rms = float(np.sqrt((loop ** 2).mean()) + 1e-9); g = min(10 ** (-20 / 20) / rms, 0.95 / np.abs(loop).max())
    save_m4a(loop * g, 'amb-forest.m4a', 44100, kbps=112)
    credits.setdefault('"forest dungeon2" (found free on itch.io by the user; author to be credited)', []).append('the ambience bed')
    print('amb-forest', round(L / 44100, 2), 's')

# --- music: matched loudness, compact stereo AAC; one long piece cut to an excerpt ---
MUSIC = {  # id: (file, mood, title, author page)
    'legend': ('legend.mp3', 'arrive', 'A Legend Will Rise', 'opengameart.org/content/a-legend-will-rise-orchestral'),
    'at-home': ('at-home.mp3', 'day', 'At Home (Orchestral)', 'opengameart.org/content/at-home-orchestral'),
    'celtic': ('celtic.mp3', 'day', 'Celtic Loop', 'opengameart.org/content/celtic-loop'),
    'market': ('market.mp3', 'day', 'Medieval: Market Day', 'opengameart.org/content/medieval-market-day'),
    'tower-inn': ('tower-inn.mp3', 'day', 'Medieval: The Old Tower Inn', 'opengameart.org/content/medieval-the-old-tower-inn'),
    'rejoicing': ('rejoicing.mp3', 'day', 'Medieval: Rejoicing', 'opengameart.org/content/medieval-rejoicing'),
    'once-upon': ('once-upon.mp3', 'day', 'Once Upon a Time', 'opengameart.org/content/once-upon-a-time-loop'),
    'hope': ('hope.mp3', 'day', 'The Hope', 'opengameart.org/content/the-hope'),
    'winter-home': ('winter-home.flac', 'night', 'A Long Winter at Home (excerpt)', 'opengameart.org/content/a-long-winter-at-home-classical-fainod'),
    'lament': ('lament.mp3', 'night', 'Lament of the War', 'opengameart.org/content/laments-of-the-war'),
    'hymn': ('hymn.mp3', 'night', 'Original Hymn', 'opengameart.org/content/original-hymn'),
    'choir2': ('choir2.mp3', 'night', 'Fantasy Choir 2', 'opengameart.org/content/fantasy-choir-3-orchestral-pieces'),
    'choir1': ('choir1.mp3', 'deep', 'Fantasy Choir 1', 'opengameart.org/content/fantasy-choir-3-orchestral-pieces'),
    'choir3': ('choir3.mp3', 'deep', 'Fantasy Choir 3', 'opengameart.org/content/fantasy-choir-3-orchestral-pieces'),
    'unexplored': ('unexplored.mp3', 'deep', 'Unexplored', 'opengameart.org/content/unexplored-short-ver-orchestra-music'),
    'battle-b': ('battle-b.mp3', 'battle', 'Battle Theme B', 'opengameart.org/content/battle-theme-b-for-rpg'),
    'battlegrounds': ('battlegrounds.mp3', 'battle', 'Fantasy - Battlegrounds', 'opengameart.org/content/fantasy-battlegrounds'),
    'pursuit': ('pursuit.wav', 'battle', 'Determined Pursuit', 'opengameart.org/content/determined-pursuit-epic-orchestra-loop'),
    'prepare': ('prepare.mp3', 'battle', 'Prepare to Fight', 'opengameart.org/content/prepare-to-fight'),
}
for mid, (fn, mood, title, page) in (MUSIC.items() if WITH_MUSIC else []):
    a = load(SRC/'music'/fn, 44100, mono=False)
    if mid == 'winter-home': a = a[:int(200 * 44100)]
    n = min(len(a), int(4 * 44100)); a[-n:] *= np.linspace(1, 0, n)[:, None] ** 2
    rms = float(np.sqrt((a ** 2).mean()) + 1e-9); g = 10 ** (-19 / 20) / rms; pk = np.abs(a).max()
    if pk * g > 0.95: g = 0.95 / pk
    save_m4a(a * g, f'music/{mid}.m4a', 44100, kbps=112)
    manifest['music'][mid] = {'mood': mood, 'title': title, 'sec': round(len(a) / 44100, 1)}
    credits.setdefault(f'"{title}" (https://{page}, CC0)', []).append('music')
    print('music', mid, mood, round(len(a) / 44100), 's')

(OUT/'CREDITS.md').write_text('# Kin & Stone sound credits\n\nEvery recording here is CC0 (public domain dedication); credit is given with thanks, not as a condition.\n\n'
                              + '\n'.join(f'- {c}: {", ".join(n)}' for c, n in sorted(credits.items())) + '\n\nMade into the game\'s set by tools/build_audio_assets.py '
                              '(trimmed, levelled, some takes pitched; the forest bed cut to a seamless loop).\n')
shutil.rmtree(TMP, ignore_errors=True)
print('done:', len(manifest['sounds']), 'sounds,', len(manifest['music']), 'tracks ->', OUT)
