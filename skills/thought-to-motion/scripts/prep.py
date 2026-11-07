"""Prepare a job: normalise the media, cut long pauses, transcribe with word timings.

Usage:
  prep.py <media> <jobdir> [--mode talking-head|voice] [--lang he|en|auto] [--no-cut] [--pause 0.45] [--clean gentle|full|off]
          [--no-protect] [--tight]
The cut keeps every word Whisper hears (silences at -40 dB + word spans) and, in talking-head, 1-2 s of quiet head and
tail up to where he reaches for the phone. --no-protect / --tight bring back the old cut.

Writes:
  <jobdir>/public/source.mp4   (talking-head: 1080x1920 H.264 30fps, pauses cut, loudness -14 LUFS)
  <jobdir>/public/voice.wav    (voice mode: the audio, pauses cut, loudness -14 LUFS)
  <jobdir>/public/sfx/*.wav    (the local sound kit)
  <jobdir>/transcript.json     (language + segments with word timings, on the CUT timeline)
  <jobdir>/job.json            (mode, duration, source file)
Everything runs locally. Nothing is uploaded.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run(args):
    subprocess.run(args, check=True)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:stream_side_data=rotation:format=duration",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def silences(wav, noise_db=-32, min_dur=0.45):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(st, en))


def keep_ranges(sil, dur, pad=0.12):
    keep, cur = [], 0.0
    for s, e in sil:
        if s <= 0.05:
            cur = max(cur, e - pad); continue
        a, b = s + pad, e - pad
        if e >= dur - 0.05: a = min(dur, s + 0.8)   # the final silence: let the last word finish and breathe (no abrupt end)
        if a > cur: keep.append([cur, a])
        cur = max(cur, b)
    if cur < dur - 0.2: keep.append([cur, dur])
    return [k for k in keep if k[1] - k[0] > 0.15]


def protect_words(keep, words, dur, pad=0.08, merge=0.25):
    """Word-protected cut. Silences come from a
    stricter -40 dB threshold; every Whisper word span (padded) is added back; gaps under `merge` s are closed."""
    spans = [[max(0.0, w["s"] - pad), min(dur, w["e"] + pad)] for w in words if w["e"] > w["s"]]
    allr = sorted([list(k) for k in keep] + spans)
    out = []
    for s, e in allr:
        if out and s - out[-1][1] < merge: out[-1][1] = max(out[-1][1], e)
        else: out.append([s, e])
    return out


def motion_curve(video, t0, t1, fps=10):
    """Mean frame difference (0-255) per frame between t0 and t1, at 64 px wide. Big values = the phone moving."""
    import numpy as np
    if t1 - t0 < 0.2: return []
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", video, "-t", f"{t1 - t0:.3f}", "-vf", f"fps={fps},scale=64:114,format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    if a.size < 2 * 64 * 114: return []
    a = a[: a.size // (64 * 114) * 64 * 114].reshape(-1, 114, 64).astype(np.float32)
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    return [(t0 + (i + 1) / fps, float(x)) for i, x in enumerate(d)]


def head_tail(keep, words, video, dur, lo=0.8, hi=2.0):
    """Head and tail "like in cinema": keep the 1-2 quiet seconds before he starts talking (a
    glance, a breath) and after he finishes. Cut only where he reaches for the phone: the last big camera move before
    the first word / the first one after the last word (else 1.5 s)."""
    if not words or not keep: return keep
    w0, w1 = words[0]["s"], words[-1]["e"]
    head = max(0.0, w0 - 1.5)
    mv = motion_curve(video, max(0.0, w0 - hi - 1.0), w0) if video else []
    big = [t for t, x in mv if x > 9.0 and t <= w0 - lo]
    if big: head = max(w0 - hi, min(w0 - lo, big[-1] + 0.1))
    tail = min(dur, w1 + 1.5)
    mv = motion_curve(video, w1, min(dur, w1 + hi + 1.0)) if video else []
    big = [t for t, x in mv if x > 9.0 and t >= w1 + lo]
    if big: tail = min(dur, max(w1 + lo, min(w1 + hi, big[0] - 0.1)))
    # the quiet lead-in and lead-out stay whole (no pause cut inside them), up to the phone moves
    out = [[s, e] for s, e in keep if e > w0 - 0.05 and s < w1 + 0.05]
    if not out: return keep
    out[0][0] = head; out[-1][1] = tail
    return [[round(s, 3), round(e, 3)] for s, e in out]


def clean_plate(video, out_png, probe_s=12.0, fps=5, min_empty=1.0):
    """If the clip opens on the empty room (locked camera; the speaker walks in later), the opening frames stay
    still apart from sensor noise. The run of frames that match the first one is the empty room: their median
    is the clean plate. Returns the time the empty opening ends (0 if the clip does not open on an empty room)."""
    import numpy as np
    from PIL import Image
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-t", str(probe_s), "-i", video, "-vf", f"fps={fps}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n, empty, ref = 1080 * 1920 * 3, [], None
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        fr = np.frombuffer(b, np.uint8).reshape(1920, 1080, 3)
        small = np.asarray(Image.fromarray(fr).resize((135, 240), Image.BILINEAR), np.int16)
        if ref is None: ref = small
        changed = (np.abs(small - ref).max(-1) > 28).mean()     # share of the picture that changed vs the first frame
        if changed > 0.004: break                               # someone (or something) entered
        empty.append(fr)
    p.kill()
    t = len(empty) / fps
    if t < min_empty:
        return 0.0
    Image.fromarray(np.median(np.stack(empty[: max(1, len(empty) - 1)]), 0).astype(np.uint8)).save(out_png)
    print(f"clean plate: the clip opens on the empty room for {t:.1f}s -> {out_png}")
    return t


def sync_check_cut(full, joined, keep, fps, tol=0.02, max_offset=0.045):
    """After cutting: the sound of every 3rd kept piece must sit where its picture starts. Measured by correlating the
    RAW waveform over a 2.5 s window. A constant offset shared by all pieces is the reference file's AAC priming delay
    (1024 samples = ~21 ms at 48 kHz), not a cut error, so pieces are judged against the median lag."""
    import numpy as np

    def pcm(p, t, d):
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", p, "-t", f"{d:.3f}", "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "f32le", "-"], capture_output=True, check=True)
        return np.frombuffer(r.stdout, np.float32)
    pos, lags = 0.0, []
    W, S = 2.5, 0.25                                    # reference window, search +- S
    for i, (s, e) in enumerate(keep):
        d = round((e - s) * fps) / fps
        if i % 3 == 0 and d > 1.0 and pos > S + 0.1:
            w = min(W, d - 0.1)
            ref = pcm(full, s + 0.05, w); got = pcm(joined, pos + 0.05 - S, w + 2 * S)
            if ref.std() > 1e-3 and len(got) > len(ref):
                a = ref - ref.mean(); b = got - got.mean()
                c = np.correlate(b, a, "valid")
                # normalise by the local energy so a loud passage doesn't win over the true alignment
                en = np.sqrt(np.convolve(b * b, np.ones(len(a)), "valid")) + 1e-9
                k = int(np.argmax(c / en)); lags.append(k / 16000 - S)
        pos += d
    if not lags:
        return
    med = float(np.median(lags)); worst = max(abs(l - med) for l in lags)
    if worst > tol or abs(med) > max_offset:
        raise SystemExit(f"cut is out of sync: pieces drift {worst * 1000:.0f} ms, constant offset {med * 1000:.0f} ms (raw-waveform check, {len(lags)} pieces)")
    print(f"cut sync ok: worst {worst * 1000:.0f} ms over {len(lags)} pieces (raw waveform)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media"); ap.add_argument("job")
    ap.add_argument("--mode", choices=["talking-head", "voice"]); ap.add_argument("--lang", default="auto")
    ap.add_argument("--no-cut", action="store_true"); ap.add_argument("--pause", type=float, default=0.45)
    ap.add_argument("--clean", choices=["gentle", "full", "off"], default="gentle", help="speech cleanup strength")
    ap.add_argument("--no-protect", action="store_true", help="old cut: -32 dB silences only (can drop quiet words)")
    ap.add_argument("--tight", action="store_true", help="old head/tail: start on the first word, end 0.8 s after the last")
    a = ap.parse_args()

    pub = os.path.join(a.job, "public"); work = os.path.join(a.job, "work")
    os.makedirs(pub, exist_ok=True); os.makedirs(work, exist_ok=True)
    info = probe(a.media)
    has_video = any(s["codec_type"] == "video" for s in info["streams"])
    mode = a.mode or ("talking-head" if has_video else "voice")
    dur = float(info["format"]["duration"])

    # 1) normalise to an intermediate (rotation is applied by ffmpeg automatically)
    if mode == "talking-head":
        inter = os.path.join(work, "full.mp4")
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"
        run(["ffmpeg", "-v", "error", "-y", "-i", a.media, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-g", "15", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", inter])
    else:
        inter = os.path.join(work, "full.wav")
        run(["ffmpeg", "-v", "error", "-y", "-i", a.media, "-vn", "-ac", "2", "-ar", "48000", inter])
    # 1b) clean plate: if the clip opens on the empty room (the speaker walks in after a few seconds), keep a
    #     median of those empty frames as the exact background reference for background.py, and start the cut after it
    lead_end = 0.0
    if mode == "talking-head":
        lead_end = clean_plate(inter, os.path.join(work, "clean_plate.png"))
    mono = os.path.join(work, "full16k.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", inter, "-vn", "-ac", "1", "-ar", "16000", mono])

    # 2) cut long pauses segment by segment (low memory), then join
    if a.no_cut:
        keep = [[0.0, dur]]
    elif a.no_protect:
        keep = keep_ranges(silences(mono, min_dur=a.pause), dur)
    else:
        # word-protected cut: silences at -40 dB, union with the words Whisper hears, gaps < 0.25 s merged
        keep = keep_ranges(silences(mono, noise_db=-40, min_dur=a.pause), dur)
        full_tr = os.path.join(work, "full_transcript.json")
        run([sys.executable, os.path.join(HERE, "transcribe.py"), mono, full_tr, "--lang", a.lang])
        words = [w for sg in json.load(open(full_tr))["segments"] for w in sg["words"]]
        keep = protect_words(keep, words, dur)
        if not a.tight and mode == "talking-head":
            keep = head_tail(keep, words, inter, dur)
        print(f"cut: {len(keep)} pieces, {sum(e - s for s, e in keep):.1f} of {dur:.1f} s kept (words protected"
              + ("" if a.tight else ", cinema head/tail") + ")")
    if lead_end > 0:  # never keep the empty-room opening (or the walk-in before the first word)
        keep = [[max(s, lead_end), e] for s, e in keep if e > lead_end + 0.1]
    json.dump(keep, open(os.path.join(a.job, "keep.json"), "w"))
    seg_dir = os.path.join(work, "seg"); os.makedirs(seg_dir, exist_ok=True)
    ext = "mov" if mode == "talking-head" else "wav"
    # Lip sync: every kept piece is cut on whole frames and its sound is cut or padded to exactly
    # the picture's length, kept as PCM (AAC adds ~21 ms of priming per piece). The old cut lost a few ms of sound per
    # piece and the voice drifted up to ~0.5 s behind his lips by the end of a 50 s video.
    FPS = 30
    keep = [[round(s * FPS) / FPS, round(e * FPS) / FPS] for s, e in keep]
    keep = [[s, e] for s, e in keep if e - s >= 2 / FPS]
    json.dump(keep, open(os.path.join(a.job, "keep.json"), "w"))
    with open(os.path.join(seg_dir, "list.txt"), "w") as lst:
        for i, (s, e) in enumerate(keep):
            out = os.path.join(seg_dir, f"s{i:03d}.{ext}")
            n = round((e - s) * FPS); d = n / FPS
            af = f"afade=t=in:d=0.02,afade=t=out:st={max(d - 0.03, 0):.3f}:d=0.03"
            if mode == "talking-head":
                run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.4f}", "-i", inter, "-t", f"{d + 0.2:.4f}",
                     "-af", f"apad,atrim=0:{d:.6f},{af}", "-frames:v", str(n),
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                     "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", out])
            else:
                run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-i", inter, "-t", f"{e - s:.3f}", "-af", af, out])
            lst.write(f"file '{os.path.basename(out)}'\n")
    final = os.path.join(pub, "source.mp4" if mode == "talking-head" else "voice.wav")
    joined = os.path.join(work, "joined." + ext)
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(seg_dir, "list.txt"), "-c", "copy", joined])
    if mode == "talking-head":
        sync_check_cut(inter, joined, keep, FPS)
    # 3) speech cleanup: DeepFilterNet3 + studio chain + -14 LUFS (see clean_audio.py)
    sys.path.insert(0, HERE)
    from clean_audio import clean
    cleaned = os.path.join(work, "clean.wav")
    clean(joined, cleaned, a.clean)
    if mode == "talking-head":
        run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", cleaned, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", final])
    else:
        shutil.copy(cleaned, final)
    cut_dur = float(probe(final)["format"]["duration"])

    # 3) sound kit
    sfx_src = os.path.join(ROOT, "engine", "sfx")
    if os.path.isdir(sfx_src):
        shutil.copytree(sfx_src, os.path.join(pub, "sfx"), dirs_exist_ok=True)

    # 4) transcribe the CUT audio, so timings match the final timeline
    cut16 = os.path.join(work, "cut16k.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", final, "-vn", "-ac", "1", "-ar", "16000", cut16])
    run([sys.executable, os.path.join(HERE, "transcribe.py"), cut16, os.path.join(a.job, "transcript.json"), "--lang", a.lang])

    # 5) talking-head: track the face so the validator can keep content off it
    if mode == "talking-head":
        run([sys.executable, os.path.join(HERE, "faces.py"), a.job])

    job = {"mode": mode, "source": os.path.basename(final), "duration": round(cut_dur, 3), "original_duration": round(dur, 3),
           "fps": 30, "kept_ranges": len(keep)}
    json.dump(job, open(os.path.join(a.job, "job.json"), "w"), indent=1)
    print(json.dumps(job))


if __name__ == "__main__":
    main()
