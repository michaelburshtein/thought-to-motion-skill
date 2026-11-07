"""Find finger snaps (and claps) in a talking-head take, on the CUT timeline, so effects he triggers land on the snap.

Usage:
  snaps.py <job> [--near T [T ...]] [--window 2.5] [--top 6]

the speaker snaps his fingers to trigger an effect ("hocus pocus" -> the background changes, "run them live" -> the panels
start playing). The effect must start on the frame of the snap, not on the word. A snap is a very short, very sharp
broadband click: in the 2.5-9 kHz band its energy jumps by >= 12 dB within ~5 ms and falls back within ~80 ms, and it
is much brighter than speech. Uses work/joined.mp4 (cut but NOT noise-cleaned - the cleanup softens clicks), falling
back to public/source.mp4. Writes <job>/snaps.json and prints the candidates (time, strength) - near each --near time
if given, otherwise the strongest in the whole take. Then use the snap time as the effect's start:
  background.py ... --reveal <snap>, media "playAt": <snap>, punchin/sfx "start"/"at": <snap>.
Always check the frame at the snap time: the hand should be closing on it.
"""
import argparse
import json
import os
import subprocess

import numpy as np

SR = 48000


def audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def band(x, lo, hi):
    """Simple FFT band-pass over the whole signal (takes are short)."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x)).astype(np.float32)


def envelope_db(x, hop):
    n = len(x) // hop
    e = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-9
    return 20 * np.log10(e)


def find(x):
    hop = SR // 500                                    # 2 ms frames
    hi = envelope_db(band(x, 2500, 9000), hop)         # where a snap lives
    lo = envelope_db(band(x, 100, 1500), hop)          # where most of speech lives
    out = []
    for i in range(5, len(hi) - 45):
        rise = hi[i] - np.min(hi[i - 5:i - 1])          # jump vs the previous ~10 ms
        if rise < 12 or hi[i] < np.max(hi[i - 3:i]) or hi[i] < np.max(hi[i + 1:i + 3]): continue
        decay = hi[i] - np.median(hi[i + 15:i + 40])   # 30-80 ms later it must be gone
        bright = hi[i] - lo[i]                          # brighter than speech at that instant
        if decay < 10 or bright < 0: continue
        out.append({"t": round(i * hop / SR, 3), "strength": round(float(rise + 0.5 * decay + 0.5 * bright), 1)})
    # keep the strongest per 150 ms
    out.sort(key=lambda c: -c["strength"]); kept = []
    for c in out:
        if all(abs(c["t"] - k["t"]) > 0.15 for k in kept): kept.append(c)
    return sorted(kept, key=lambda c: c["t"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("--near", type=float, nargs="*"); ap.add_argument("--window", type=float, default=2.5)
    ap.add_argument("--top", type=int, default=6)
    a = ap.parse_args()
    src = os.path.join(a.job, "work", "joined.mp4")
    if not os.path.exists(src): src = os.path.join(a.job, "public", "source.mp4")
    cands = find(audio(src))
    json.dump({"source": os.path.relpath(src, a.job), "snaps": cands}, open(os.path.join(a.job, "snaps.json"), "w"), indent=1)
    if a.near:
        for t in a.near:
            near = sorted([c for c in cands if abs(c["t"] - t) <= a.window], key=lambda c: -c["strength"])[:3]
            print(f"near {t}s:", ", ".join(f"{c['t']}s (strength {c['strength']})" for c in near) or "no snap found")
    else:
        for c in sorted(cands, key=lambda c: -c["strength"])[: a.top]: print(f"{c['t']}s strength {c['strength']}")
    print(f"{len(cands)} candidates from {os.path.relpath(src, a.job)} -> snaps.json")


if __name__ == "__main__":
    main()
