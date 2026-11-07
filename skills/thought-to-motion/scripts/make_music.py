"""Generate an original background-music bed from code (no samples, no third-party recordings).

Because every note is synthesized here, there is no copyrighted recording for TikTok / Instagram / YouTube
Content ID to match. Usage:
  make_music.py <out.wav> --duration 73.4 [--style calm|warm|pulse] [--bpm 84] [--key A] [--seed 1]

Styles:
  calm  - soft pad chords + slow arpeggio, no drums (reflective, voice-friendly)
  warm  - pad + plucked arpeggio + soft brushed pulse (personal, story)
  pulse - pad + arpeggio + light kick and hat (tech, building, energy)
The bed is mixed low and ducked under the voice later by render.py.
"""
import argparse

import os
import sys

import numpy as np
import soundfile as sf

STYLES = {}  # extra bed styles can be registered here: name -> (fn(duration, bpm, key, seed), bpm, key)

SR = 44100
NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
# progression in scale degrees (major key): I - V - vi - IV, a warm, unresolved-but-friendly loop
PROG = [(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def chord(root_midi, quality):
    third = 3 if quality == "min" else 4
    return [root_midi, root_midi + third, root_midi + 7, root_midi + 12]


def adsr(n, a, d, s, r):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, max(na, 1))
    e[na:na + nd] = np.linspace(1, s, max(len(e[na:na + nd]), 1))
    if nr > 0: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, cutoff):
    # one-pole low-pass, enough to soften saw harmonics
    a = np.exp(-2 * np.pi * cutoff / SR); y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y


def pad(freqs, n, rng):
    t = np.arange(n) / SR; out = np.zeros(n)
    for f in freqs:
        for det in (-0.004, 0.0, 0.005):  # three slightly detuned voices = gentle chorus
            ph = rng.uniform(0, 2 * np.pi)
            out += np.sin(2 * np.pi * f * (1 + det) * t + ph) + 0.25 * np.sin(4 * np.pi * f * (1 + det) * t + ph)
    return out / (len(freqs) * 3) * adsr(n, 0.8, 0.5, 0.85, 0.9)


def pluck(f, n):
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 6)


def kick(n):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 9)


def hat(n, rng):
    t = np.arange(n) / SR
    return rng.standard_normal(n) * np.exp(-t * 60) * 0.25


def make(duration, style="calm", bpm=84, key="A", seed=1):
    if style in STYLES:
        fn, b0, k0 = STYLES[style]
        return fn(duration, bpm or b0, key or k0, seed)
    bpm = bpm or 84; key = key or "A"
    rng = np.random.default_rng(seed)
    beat = 60 / bpm; bar = 4 * beat
    total = int((duration + 2) * SR)
    out = np.zeros(total)
    base = 48 + NOTES[key]  # C3-ish register for pads
    nbars = int(np.ceil((duration + 2) / bar))
    for b in range(nbars):
        deg, q = PROG[b % len(PROG)]
        notes = chord(base + deg, q)
        s0 = int(b * bar * SR); n = int(bar * SR * 1.15)
        if s0 >= total: continue
        seg = pad([hz(m) for m in notes], n, rng) * 0.55
        end = min(total, s0 + n); out[s0:end] += seg[: end - s0]
        # arpeggio: 8th notes walking the chord an octave up
        arp = [notes[i % 4] + 12 for i in (0, 1, 2, 3, 2, 1, 2, 3)]
        if style in ("calm",): arp = arp[::2]  # slower for calm
        step = bar / len(arp)
        for i, m in enumerate(arp):
            st = int((b * bar + i * step) * SR); ln = int(min(step * 2.5, 1.2) * SR)
            if st >= total: continue
            e = min(total, st + ln); out[st:e] += pluck(hz(m), ln)[: e - st] * (0.16 if style == "calm" else 0.2)
        if style in ("warm", "pulse"):
            for k in range(4):
                st = int((b * bar + k * beat) * SR)
                if st >= total: continue
                if style == "pulse" or k % 2 == 0:
                    ln = int(0.4 * SR); e = min(total, st + ln); out[st:e] += kick(ln)[: e - st] * (0.5 if style == "pulse" else 0.25)
                if style == "pulse":
                    hs = int((b * bar + k * beat + beat / 2) * SR); ln = int(0.08 * SR); e = min(total, hs + ln)
                    if hs >= total: continue
                    out[hs:e] += hat(ln, rng)[: e - hs]
    out = lowpass(out, 5200 if style == "pulse" else 3600)
    out = out[: int(duration * SR)]
    fade = int(min(2.0, duration / 4) * SR)
    out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.5
    # subtle stereo width: tiny delay on the right channel
    d = int(0.012 * SR); right = np.concatenate([np.zeros(d), out[:-d]])
    return np.stack([out, right], 1).astype(np.float32)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("out")
    ap.add_argument("--duration", type=float, required=True); ap.add_argument("--style", default="calm", choices=["calm", "warm", "pulse"])
    ap.add_argument("--bpm", type=float, default=None); ap.add_argument("--key", default=None); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    sf.write(a.out, make(a.duration, a.style, a.bpm, a.key, a.seed), SR, subtype="PCM_16")
    print("music:", a.out)
