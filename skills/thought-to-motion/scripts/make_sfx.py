"""Synthesize a small, licence-clean sound-effect kit (pop, whoosh, ding, tick, rise).

Generated from math, so there is no third-party licence to track. Usage: make_sfx.py <outdir>
"""
import os
import sys

import numpy as np
import soundfile as sf

SR = 48000


def env(n, attack, decay):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / decay)


def pop():
    n = int(0.18 * SR); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 28) + 180
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.04)


def whoosh():
    n = int(0.55 * SR); rng = np.random.default_rng(7)
    noise = rng.standard_normal(n)
    # sweep a simple one-pole low-pass up then down
    cut = np.concatenate([np.linspace(0.02, 0.35, n // 2), np.linspace(0.35, 0.02, n - n // 2)])
    out = np.zeros(n); y = 0.0
    for i in range(n):
        y += cut[i] * (noise[i] - y); out[i] = y
    shape = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return out * shape * 2.2


def ding():
    n = int(1.2 * SR); t = np.arange(n) / SR
    tone = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1320, 1.0), (2640, 0.35), (3960, 0.12)])
    return tone * env(n, 0.003, 0.35) * 0.6


def tick():
    n = int(0.05 * SR); rng = np.random.default_rng(3)
    return rng.standard_normal(n) * env(n, 0.0005, 0.006) * 0.8


def rise():
    n = int(0.8 * SR); t = np.arange(n) / SR
    f = 220 + 660 * (t / t[-1]) ** 2
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.linspace(0, np.pi, n)) * 0.45


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for name, fn in {"pop": pop, "whoosh": whoosh, "ding": ding, "tick": tick, "rise": rise}.items():
        x = fn()
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.7  # peak about -3 dBFS
        sf.write(os.path.join(outdir, f"{name}.wav"), np.stack([x, x], 1).astype(np.float32), SR, subtype="PCM_16")
    print("sfx written to", outdir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sfx")
