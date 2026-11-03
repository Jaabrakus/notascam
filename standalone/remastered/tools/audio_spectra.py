#!/usr/bin/env python3
"""Spectrogram contact sheet of the WAVs tools/render_audio.js writes (numpy + PIL, no matplotlib):
    python3 tools/audio_spectra.py [samples-dir] [out.png] [glob]
Each tile: log-frequency spectrogram (60 Hz-11 kHz, 70 dB range) over the waveform envelope, with the file name."""
import sys, wave, glob
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parents[1]
src = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE/'reports/polish-2026-10-22/audio/samples'
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent/'spectra.png'
pat = sys.argv[3] if len(sys.argv) > 3 else '*.wav'
files = sorted(glob.glob(str(src/pat)))
TW, TH, COLS = 300, 150, 5


def load(p):
    with wave.open(p) as w:
        n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
        a = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float32) / 32768
    return a.reshape(-1, ch).mean(axis=1), sr


def tile(p):
    a, sr = load(p)
    a = a[:int(sr * 6)]
    nfft, hop = 1024, max(64, len(a) // TW)
    if len(a) < nfft:
        a = np.pad(a, (0, nfft - len(a)))
    frames = [a[i:i + nfft] * np.hanning(nfft) for i in range(0, len(a) - nfft + 1, hop)] or [a[:nfft]]
    S = 20 * np.log10(np.abs(np.fft.rfft(np.array(frames), axis=1)) + 1e-7)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    rows = np.geomspace(60, min(11000, sr / 2), TH - 30)
    idx = np.clip(np.searchsorted(freqs, rows), 0, len(freqs) - 1)
    S = S[:, idx].T[::-1]
    top = S.max()
    S = np.clip((S - (top - 70)) / 70, 0, 1)
    img = np.zeros((TH, TW, 3), np.uint8)
    cols = np.linspace(0, S.shape[1] - 1, TW).astype(int)
    v = S[:, cols]
    img[18:18 + v.shape[0], :, 0] = (np.clip(v * 2.2 - 0.6, 0, 1) * 255).astype(np.uint8)
    img[18:18 + v.shape[0], :, 1] = (np.clip(v * 1.6 - 0.25, 0, 1) * 220).astype(np.uint8)
    img[18:18 + v.shape[0], :, 2] = (np.clip(v * 1.2, 0, 1) * 120 + 20).astype(np.uint8)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    env = [np.abs(a[int(i * len(a) / TW):int((i + 1) * len(a) / TW) + 1]).max() for i in range(TW)]
    for x, e in enumerate(env):
        d.line([(x, TH - 1), (x, TH - 1 - int(e * 11))], fill=(230, 200, 120))
    d.text((3, 3), Path(p).stem[:44] + '  %.2fs' % (len(a) / sr), fill=(255, 255, 255))
    return im


rows = (len(files) + COLS - 1) // COLS
sheet = Image.new('RGB', (COLS * TW + (COLS - 1) * 4, rows * TH + (rows - 1) * 4), (40, 40, 40))
for i, f in enumerate(files):
    sheet.paste(tile(f), ((i % COLS) * (TW + 4), (i // COLS) * (TH + 4)))
sheet.save(dst)
print(dst, len(files), 'tiles')
