"""Render stills (approval gate 2) or the full video, then the finishing pass.

Usage:
  render.py stills <jobdir> [--plan plan.json] [--times 1.0,9.5,...]   -> <jobdir>/stills/sheet.jpg
  render.py video  <jobdir> [--plan plan.json] [--name NAME] [--res 360|540]  -> <jobdir>/out/NAME_draft540.mp4 (fast draft;
                                                                        --res 360 = third resolution, quickest look)
  render.py video  <jobdir> --final [--grain 0]                        -> <jobdir>/out/NAME.mp4 (full quality, final only)

The plan defaults to <jobdir>/plan.json. Set BROWSER_EXECUTABLE to use an existing Chrome/Chromium
headless shell; otherwise Remotion downloads its own headless shell into engine/node_modules.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(os.path.dirname(HERE), "engine")


def remotion(args, job, plan_path, guides=False):
    plan = json.load(open(plan_path))
    if guides:  # review overlay: non-safe zones + the tracked face
        plan["guides"] = True
        fp = os.path.join(job, "faces.json")
        if os.path.exists(fp): plan["faces"] = json.load(open(fp))
    props = os.path.join(job, "work", "props.json")
    os.makedirs(os.path.dirname(props), exist_ok=True)
    json.dump({"plan": plan}, open(props, "w"), ensure_ascii=False)
    cmd = ["npx", "--no-install", "remotion"] + args + ["--props", os.path.abspath(props), "--public-dir", os.path.abspath(os.path.join(job, "public")),
                                         "--log", "error",
                                         # keep memory bounded on small machines (decoded-frame cache)
                                         "--offthreadvideo-cache-size-in-bytes", str(512 * 1024 * 1024),
                                         "--offthreadvideo-video-threads", "2"]
    if os.environ.get("BROWSER_EXECUTABLE"):
        cmd += ["--browser-executable", os.environ["BROWSER_EXECUTABLE"]]
    if any(e.get("type") == "lightleak" for e in plan.get("elements", [])):
        cmd += ["--gl", "swangle"]  # WebGL effects on machines without a GPU
    subprocess.run(cmd, cwd=ENGINE, check=True)
    return plan


def key_times(plan):
    ts = set()
    for e in plan.get("elements", []):
        if e.get("type") in ("sfx", "punchin", "lightleak"):
            continue
        a, b = e.get("start", 0), e.get("end", e.get("start", 0) + 1)
        ts.add(round(a + min(0.8, (b - a) / 2), 2))
        if e.get("reveal"):
            ts.add(round(e["reveal"]["at"] + 0.6, 2))
    return sorted(ts)[:12] or [1.0]


def stills(job, plan_path, times, guides=True):
    from PIL import Image
    plan = json.load(open(plan_path))
    times = times or key_times(plan)
    sd = os.path.join(job, "stills"); os.makedirs(sd, exist_ok=True)
    paths = []
    for t in times:
        f = int(t * plan.get("fps", 30)); p = os.path.abspath(os.path.join(sd, f"t{t:06.2f}.png"))
        remotion(["still", "src/index.jsx", "Main", p, f"--frame={f}"], job, plan_path, guides)
        paths.append((t, p))
    w, h, cols = 324, 576, 4
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows), "white")
    for i, (t, p) in enumerate(paths):
        sheet.paste(Image.open(p).convert("RGB").resize((w, h)), ((i % cols) * w, (i // cols) * h))
    out = os.path.join(sd, "sheet.jpg"); sheet.save(out, quality=85)
    print("stills:", out, "times:", times)


def music_dips(plan):
    """Silence beats: {"type": "silence", "at": t, "duration": d} dips the music ~9 dB with 150 ms ramps."""
    terms = []
    for e in plan.get("elements", []):
        if e.get("type") != "silence": continue
        a, b = float(e["at"]), float(e["at"]) + float(e.get("duration", 1.0))
        terms.append(f"(1-0.65*clip(min((t-{a:.3f})/0.15,({b:.3f}-t)/0.15),0,1))")
    return f",volume='{'*'.join(terms)}':eval=frame" if terms else ""


def loudnorm_2pass(src_wav, dst, target=-14.0, tp=-1.0):
    """Measure, then normalise with the measured values (accurate to about 0.5 LU, unlike one pass)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src_wav, "-af", f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,"
          f"alimiter=limit={10 ** ((tp - 0.3) / 20):.3f}:level=0")  # level=0: no auto make-up gain (it pushed output ~1.3 LU over target)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src_wav, "-af", af, "-ar", "48000", dst], check=True)
    print(f"loudness: measured {j['input_i']} LUFS -> {target} LUFS, true peak <= {tp} dBTP")


