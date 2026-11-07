"""Background QA: compare the original video with the replaced-background video, frame by frame, and measure
where the person was lost and where the old room leaked through.

Usage: bg_qa.py <job> [--every 2] [--top 8]

For every Nth frame (default: every other frame):
  - EXPECTED person: a second, independent opinion of where the person is - the portrait model at a higher
    resolution than the compositor uses, joined with the difference from the empty room where that room is
    reliable (seen empty), and the desk band (always in front).
  - KEPT: where the output actually kept the original pixels. The compositor relights the person with one
    global gain/tint, so each output pixel is compared with the relit original; close = kept.
  - LOST  = expected person but not kept (arms vanishing).
  - LEAK  = kept but expected background, and the original there looks like the old room (grey behind head).
Writes <job>/work/bg_qa.json (per-frame percentages, per-second summary) and <job>/work/bg_qa_sheet.jpg (the
worst frames with LOST in red and LEAK in yellow). Exit code 1 if any second fails the thresholds.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import background as bg  # noqa: E402

W, H = 540, 960   # QA works at half resolution: enough to see an arm or a patch of wall, 4x cheaper


def read_frames(path, every):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    n, i = W * H * 3, 0
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        if i % every == 0: yield i, np.frombuffer(b, np.uint8).reshape(H, W, 3)
        i += 1


def main():
    import cv2
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("--every", type=int, default=2); ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--lost-max", type=float, default=0.004, help="fail a frame if this share of the frame is LOST")
    ap.add_argument("--leak-max", type=float, default=0.004, help="fail a frame if this share of the frame is LEAK")
    a = ap.parse_args()
    src = os.path.join(a.job, "public", "source.mp4"); out = os.path.join(a.job, "public", "source_bg.mp4")
    meta = json.load(open(os.path.join(a.job, "work", "bg_meta.json")))
    gain, tint, reveal = meta["gain"], np.array(meta["tint"], np.float32), meta.get("reveal")
    desk = meta.get("desk")
    from PIL import Image as _I, ImageFilter as _F
    pl = _I.open(meta["plate"]).convert("RGB"); k = max(W / pl.width, H / pl.height)
    pl = pl.resize((int(pl.width * k + 0.5), int(pl.height * k + 0.5)), _I.LANCZOS)
    l0, t0 = (pl.width - W) // 2, (pl.height - H) // 2
    pl = pl.crop((l0, t0, l0 + W, t0 + H)).filter(_F.GaussianBlur(meta.get("blur", 6) * W / 1080))
    PL = np.asarray(pl, np.float32) / 255
    sess = bg.get_model()
    ref = os.path.join(a.job, "work", "clean_plate.png")
    if os.path.exists(ref):   # filmed empty-room opening: exact reference
        from PIL import Image
        room = np.asarray(Image.open(ref).convert("RGB").resize((W, H)))
        room_lab = cv2.cvtColor(cv2.GaussianBlur(room, (5, 5), 0), cv2.COLOR_RGB2LAB).astype(np.float32)
        seen = np.ones((H, W), bool)
    else:
        room_lab, room, seen = bg.clean_room(src, sess)
    room_lab = cv2.resize(room_lab, (W, H)); seen = cv2.resize(seen.astype(np.uint8), (W, H)) > 0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vign = np.clip(1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * 0.45) / (H / 1.6)) ** 2), 0.7, 1)[..., None]
    deskband = np.zeros((H, W), bool) if desk is None else (yy / H > desk)

    frames, worst = [], []
    for (i, fo), (_, fn) in zip(read_frames(src, a.every), read_frames(out, a.every)):
        t = i / 30
        if reveal is not None and t < reveal + 0.8: continue          # before the wipe the room is the original on purpose
        F = fo.astype(np.float32) / 255; O = fn.astype(np.float32) / 255
        # expected person: portrait model at 640 short side + reliable room difference + desk band
        m = bg.matte(sess, fo, 640) > 0.5
        lab = cv2.cvtColor(cv2.GaussianBlur(fo, (5, 5), 0), cv2.COLOR_RGB2LAB).astype(np.float32)
        d = np.sqrt(((lab[..., 0] - room_lab[..., 0]) * 0.6) ** 2 + ((lab[..., 1] - room_lab[..., 1]) * 1.6) ** 2
                    + ((lab[..., 2] - room_lab[..., 2]) * 1.6) ** 2)
        dm = (d > 26) & seen
        exp_p = m | dm | deskband
        exp_b = ~(cv2.dilate(exp_p.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)   # sure background (8 px margin)
        exp_p = cv2.erode(exp_p.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0           # sure person
        # kept: output close to the relit original (vignette/grain tolerance)
        relit = np.clip(F * gain * tint, 0, 1) * vign
        Pv = PL * vign
        d_orig, d_new = np.abs(O - relit).mean(-1), np.abs(O - Pv).mean(-1)
        decidable = np.abs(relit - Pv).mean(-1) > 0.06          # original and new room look different enough here
        kept = decidable & (d_orig < 0.08) & (d_orig + 0.03 < d_new)
        replaced = decidable & (d_new < 0.08) & (d_new + 0.03 < d_orig)
        # old room colour: the original pixel matches the empty room where the room is known, or it is neutral grey
        hsv = cv2.cvtColor(fo, cv2.COLOR_RGB2HSV)
        oldroom = ((d < 18) & seen) | ((hsv[..., 1] < 40) & (hsv[..., 2] > 90))
        lost = exp_p & replaced
        leak = kept & exp_b & oldroom
        lost = cv2.morphologyEx(lost.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0   # ignore specks
        leak = cv2.morphologyEx(leak.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
        lp, kp = float(lost.mean()), float(leak.mean())
        frames.append({"t": round(t, 3), "lost": round(lp, 5), "leak": round(kp, 5)})
        worst.append((max(lp / a.lost_max, kp / a.leak_max), t, fn.copy(), lost, leak))
        worst = sorted(worst, key=lambda x: -x[0])[: a.top]
        if i % 300 == 0: print(f"t={t:5.1f}s lost {lp:.2%} leak {kp:.2%}", flush=True)

    secs = {}
    for f in frames:
        s = int(f["t"]); x = secs.setdefault(s, {"lost": 0, "leak": 0, "n": 0, "bad": 0})
        x["lost"] = max(x["lost"], f["lost"]); x["leak"] = max(x["leak"], f["leak"]); x["n"] += 1
        x["bad"] += int(f["lost"] > a.lost_max or f["leak"] > a.leak_max)
    bad = [s for s, x in sorted(secs.items()) if x["bad"]]
    rep = {"frames_checked": len(frames), "bad_frames": sum(x["bad"] for x in secs.values()), "bad_seconds": bad,
           "worst_lost": max((f["lost"] for f in frames), default=0), "worst_leak": max((f["leak"] for f in frames), default=0),
           "per_second": secs, "frames": frames}
    json.dump(rep, open(os.path.join(a.job, "work", "bg_qa.json"), "w"), indent=1)

    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (len(worst) * 270, 500), "white"); dr = ImageDraw.Draw(sheet)
    for k, (_, t, fn, lost, leak) in enumerate(worst):
        v = fn.astype(np.float32)
        v[lost] = v[lost] * 0.4 + np.array([255, 0, 0]) * 0.6
        v[leak] = v[leak] * 0.4 + np.array([255, 220, 0]) * 0.6
        sheet.paste(Image.fromarray(v.astype(np.uint8)).resize((270, 480)), (k * 270, 20))
        dr.text((k * 270 + 6, 4), f"{int(t // 60)}:{t % 60:05.2f}", fill="black")
    sheet.save(os.path.join(a.job, "work", "bg_qa_sheet.jpg"), quality=85)
    print(f"checked {len(frames)} frames: {rep['bad_frames']} over threshold; seconds: {bad}")
    print(f"worst LOST {rep['worst_lost']:.2%} of frame, worst LEAK {rep['worst_leak']:.2%}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
