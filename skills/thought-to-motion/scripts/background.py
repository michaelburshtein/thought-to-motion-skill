"""Replace the background behind a talking head, and make the person sit in the new light.

Usage:
  background.py <job> <plate.jpg|png> [--blur 6] [--reveal 10.2] [--wipe 0.7] [--match 0.65] [--wrap 0.35]

Reads   <job>/public/source.mp4 (from prep.py), writes <job>/public/source_bg.mp4 (same audio) and
switches plan.source to it if <job>/plan.json exists. Everything runs locally:
  1. Portrait matte per frame with MODNet (Apache-2.0, ONNX, CPU), smoothed over time to avoid flicker.
  2. Light matching (computed once for the whole clip, so it never flickers): the person's brightness and
     colour are pulled toward the plate's (--match 0..1), so a brightly lit face doesn't float on a dim room.
  3. Light wrap: the plate's light bleeds softly onto the person's edges (--wrap 0..1).
  4. One shared finish on the composite: soft vignette and fine grain, so both layers read as one camera.
  Desk line: everything below the desk line is in FRONT of the person (the desk and the forearms resting on it), so
     it is kept as filmed (relit like the person) instead of being matted - resting arms otherwise vanish, because
     they sit in the same place all clip long (so the clean-room median thinks they are furniture) and portrait models
     stop at the desk. --desk auto puts the line ~1.2 face-heights under the chin (needs faces.json); --desk 0.9 sets it
     as a fraction of the height; --desk off disables it.
  --reveal T: keep the original room until T seconds, then wipe to the new background (a "before/after" moment).
Model downloads once from huggingface.co into <skill>/.cache/models.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODEL_URL = "https://huggingface.co/Xenova/modnet/resolve/main/onnx/model.onnx"
MODEL = os.path.join(ROOT, ".cache", "models", "modnet.onnx")
W, H, FPS = 1080, 1920, 30
MATTE_SHORT = 512


def get_model():
    if not os.path.exists(MODEL):
        os.makedirs(os.path.dirname(MODEL), exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL + ".part"); os.replace(MODEL + ".part", MODEL)
    import onnxruntime as ort
    # NVIDIA GPU when onnxruntime-gpu is installed (scripts/setup_gpu.sh); otherwise the CPU, exactly as before
    providers = ["CPUExecutionProvider"]
    if "CUDAExecutionProvider" in ort.get_available_providers() and os.environ.get("TTM_GPU", "1") != "0":
        try: ort.preload_dlls()  # CUDA/cuDNN from the pip wheels
        except Exception: pass
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    sess = ort.InferenceSession(MODEL, providers=providers)
    print("matte runs on:", sess.get_providers()[0])
    return sess


def matte(sess, rgb, short=None):
    short = short or MATTE_SHORT
    h, w = rgb.shape[:2]; k = short / min(w, h)
    mw, mh = int(w * k) // 32 * 32, int(h * k) // 32 * 32
    x = np.asarray(Image.fromarray(rgb).resize((mw, mh), Image.BILINEAR), np.float32) / 127.5 - 1
    a = sess.run(None, {"input": x.transpose(2, 0, 1)[None]})[0][0, 0]
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) / 255


def lum(x):
    return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722


def frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)


SW, SH = 540, 960


def clean_room(src, sess=None, fps=1.5):
    """Static camera: the empty room, per pixel, from the frames where that pixel is NOT covered by the person.
    A plain median fails where the person sits most of the time (the head, resting arms): the "room" there becomes
    the person, and then the real wall next to them is mistaken for the person (a grey patch beside the head).
    So each sampled frame is matted first and only background samples vote. Comparing each frame to this room
    finds everything that is the person, including fast hands and hair the portrait model loses."""
    import cv2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={fps},scale={SW}:{SH}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    frs, n = [], SW * SH * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        frs.append(np.frombuffer(b, np.uint8).reshape(SH, SW, 3))
    st = np.stack(frs).astype(np.float32)
    room = np.median(st, axis=0)
    if sess is not None:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        bgm = np.stack([cv2.erode((matte(sess, f, 320) < 0.15).astype(np.uint8), k) > 0 for f in frs])  # sure background
        cnt = bgm.sum(0)
        import warnings
        warnings.filterwarnings("ignore", "All-NaN slice")   # pixels never seen empty fall back to the plain median
        for c in range(3):
            v = np.where(bgm, st[..., c], np.nan)
            med = np.nanmedian(v, axis=0) if cnt.max() else room[..., c]
            room[..., c] = np.where(cnt >= 3, med, room[..., c])   # enough empty samples: trust them
        print(f"clean room plate from {len(frs)} frames (person masked out; {np.mean(cnt >= 3):.0%} of pixels seen empty)")
    else:
        print(f"clean room plate from {len(frs)} frames")
    room = room.astype(np.uint8)
    room_lab = cv2.cvtColor(cv2.GaussianBlur(room, (5, 5), 0), cv2.COLOR_RGB2LAB).astype(np.float32)
    # where the room was really seen empty; elsewhere (the head, the torso) the "room" is a guess and must not be used
    seen = (cnt >= 3) if sess is not None else np.ones(room.shape[:2], bool)
    return room_lab, room, seen


def diff_matte(fr, room_lab, seen=None):
    import cv2
    small = cv2.resize(fr, (SW, SH), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(cv2.GaussianBlur(small, (5, 5), 0), cv2.COLOR_RGB2LAB).astype(np.float32)
    # colour differences count more than brightness, so shadows and exposure drift are mostly ignored
    d = np.sqrt(((lab[..., 0] - room_lab[..., 0]) * 0.6) ** 2 + ((lab[..., 1] - room_lab[..., 1]) * 1.6) ** 2
                + ((lab[..., 2] - room_lab[..., 2]) * 1.6) ** 2)
    m = np.clip((d - 14) / 16, 0, 1)
    if seen is not None: m = m * seen   # only where the empty room is actually known
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mb = cv2.morphologyEx((m > 0.5).astype(np.uint8), cv2.MORPH_OPEN, k)
    mb = cv2.morphologyEx(mb, cv2.MORPH_CLOSE, k, iterations=2)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(mb)
    keep = np.isin(lbl, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 600])  # drop specks
    m = cv2.GaussianBlur((m * keep).astype(np.float32), (7, 7), 0)
    return cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("plate")
    ap.add_argument("--blur", type=float, default=6, help="depth-of-field blur on the plate, px")
    ap.add_argument("--reveal", type=float, default=None); ap.add_argument("--wipe", type=float, default=0.7)
    ap.add_argument("--match", type=float, default=0.65); ap.add_argument("--wrap", type=float, default=0.35)
    ap.add_argument("--grain", type=float, default=3.0)
    ap.add_argument("--preview", type=float, default=None, help="render one frame at this time to work/ and stop")
    ap.add_argument("--draft", action="store_true",
                    help="half resolution (540x960) and a lighter matte: ~3-4x faster, for draft renders only")
    ap.add_argument("--desk", default="auto", help="desk line: auto | off | fraction of the height (e.g. 0.9)")
    ap.add_argument("--moving-camera", action="store_true",
                    help="camera moves: skip the clean-room difference matte (use only the portrait model)")
    a = ap.parse_args()
    src = os.path.join(a.job, "public", "source.mp4"); out = os.path.join(a.job, "public", "source_bg.mp4")
    global W, H, MATTE_SHORT
    if a.draft:
        # draft keeps the full-strength matte (arms are thin, low-res mattes lose them) unless a filmed clean plate
        # exists: then the exact difference matte does the heavy lifting and the faster portrait pass is enough
        W, H = 540, 960
        MATTE_SHORT = 320 if os.path.exists(os.path.join(a.job, "work", "clean_plate.png")) else 512
        small = os.path.join(a.job, "work", "source_540.mp4"); os.makedirs(os.path.dirname(small), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale=540:960", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "18", "-c:a", "copy", small], check=True)
        src = small
    sess = get_model()
    plate_ref = os.path.join(a.job, "work", "clean_plate.png")
    if not a.moving_camera and os.path.exists(plate_ref):
        # the speaker filmed the empty room first: an exact reference everywhere (behind the head and torso too)
        import cv2
        room_rgb = np.asarray(Image.open(plate_ref).convert("RGB").resize((SW, SH), Image.BILINEAR))
        room = cv2.cvtColor(cv2.GaussianBlur(room_rgb, (5, 5), 0), cv2.COLOR_RGB2LAB).astype(np.float32)
        seen = np.ones((SH, SW), bool)
        print("clean plate: using the empty-room opening as the exact background reference")
    else:
        room, room_rgb, seen = (None, None, None) if a.moving_camera else clean_room(src, sess)
    if room_rgb is not None:  # the empty room at output size, for edge decontamination
        import cv2
        R = cv2.resize(cv2.GaussianBlur(room_rgb, (5, 5), 0), (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
        seen_full = cv2.resize(seen.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0

    plate = Image.open(a.plate).convert("RGB")
    # cover-fit the plate to 1080x1920
    k = max(W / plate.width, H / plate.height)
    plate = plate.resize((int(plate.width * k + 0.5), int(plate.height * k + 0.5)), Image.LANCZOS)
    l, t = (plate.width - W) // 2, (plate.height - H) // 2
    plate = plate.crop((l, t, l + W, t + H))
    if a.blur > 0: plate = plate.filter(ImageFilter.GaussianBlur(a.blur * W / 1080))
    P = np.asarray(plate, np.float32) / 255
    P_wrap = np.asarray(plate.filter(ImageFilter.GaussianBlur(40 * W / 1080)), np.float32) / 255

    # 1) light statistics from ~12 frames spread over the clip (one correction for the whole video)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout)
    fg_means = []
    for ts in np.linspace(0.5, dur - 0.5, 12):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ts:.2f}", "-i", src, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        if len(raw) < W * H * 3: continue
        f = np.frombuffer(raw[: W * H * 3], np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        al = matte(sess, (f * 255).astype(np.uint8)) > 0.9
        if al.sum() > 1000: fg_means.append(f[al].mean(0))
    fg = np.mean(fg_means, 0)
    # plate light around where the person sits (centre band), which is what should light them
    bg = P[int(H * 0.2):int(H * 0.75), int(W * 0.15):int(W * 0.85)].reshape(-1, 3).mean(0)
    gain_l = (lum(bg[None])[0] / max(lum(fg[None])[0], 1e-3))
    # keep faces readable: limit how far brightness moves, then apply only part of the gap (--match)
    gain_l = float(np.clip(gain_l, 0.55, 1.4)) ** a.match
    tint = (bg / max(bg.mean(), 1e-3)) / (fg / max(fg.mean(), 1e-3))
    tint = 1 + (np.clip(tint, 0.8, 1.25) - 1) * a.match
    print(f"light match: brightness x{gain_l:.2f}, colour {np.round(tint, 3).tolist()}")

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    desk = None
    if a.desk != "off":
        if a.desk == "auto":
            fp = os.path.join(a.job, "faces.json")
            if os.path.exists(fp):
                import statistics as stt
                fj = json.load(open(fp)); bs = [b for b in fj["boxes"] if b[1] is not None]
                if bs:
                    chin = stt.median(b[2] + b[4] for b in bs) / fj["h"]; fh = stt.median(b[4] for b in bs) / fj["h"]
                    desk = float(np.clip(chin + 1.2 * fh, 0.8, 0.96))
        else:
            desk = float(a.desk)
    # keep-zone: 0 above the desk line, 1 below it, with a soft 4% feather so the seam never shows
    keep = None if desk is None else np.clip((yy / H - (desk - 0.03)) / 0.04, 0, 1)
    print("desk line:", "off" if desk is None else f"{desk:.3f} of the height (y={int(desk * 1920)} at 1080x1920)")
    vign = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * 0.45) / (H / 1.6)) ** 2)
    vign = np.clip(vign, 0.7, 1)[..., None]
    rng = np.random.default_rng(1)

    def raw_alpha(fr):
        al = matte(sess, fr)
        if room is not None: al = np.maximum(al, diff_matte(fr, room, seen))  # hands, hair, arms the model misses
        return al

    def compose(fr, al, i=0):
        F0 = F = fr.astype(np.float32) / 255
        A = np.clip((al - 0.04) / 0.92, 0, 1)
        if room is not None:
            # edge decontamination: semi-transparent edges (hair) still carry the old wall's colour; with the empty room
            # known, solve I = A*F + (1-A)*R for F so the old wall never shows through as a grey rim
            e = ((A > 0.02) & (A < 0.98) & seen_full & (keep < 0.5 if keep is not None else True))[..., None]
            Ad = np.maximum(A, 0.15)[..., None]
            Fd = np.clip((F - (1 - A[..., None]) * R) / Ad, 0, 1)
            F = np.where(e, Fd, F)
        if keep is not None: A = np.maximum(A, keep)          # the desk and resting arms stay as filmed
        A = A[..., None]
        Fm = np.clip(F * gain_l * tint, 0, 1)                 # person relit toward the plate
        edge = np.clip(A * (1 - A) * 4, 0, 1)                 # light wrap on the edges
        Fm = Fm * (1 - a.wrap * edge) + P_wrap * (a.wrap * edge)
        comp = (Fm * A + P * (1 - A)) * vign
        if a.grain > 0:  # per-frame seed, so frames can be finished in parallel and still come out the same every run
            comp = comp + np.random.default_rng([1, i]).normal(0, a.grain / 255, (H, W, 1)).astype(np.float32)
        return F0, np.clip(comp, 0, 1)

    def composite(fr, prev):  # single frame (preview)
        al = raw_alpha(fr)
        F0, comp = compose(fr, al)
        return F0, comp, al

    if a.preview is not None:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a.preview:.2f}", "-i", src, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        _, comp, _ = composite(np.frombuffer(raw[: W * H * 3], np.uint8).reshape(H, W, 3), None)
        outp = os.path.join(a.job, "work", f"bg_preview_{a.preview:.1f}.png"); os.makedirs(os.path.dirname(outp), exist_ok=True)
        Image.fromarray((comp * 255 + 0.5).astype(np.uint8)).save(outp); print("preview:", outp); return

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-i", src, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-g", "15", "-c:a", "copy", "-shortest", out], stdin=subprocess.PIPE)
    # Temporal stabilisation with one frame of look-ahead: the median of (previous, current, next) alpha removes
    # single-frame dropouts (an arm vanishing for a frame) and single-frame false positives (a wall flash), then a
    # light blend with the previous result only where the matte is steady (no trailing halo when the head moves).
    def finish(i, fr, al):
        F, comp = compose(fr, al, i)
        if a.reveal is not None:
            t = i / FPS
            if t < a.reveal: comp = F
            elif t < a.reveal + a.wipe:  # soft left-to-right wipe
                p = (t - a.reveal) / a.wipe
                edge_x = p * (W + 200) - 100
                m = np.clip((edge_x - xx) / 100, 0, 1)[..., None]
                comp = comp * m + F * (1 - m)
        return (comp * 255 + 0.5).astype(np.uint8).tobytes()

    # Finishing a frame (relight, decontaminate, wrap, grain, wipe) is independent per frame and was ~40% of the time
    # on one core; it now runs on every core (numpy releases the GIL), and frames are written strictly in order.
    from collections import deque
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=max(1, min(12, (os.cpu_count() or 2))))
    pending = deque()

    def drain(limit):
        while len(pending) > limit:
            j, fut = pending.popleft()
            enc.stdin.write(fut.result())
            if j % 150 == 0: print(f"frame {j}", flush=True)

    def emit(i, fr, al):
        pending.append((i, pool.submit(finish, i, fr, al)))
        drain(2 * (pool._max_workers))

    def med3(x, y, z):  # median of three, elementwise (same result as np.median, ~10x faster)
        return np.maximum(np.minimum(x, y), np.minimum(np.maximum(x, y), z))

    buf, prev_out, i = [], None, -1
    ahead = deque()  # the matte (GPU/CPU model + difference matte) for the next frames runs in the pool too

    def alphas():
        for fr in frames(src):
            ahead.append((fr, pool.submit(raw_alpha, fr)))
            if len(ahead) > pool._max_workers:
                f0, fut = ahead.popleft(); yield f0, fut.result()
        while ahead:
            f0, fut = ahead.popleft(); yield f0, fut.result()

    for i, (fr, al_raw) in enumerate(alphas()):
        buf.append((fr, al_raw))
        if len(buf) < 2: continue
        if len(buf) > 3: buf.pop(0)
        idx = len(buf) - 2                       # the frame we can now finalise (it has a neighbour on each side, or is first)
        trio = [b[1] for b in buf]
        al = med3(*trio) if len(trio) == 3 else trio[idx]
        if prev_out is not None:
            w = 0.25 * np.clip(1 - np.abs(al - prev_out) * 4, 0, 1)
            al = al * (1 - w) + prev_out * w
        emit(i - 1, buf[idx][0], al); prev_out = al
    if buf:
        emit(i, buf[-1][0], buf[-1][1] if prev_out is None else np.maximum(buf[-1][1] * 0.75 + prev_out * 0.25, 0))
    drain(0); pool.shutdown()
    enc.stdin.close(); enc.wait()
    plan = os.path.join(a.job, "plan.json")
    if os.path.exists(plan):
        p = json.load(open(plan)); p["source"] = "source_bg.mp4"; json.dump(p, open(plan, "w"), ensure_ascii=False, indent=1)
    open(os.path.join(a.job, "work", "bg_quality"), "w").write("draft" if a.draft else "full")
    json.dump({"gain": gain_l, "tint": [float(x) for x in tint], "reveal": a.reveal, "desk": desk, "plate": os.path.abspath(a.plate), "blur": a.blur,
               "draft": a.draft}, open(os.path.join(a.job, "work", "bg_meta.json"), "w"), indent=1)  # for scripts/bg_qa.py
    print("background:", out)


if __name__ == "__main__":
    main()
