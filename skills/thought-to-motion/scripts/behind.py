#!/usr/bin/env python3
"""A word behind the speaker's head.

Plan element: {"type": "behind", "text": "GODS", "start": 41.2, "end": 44.0, "size"?: px, "y"?: centre y, "x"?: centre x}
The word is drawn INTO the scene: on the footage, under a cut-out of the person, so his head and shoulders pass in front
of it. Works on a single take (no clean plate): a MODNet portrait matte per frame (the same model as background.py),
smoothed over time. For each behind element this script writes RGBA cut-outs for every
frame of the window into <job>/public/behind/<n>/<frame>.webp and records them in the plan ("cutout", "frames"), plus
the word's position (centred on his head, the middle of the word at the upper head) unless the plan sets x / y.

Usage: behind.py <job> [--plan <job>/plan.json] [--short 512]
Run it after the plan's timings are final (it reads public/<source>); re-run after any change to start/end.
Colour: the series accent with a thin dark edge so it reads on a light wall. About 3 s.
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from background import get_model, matte  # noqa: E402


def read_frames(src, t0, n, fps, w, h):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", src, "-frames:v", str(n), "-vf", f"fps={fps},scale={w}:{h}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    k = w * h * 3
    while True:
        b = p.stdout.read(k)
        if len(b) < k: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def head_anchor(alphas, w, h):
    """Head centre x and the y of the top of the head, from the mattes (median over the window)."""
    xs, tops, widths = [], [], []
    for a in alphas[:: max(1, len(alphas) // 12)]:
        m = a > 0.5
        rows = np.where(m.any(axis=1))[0]
        if not len(rows): continue
        top = rows[0]; band = m[top: top + int(0.08 * h)]
        cols = np.where(band.any(axis=0))[0]
        if not len(cols): continue
        tops.append(top); xs.append((cols[0] + cols[-1]) / 2)
        head = m[top + int(0.09 * h)]; c = np.where(head)[0]
        widths.append(c[-1] - c[0] if len(c) else 0.25 * w)
    if not tops: return w / 2, 0.3 * h, 0.25 * w
    return float(np.median(xs)), float(np.median(tops)), float(np.median(widths))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("job"); ap.add_argument("--plan")
    ap.add_argument("--short", type=int, default=512, help="matte resolution (short side); 512 = sharp hair at 1080")
    a = ap.parse_args()
    plan_path = a.plan or os.path.join(a.job, "plan.json")
    plan = json.load(open(plan_path)); fps = plan.get("fps", 30)
    src = os.path.join(a.job, "public", plan["source"])
    w, h = 1080, 1920
    items = [e for e in plan.get("elements", []) if e.get("type") == "behind"]
    if not items: print("no behind elements in the plan"); return
    sess = get_model()
    for n, e in enumerate(items):
        f0 = int(round(e["start"] * fps)) - 2; f1 = int(round(e["end"] * fps)) + 2
        f0 = max(0, f0)
        out = os.path.join(a.job, "public", "behind", str(n)); os.makedirs(out, exist_ok=True)
        prev = None; alphas = []; k = f0
        for rgb in read_frames(src, f0 / fps, f1 - f0 + 1, fps, w, h):
            al = matte(sess, rgb, a.short)
            # temporal smoothing against flicker, but follow fast moves (keep the larger of the two where he moved)
            al = al if prev is None else np.maximum(0.55 * al + 0.45 * prev, al * 0.9)
            prev = al; alphas.append(al)
            rgba = np.dstack([rgb, (np.clip(al, 0, 1) * 255).astype(np.uint8)])
            Image.fromarray(rgba, "RGBA").save(os.path.join(out, f"{k:05d}.webp"), quality=92, alpha_quality=100, method=2)
            k += 1
        cx, top, hw = head_anchor(alphas, w, h)
        e["cutout"] = f"behind/{n}"; e["frames"] = [f0, k - 1]
        e.setdefault("x", round(cx)); e.setdefault("y", round(top + 0.32 * hw))
        e["_head"] = {"top": round(top), "width": round(hw)}
        print(f"behind {n} '{e.get('text')}': frames {f0}-{k - 1}, head x {cx:.0f}, top {top:.0f}, width {hw:.0f} -> word at ({e['x']}, {e['y']})")
    json.dump(plan, open(plan_path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
