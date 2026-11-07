"""Clean plate from a separate empty-room clip (filmed from the same locked phone position before or after the talk).

Usage: plate_from_clip.py <job> <empty_room_clip> [--samples 24]

1. Empty room: median of the clip's frames (normalised to 1080x1920 exactly like prep.py), so sensor noise and a
   passing shadow disappear.
2. Alignment: the phone may have shifted a few pixels or re-zoomed slightly between the two recordings. The plate is
   aligned to the talk's own background (pixels the portrait model is sure are room) with ECC image registration
   (affine), so walls, door frames and shelves line up.
3. Exposure and colour: phones re-expose when the person sits in the frame, so the empty-room clip is usually
   brighter. A per-channel gain + offset is fitted on the same sure-room pixels and applied to the plate.
Writes <job>/work/clean_plate.png (used automatically by background.py and bg_qa.py) and work/plate_check.jpg
(talk frame | aligned plate | difference) for a visual check. Reports how well the plate matches.
"""
import argparse
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
W, H = 1080, 1920
VF = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"


def frames(path, fps):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},{VF}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout)


def main():
    import cv2
    from PIL import Image
    from background import get_model, matte
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("clip"); ap.add_argument("--samples", type=int, default=24)
    a = ap.parse_args()
    work = os.path.join(a.job, "work"); os.makedirs(work, exist_ok=True)

    # 1) empty room: the still opening of the clip (until something enters the picture), median of those frames
    pf, ref = [], None
    for f in frames(a.clip, 5):
        small = np.asarray(Image.fromarray(f).resize((135, 240), Image.BILINEAR), np.int16)
        if ref is None: ref = small
        if (np.abs(small - ref).max(-1) > 28).mean() > 0.004: break   # someone walked in
        pf.append(f)
    if len(pf) < 5: raise SystemExit("the clip doesn't open on a still, empty room (need at least 1 s)")
    plate = np.median(np.stack(pf[:-1]), 0).astype(np.uint8)
    print(f"empty room: the first {len(pf) / 5:.1f}s are still and empty; median of {len(pf) - 1} frames")

    # 2) the talk's sure-room pixels: sample frames, mask the person generously, median what is left
    talk = os.path.join(work, "full.mp4") if os.path.exists(os.path.join(work, "full.mp4")) else os.path.join(a.job, "public", "source.mp4")
    sess = get_model()
    tf = list(frames(talk, a.samples / max(1, duration(talk))))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61))
    masks = [cv2.erode((matte(sess, f, 320) < 0.1).astype(np.uint8), k) > 0 for f in tf]   # sure room, 30 px from the person
    st = np.stack(tf).astype(np.float32); mk = np.stack(masks)
    cnt = mk.sum(0)
    room_t = np.where(cnt[..., None] > 0, np.nansum(np.where(mk[..., None], st, 0), 0) / np.maximum(cnt, 1)[..., None], 0).astype(np.uint8)
    valid = cnt >= max(2, len(tf) // 4)
    print(f"talk background: {len(tf)} frames, {valid.mean():.0%} of the picture is reliably room")

    # 3) align the plate to the talk background (affine ECC on grey, only on reliable room pixels)
    g1 = cv2.GaussianBlur(cv2.cvtColor(room_t, cv2.COLOR_RGB2GRAY), (0, 0), 2).astype(np.float32) / 255
    g2 = cv2.GaussianBlur(cv2.cvtColor(plate, cv2.COLOR_RGB2GRAY), (0, 0), 2).astype(np.float32) / 255
    # normalise brightness first so exposure doesn't fight the alignment
    g2n = (g2 - g2[valid].mean()) / (g2[valid].std() + 1e-6) * g1[valid].std() + g1[valid].mean()
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        _, warp = cv2.findTransformECC(g1, g2n.astype(np.float32), warp, cv2.MOTION_AFFINE,
                                       (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), valid.astype(np.uint8), 5)
    except cv2.error as e:
        print("alignment: ECC did not converge, using the plate as filmed:", str(e).splitlines()[-1])
    shift = np.hypot(warp[0, 2], warp[1, 2]); scale = np.sqrt(abs(np.linalg.det(warp[:, :2])))
    print(f"alignment: shift {shift:.1f}px, scale {scale:.4f}")
    plate_a = cv2.warpAffine(plate, warp, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)

    # 4) exposure + colour: per-channel gain/offset fitted on reliable room pixels
    P = plate_a.astype(np.float32); T = room_t.astype(np.float32)
    out = np.empty_like(P)
    idx = np.flatnonzero(valid.ravel())[:: max(1, int(valid.sum() // 200000))]
    for c in range(3):
        x = P[..., c].ravel()[idx]; y = T[..., c].ravel()[idx]
        g, o = np.polyfit(x, y, 1)
        out[..., c] = P[..., c] * g + o
        print(f"colour ch{c}: x{g:.3f} {o:+.1f}")
    plate_m = np.clip(out, 0, 255).astype(np.uint8)
    err = np.abs(plate_m.astype(np.float32) - T).mean(-1)[valid]
    print(f"match: median difference {np.median(err):.1f}/255, 95th percentile {np.percentile(err, 95):.1f}/255 on reliable room pixels")

    Image.fromarray(plate_m).save(os.path.join(work, "clean_plate.png"))
    dif = (np.clip(np.abs(plate_m.astype(np.float32) - tf[len(tf) // 2].astype(np.float32)).mean(-1) * 3, 0, 255)).astype(np.uint8)
    sheet = Image.new("RGB", (3 * 360, 640))
    for i, im in enumerate([tf[len(tf) // 2], plate_m, np.dstack([dif] * 3)]):
        sheet.paste(Image.fromarray(im).resize((360, 640)), (i * 360, 0))
    sheet.save(os.path.join(work, "plate_check.jpg"), quality=85)
    print("clean plate:", os.path.join(work, "clean_plate.png"))


if __name__ == "__main__":
    main()
