"""Virtual cameras: make one static or handheld shot look like a multi-camera edit (talking-head mode).

Usage: shots.py <job> [--plan plan.json] [--min 3.0] [--max 8.0] [--dry]

Cuts the talking-head footage into "cameras" (A wide, B medium, C close) by cropping the same frame differently,
anchored on the tracked face (faces.json), and writes plan["shots"]:
  [{"start", "end", "cam", "zoom", "x", "y", "drift"}]   x/y = top-left of the crop in source pixels (1080x1920)

Rules (references/motion-rules.md + the editing convention against jump cuts):
- Camera changes land on the pause cuts that prep.py made (so the cut hides the jump), otherwise on sentence ends,
  otherwise on a caption boundary. Never while an element is flying in.
- Shots last min..max seconds; never the same camera twice in a row; shot size changes by >= ~20%.
- While a card, list, compare or panel is on screen the camera is A (wide): cards need space, and a bigger face
  would collide with them. Close-ups (C) go to the moments with no graphics, preferring a punch-in or a reveal.
- Close-up selfies (face taller than a third of the frame) get no virtual cameras in 9:16: there is no room to go
  closer, and a handheld frame moves too much for a fixed crop.
- Zoom is capped by the source resolution (9:16 from a 1080-wide source: C <= 1.4x; 16:9 frames the speaker
  smaller, so up to 1.7x).
- The crop never shows outside the frame; each shot slowly pushes in by `drift` (calm, ~1.5%).
"""
import argparse
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_plan import est_box, face_at, overlap, caption_box  # noqa: E402  (same geometry as the validator)

CARD = {"title", "keyword", "compare", "icon", "list", "media", "endcard", "image", "logo"}
PINNED = {"media", "logo"}   # placed where the speaker points, around the wide framing: the camera stays wide while they show
CAMS = {"9:16": {"A": 1.0, "B": 1.2, "C": 1.4}, "16:9": {"A": 1.0, "B": 1.35, "C": 1.7}}
FRAME_X = {"A": 0.5, "B": 0.44, "C": 0.56}   # where the face centre sits horizontally: B and C from "different sides"
W, H = 1080, 1920


def cut_points(job, plan):
    """Pause cuts on the cut timeline (from keep.json) and sentence/caption boundaries."""
    pts = []
    kp = os.path.join(job, "keep.json")
    if os.path.exists(kp):
        t = 0.0
        for a, b in json.load(open(kp))[:-1]:
            t += b - a; pts.append((round(t, 3), "pause"))
    for c in plan["captions"]:
        kind = "sentence" if c["text"].rstrip().endswith((".", "?", "!", "׃")) else "caption"
        pts.append((c["end"], kind))
        pts.append((c["start"], "caption"))
    return sorted(set(pts))


def busy(plan, a, b):
    """True if a card is on screen for a meaningful part of [a, b]."""
    for e in plan["elements"]:
        if e.get("type") in CARD:
            o = min(b, e["end"]) - max(a, e["start"])
            if o > 0.25: return True
    return False


def entering(plan, t):
    return any(e.get("type") in CARD and e["start"] - 0.2 <= t <= e["start"] + 0.5 for e in plan["elements"])


def face_center(faces, a, b):
    bs = [x for x in faces["boxes"] if x[1] is not None and a <= x[0] <= b] or [x for x in faces["boxes"] if x[1] is not None]
    return (st.median(x[1] + x[3] / 2 for x in bs), st.median(x[2] + x[4] / 2 for x in bs), st.median(x[4] for x in bs))


def crop(zoom, fx, fy, fh, cam, eye=0.34, fxr=None):
    """Top-left of the crop so the face sits at FRAME_X horizontally and its eyes `eye` of the way down;
    clamped inside the frame."""
    cw, ch = W / zoom, H / zoom
    x = fx - (FRAME_X[cam] if fxr is None else fxr) * cw
    eyes = fy - 0.12 * fh
    y = eyes - eye * ch
    return round(min(max(x, 0), W - cw), 1), round(min(max(y, 0), H - ch), 1)


def plan_shots(plan, job, mn, mx):
    D = plan["duration"]
    pts = [(t, k) for t, k in cut_points(job, plan) if 0 < t < D - mn * 0.6 and not entering(plan, t)]
    pri = {"pause": 0, "sentence": 1, "caption": 2}
    cuts, t = [0.0], 0.0
    while D - t > mx:
        win = [(tt, k) for tt, k in pts if t + mn <= tt <= t + mx]
        if not win:  # nothing natural in range: take the next boundary after max, if any
            later = [tt for tt, _ in pts if tt > t + mx]
            if not later: break
            t = later[0]
        else:
            t = min(win, key=lambda x: (pri[x[1]], -x[0]))[0]   # best kind; among equals the latest (longer shots, calmer)
        cuts.append(t)
    if D - cuts[-1] < mn and len(cuts) > 1: cuts.pop()
    bounds = list(zip(cuts, cuts[1:] + [D]))

    return bounds


