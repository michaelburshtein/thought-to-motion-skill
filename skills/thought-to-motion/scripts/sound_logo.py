"""The brand's three-note sound logo, synthesized from code (original, claim-free).

Same melody in every mood so it becomes recognisable; only the instrument changes:
  dark -> soft piano     light -> warm pluck     bold -> clean synth pulse
Usage:
  sound_logo.py <out.wav> --kind intro|outro --theme bold [--duration 2.0] [--key A]
intro: the three notes rise with the play triangle and the wordmark (0.30 / 0.47 / 0.64 s).
outro: the same three notes, then the octave resolves when the play triangle turns into pause (1.8 s).
"""
import argparse

import numpy as np
import soundfile as sf

SR = 48000
NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def piano(f, n):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, a in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12), (5, 0.06)):
        out += a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (2.2 + 1.6 * k))
    att = np.minimum(1, t / 0.006)
    return out * att


def pluck(f, n, rng):
    # Karplus-Strong with a soft, warm low-pass in the loop
    p = max(2, int(SR / f)); buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    buf = np.convolve(buf, np.ones(4) / 4, mode="same")
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out


def pulse(f, n):
    t = np.arange(n) / SR
    sq = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5, 7))
    env = np.exp(-t * 5.5) * np.minimum(1, t / 0.004)
    # filter sweep feel: blend toward the fundamental as the note decays
    return (0.35 * sq * np.exp(-t * 9) + np.sin(2 * np.pi * f * t)) * env


def voice(theme, f, n, rng):
    if theme == "dark": return piano(f, n)
    if theme == "light": return pluck(f, n, rng)
    return pulse(f, n)


def room(x, wet=0.22):
    # a small, soft room: a few decaying taps
    y = x.copy()
    for d, g in ((0.043, 0.5), (0.071, 0.38), (0.113, 0.27), (0.167, 0.18), (0.241, 0.11)):
        k = int(d * SR); y[k:] += wet * g * x[:-k]
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--kind", default="intro"); ap.add_argument("--theme", default="bold")
    ap.add_argument("--duration", type=float, default=None); ap.add_argument("--key", default="A")
    a = ap.parse_args()
    dur = a.duration or (3.0 if a.kind == "outro" else 2.0)
    root = 57 + NOTES[a.key]  # A3 for key A
    third, fifth, octave = root + 12 + 4, root + 12 + 7, root + 24
    first = root + 12
    if a.kind == "intro":
        events = [(0.30, first, 1.0), (0.47, third, 0.9), (0.64, fifth, 1.0)]
    else:
        events = [(0.20, first, 0.8), (0.37, third, 0.75), (0.54, fifth, 0.85),
                  (1.80, octave, 0.9), (1.80, first, 0.55), (1.80, root, 0.4)]
    rng = np.random.default_rng(7)
    n = int(dur * SR); mix = np.zeros(n)
    for at, m, g in events:
        s = int(at * SR); ln = n - s
        mix[s:] += g * voice(a.theme, hz(m), ln, rng)
    mix = room(mix)
    fade = int(0.25 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    mix *= 0.5 / max(1e-6, np.abs(mix).max())  # peak -6 dBFS; render loudness is set in the final mix
    sf.write(a.out, np.stack([mix, mix], 1), SR)
    print("sound logo:", a.out, a.kind, a.theme)


if __name__ == "__main__":
    main()