# default music bed per theme (engine/src/lib/theme.js SERIES_LOOK.bed)
SERIES_BED = {"light": "warm", "dark": "calm", "bold": "pulse"}


def add_music(master, plan, job):
    """Mix the generated music bed (scripts/make_music.py, original, claim-free) under the master audio.
    With a voice (talking-head / voice modes) the music ducks under speech; in text mode it plays at full bed level.
    Silence elements dip the music; the mix is then normalised in two passes to -14 LUFS / -1 dBTP."""
    m = plan["music"] if isinstance(plan["music"], dict) else ({} if plan["music"] is True else {"style": str(plan["music"])})
    if not m.get("style"):
        # no style in the plan: the series picks its bed (it matches the series sound logo); a plan style still wins
        m = {**m, "style": SERIES_BED.get(plan.get("theme"), "calm")}
    wav = os.path.join(job, "work", f"music_{m.get('style', 'calm')}_{m.get('seed', 1)}.wav")
    if not os.path.exists(wav):
        subprocess.run([sys.executable, os.path.join(HERE, "make_music.py"), wav, "--duration", str(plan["duration"]),
                        "--style", m.get("style", "calm"), *(["--bpm", str(m["bpm"])] if m.get("bpm") else (["--bpm", str({"pulse": 100}.get(m.get("style"), 80))]
                          if m.get("style") in ("calm", "warm", "pulse") else [])),
                        *(["--key", m["key"]] if m.get("key") else []), "--seed", str(m.get("seed", 1))], check=True)
    voiced = plan.get("mode") != "text"
    bed_db = m.get("level", -32 if voiced else -17)  # bed level before ducking (voice ~-14: >= 18 dB under it)
    dips = music_dips(plan)
    if voiced:
        fc = (f"[1:a]loudnorm=I={bed_db}:TP=-6:LRA=7{dips}[bed];[0:a]asplit=2[v][key];"
              "[bed][key]sidechaincompress=threshold=0.02:ratio=8:attack=150:release=400:makeup=1[duck];"
              "[v][duck]amix=inputs=2:normalize=0:duration=first[a]")
    else:
        fc = f"[1:a]loudnorm=I={bed_db}:TP=-1.5:LRA=7{dips}[bed];[0:a][bed]amix=inputs=2:normalize=0:duration=first[a]"
    raw = master.replace(".mp4", "_mix.wav"); norm = master.replace(".mp4", "_norm.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-i", wav, "-filter_complex", fc, "-map", "[a]", raw], check=True)
    loudnorm_2pass(raw, norm)
    mixed = master.replace(".mp4", "_music.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-i", norm, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", mixed], check=True)
    for f in (master, raw, norm): os.remove(f)
    return mixed


def srt_time(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def insert_shift(plan, t):
    """Seconds that inserts (bumpers.py) add before time t of the rendered video."""
    fps = plan.get("fps", 30); sh = 0.0
    for ins in plan.get("inserts") or []:
        if t >= ins["at"] - 1e-6:
            sh += ins.get("duration") or ffdur(os.path.join(plan["_job"], "public", ins["src"]))
    return sh


def ffdur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets,r_frame_rate", "-of", "json", path], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return int(s["nb_read_packets"]) * int(d) / int(n)


def write_srt(plan, od, name, offset=0.0):
    """Captions as .srt files next to the video (YouTube / LinkedIn uploads, accessibility)."""
    for key, lang in (("text", plan.get("lang")), ("text2", plan.get("lang2"))):
        cues = [c for c in plan.get("captions", []) if c.get(key)]
        if not cues or not lang: continue
        path = os.path.join(od, f"{name}.{lang}.srt")
        with open(path, "w", encoding="utf-8") as f:
            for i, c in enumerate(cues, 1):
                sh = offset + insert_shift(plan, c["start"])
                f.write(f"{i}\n{srt_time(c['start'] + sh)} --> {srt_time(c['end'] + sh)}\n{c[key]}\n\n")
        print("captions:", path)


def video(job, plan_path, name, grain, final_quality=False, res=540):
    """Draft by default: 540x960 (half resolution, about 480p class), fast, for review. --final: full 1080x1920 at the highest practical quality."""
    od = os.path.join(job, "out"); os.makedirs(od, exist_ok=True)
    q = os.path.join(job, "work", "bg_quality")
    if final_quality and os.path.exists(q) and open(q).read().strip() == "draft":
        raise SystemExit("The background was processed in draft mode. Re-run scripts/background.py without --draft before --final.")
    tag = "" if final_quality else f"_draft{res}"
    master = os.path.abspath(os.path.join(od, f"{name}{tag}_master.mp4"))
    if final_quality:
        args = ["--codec", "h264", "--crf", "14", "--audio-bitrate", "320k", "--jpeg-quality", "95"]
    else:
        args = ["--codec", "h264", "--crf", "26", "--audio-bitrate", "128k", "--scale", str(1 / 3 if res == 360 else 0.5), "--jpeg-quality", "75"]
    remotion(["render", "src/index.jsx", "Main", master] + args + ["--concurrency", str(max(1, (os.cpu_count() or 2)))], job, plan_path)
    out = os.path.join(od, f"{name}{tag}.mp4")
    plan = json.load(open(plan_path)); plan["_job"] = job
    if plan.get("music"):
        master = add_music(master, plan, job)
    b = plan.get("bumpers") or {}
    op = b.get("opener")
    # captions move by what is joined in front of the video (opener + 2 s intro)
    write_srt(plan, od, name, ((float(op["end"]) - float(op["start"])) if op else 0.0) + (2.0 if b and b.get("intro", True) and b.get("intro") != "overlay" else 0.0))
    if plan.get("bumpers") or plan.get("inserts"):
        # opener (the video's catchphrase) -> 2 s brand intro -> the video -> 3 s outro; checks lip sync on the joined file
        full = os.path.join(od, f"{name}_full{tag}_tmp_src.mp4"); os.replace(master, full)
        subprocess.run([sys.executable, os.path.join(HERE, "bumpers.py"), job, "--video", full, "--plan", plan_path,
                        "--name", f"{name}{tag}_bumpered"], check=True)
        master = os.path.join(od, f"{name}{tag}_bumpered.mp4"); os.replace(full, os.path.join(od, f"{name}{tag}_core.mp4"))
    check_streams(master)
    if final_quality:
        # Finishing pass: optional light film grain, then a high-quality delivery encode
        # (1080x1920, H.264 high profile, slow preset, CRF 16, peaks capped so platforms accept it, faststart).
        vf = f"noise=alls={grain}:allf=t" if grain > 0 else "null"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                        "-profile:v", "high", "-maxrate", "20M", "-bufsize", "40M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k",
                        "-movflags", "+faststart", out], check=True)
        os.remove(master)
        social(out, os.path.join(od, f"{name}_social.mp4"))
    else:
        os.replace(master, out)
    print("video:", out, "(final quality)" if final_quality else f"({res}p-class draft)")