def collisions(plan, faces, a, b, z, x, y):
    """How much the (zoomed) face is covered in [a, b]: worst card overlap and worst caption overlap (0..1)."""
    worst_card = worst_cap = 0.0
    for e in plan["elements"]:
        if e.get("type") not in CARD or min(b, e["end"]) - max(a, e["start"]) <= 0: continue
        r = est_box(e); fb = face_at(faces, max(a, e["start"]), min(b, e["end"]))
        if not r or not fb: continue
        fz = ((fb[0] - x) * z, (fb[1] - y) * z, fb[2] * z, fb[3] * z)
        worst_card = max(worst_card, overlap(r, fz) / (r[2] * r[3]))
    for c in plan["captions"]:
        if min(b, c["end"]) - max(a, c["start"]) <= 0: continue
        fb = face_at(faces, max(a, c["start"]), min(b, c["end"]))
        if not fb: continue
        cb = caption_box(c, plan); fz = ((fb[0] - x) * z, (fb[1] - y) * z, fb[2] * z, fb[3] * z * 0.92)
        worst_cap = max(worst_cap, overlap(cb, fz) / (cb[2] * cb[3]))
    return worst_card, worst_cap


def fits(plan, faces, a, b, z, x, y, base):
    """A camera is allowed if cards stay off the face and captions off the mouth, or, when the original framing
    already can't avoid it (a selfie close-up), if it is no worse than the original framing."""
    card, cap = collisions(plan, faces, a, b, z, x, y)
    # cards, panels and logos: a zoomed camera may not bring the face any closer to them than ~nothing
    return card <= 0.005 and cap <= max(0.10, base[1] + 0.03)


def choose(plan, faces, bounds, zooms):
    punch = [e["start"] for e in plan["elements"] if e.get("type") == "punchin"]
    reveal = [e["reveal"]["at"] for e in plan["elements"] if e.get("type") == "compare" and e.get("reveal")]
    shots, prev, k = [], None, 0
    for a, b in bounds:
        fx, fy, fh = face_center(faces, a, b)
        opts = {}
        pinned = any(e.get("type") in PINNED and min(b, e["end"]) - max(a, e["start"]) > 0.1 for e in plan["elements"])
        base = collisions(plan, faces, a, b, 1.0, 0, 0)
        for cam in ("A", "B", "C"):
            if cam == "A": opts[cam] = (0.0, 0.0); continue
            if pinned: continue
            # try framings from the preferred one outward: face higher/lower in the frame, then centred
            for eye in (0.34, 0.40, 0.46, 0.52, 0.30):
                for fxr in (None, 0.5):
                    x, y = crop(zooms[cam], fx, fy, fh, cam, eye, fxr)
                    if fits(plan, faces, a, b, zooms[cam], x, y, base): opts[cam] = (x, y); break
                if cam in opts: break
        # wide is the "master" the edit keeps returning to; B and C alternate between, C on punch-ins and reveals
        cycle = [["B", "A", "C"], ["A", "C", "B"], ["C", "A", "B"], ["A", "B", "C"]][k % 4]
        want = ["C", "B", "A"] if any(a <= t < b for t in punch + reveal) else cycle
        cam = next((c for c in want if c in opts and c != prev), None)
        if cam is None:  # only the previous camera fits: extend that shot instead of cutting to the same framing
            shots[-1]["end"] = b; continue
        x, y = opts[cam]
        shots.append({"start": round(a, 3), "end": round(b, 3), "cam": cam, "zoom": zooms[cam], "x": x, "y": y})
        prev = cam; k += 1
    return shots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("--plan"); ap.add_argument("--min", type=float, default=3.0)
    ap.add_argument("--max", type=float, default=8.0); ap.add_argument("--drift", type=float, default=0.015)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    pp = a.plan or os.path.join(a.job, "plan.json")
    plan = json.load(open(pp))
    if plan.get("mode") != "talking-head": raise SystemExit("virtual cameras are for talking-head videos")
    faces = json.load(open(os.path.join(a.job, "faces.json")))
    hs = [b[4] for b in faces["boxes"] if b[1] is not None]
    if hs and st.median(hs) > 0.33 * H and plan.get("aspect", "9:16") == "9:16":
        print(f"close-up selfie (face is {st.median(hs) / H:.0%} of the frame height): there is no room to cut closer, "
              "so virtual cameras stay off for 9:16. They work in 16:9, or with the phone held a bit farther away.")
        if not a.dry: plan.pop("shots", None); json.dump(plan, open(pp, "w"), ensure_ascii=False, indent=1)
        return
    zooms = CAMS[plan.get("aspect", "9:16")]
    out = choose(plan, faces, plan_shots(plan, a.job, a.min, a.max), zooms)
    for o in out: o["drift"] = 0 if o["cam"] == "A" else a.drift
    for o in out: print(f"{o['start']:6.2f}-{o['end']:6.2f}  {o['cam']}  zoom {o['zoom']}")
    print(f"{len(out)} shots, average {plan['duration'] / max(1, len(out)):.1f}s")
    if not a.dry:
        plan["shots"] = out
        json.dump(plan, open(pp, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