def check_streams(path, tol=0.05):
    """Sound and picture must be the same length; a mismatch is how drift (voice not matching his lips) shows up."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    d = {s["codec_type"]: float(s.get("duration", 0)) for s in json.loads(r.stdout)["streams"]}
    if "audio" in d and "video" in d and abs(d["audio"] - d["video"]) > tol:
        raise SystemExit(f"{path}: audio {d['audio']:.3f}s vs video {d['video']:.3f}s - out of sync, do not deliver.")
    print(f"streams ok: video {d.get('video', 0):.2f}s, audio {d.get('audio', 0):.2f}s")


def social(src, dst):
    """Upload copy for social apps: same picture at about 10 Mbps (well under Instagram's ~300 MB API limit for a few
    minutes of video) and the audio re-measured and normalised in two passes on the FINAL file, so the delivered copy
    is -14 LUFS / -1 dBTP even if the master drifted (the final master once measured -12.7 LUFS)."""
    wav = dst.replace(".mp4", "_a.wav"); norm = dst.replace(".mp4", "_an.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", "48000", wav], check=True)
    loudnorm_2pass(wav, norm)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", norm, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-maxrate", "10M", "-bufsize", "20M",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", dst], check=True)
    for f in (wav, norm): os.remove(f)
    print("social copy:", dst, f"({os.path.getsize(dst) / 1e6:.0f} MB)")


def caption_sheet(job, plan_path, video_path=None):
    """One still per caption. Frames come from the draft video (cheap) at the moment each cue is fully lit; each
    tile is the caption band (y 860-1460) with the cue number, so a wrapped or overlapping line is easy to spot."""
    from PIL import Image, ImageDraw
    plan = json.load(open(plan_path)); plan["_job"] = job
    if not video_path:
        outs = sorted(glob.glob(os.path.join(job, "out", "*.mp4")), key=os.path.getmtime)
        if not outs: raise SystemExit("no draft in <job>/out; render the draft first (render.py video <job>) or pass --video")
        video_path = outs[-1]
    off = 0.0
    bump = plan.get("bumpers") or {}
    if bump.get("opener"): off += bump["opener"]["end"] - bump["opener"]["start"]
    if bump and bump.get("intro", True) and bump.get("intro") != "overlay": off += 2.0   # same offset as the .srt files
    W = ffdur(video_path); od = os.path.join(job, "stills", "captions"); os.makedirs(od, exist_ok=True)
    tiles = []
    for i, c in enumerate(plan["captions"]):
        t = max(c["start"] + 0.05, c["end"] - 0.12) + off + insert_shift(plan, c["start"])
        if t >= W: continue
        f = os.path.join(od, f"c{i:03d}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video_path, "-frames:v", "1", "-vf", "scale=1080:1920", f], check=True)
        im = Image.open(f).convert("RGB").crop((0, 860, 1080, 1460)).resize((540, 300))
        ImageDraw.Draw(im).text((8, 6), f"#{i}  {c['start']:.1f}s", fill=(255, 80, 80))
        tiles.append(im)
    cols = 4; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (540 * cols, 300 * rows), "black")
    for k, im in enumerate(tiles): sheet.paste(im, ((k % cols) * 540, (k // cols) * 300))
    out = os.path.join(job, "stills", "captions_sheet.jpg"); sheet.save(out, quality=82)
    print("caption sheet:", out, f"({len(tiles)} cues from {os.path.basename(video_path)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["stills", "video", "captions"]); ap.add_argument("job")
    ap.add_argument("--plan"); ap.add_argument("--times"); ap.add_argument("--name", default="final")
    ap.add_argument("--grain", type=int, default=0)
    ap.add_argument("--res", type=int, choices=[360, 540], default=540, help="draft resolution (short side)")
    ap.add_argument("--clean-stills", action="store_true", help="stills without the safe-zone/face guides")
    ap.add_argument("--final", action="store_true", help="full 1080x1920 highest quality; only for the approved final version")
    ap.add_argument("--video", help="captions: the draft to take the frames from (default: the newest <job>/out/*.mp4)")
    a = ap.parse_args()
    plan = a.plan or os.path.join(a.job, "plan.json")
    if a.what == "captions":
        caption_sheet(a.job, plan, a.video)
    elif a.what == "stills":
        stills(a.job, plan, [float(x) for x in a.times.split(",")] if a.times else None, not a.clean_stills)
    else:
        video(a.job, plan, a.name, a.grain, a.final, a.res)


if __name__ == "__main__":
    main()
