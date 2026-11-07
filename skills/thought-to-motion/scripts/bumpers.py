"""Wrap a rendered video in the brand's opener, intro and outro.

Order: video catchphrase (about 2 s, cut from the video itself) -> brand intro (2 s)
-> the full video -> brand outro (3 s). No video opens on a logo.

Plan keys (all optional except what you want to use):
  "bumpers": {
    "opener": {"start": 20.7, "end": 23.2, "text": "...", "text2": "...", "emph": "...", "words": [{"w": "...", "s": 20.74}]},
              # with "text": the edited opener template (footage + push-in + the line in big kinetic type, nothing else);
              # without it: a plain cut from the rendered video.   # the video catchphrase: his own line, cut from the video; end in the pause after the last word (check the audio, transcript times can be 0.3 s early)
    "intro": true, "outro": true,
    "catchphrase": "Your brand line", "catchphrase2": null,   # brand line, a title: no full stop; 2nd line = smaller translation
    "follow": "Follow", "handle": "@yourhandle",
    "platforms": "LinkedIn · Instagram · TikTok · Threads · YouTube"
  },
  "inserts": [{"at": 46.133, "src": "clip.mp4", "kicker": "One photo · 1.5 minutes", "headline": "Here's what it made.",
               "quote": "A line from the clip", "tag": "AI-generated clip"}]
              # a card that pauses the video at `at` (seconds of the rendered video) to play one of his own clips with its own
              # sound, dressed by the series (Bumper "insert"). The video picks up again right after; captions move with it.
Usage:
  bumpers.py <job> --video out/NAME_draft540.mp4 [--plan plan.json] [--name NAME_bumpers]
The video's resolution decides the bumpers' resolution (drafts stay drafts). Writes out/<name>.mp4 at -14 LUFS / -1 dBTP.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import loudnorm_2pass, remotion  # noqa: E402

LOGO_GAIN_DB = -3.0  # sound logo level against the -6 dBFS peak it is written at


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], round(int(n) / int(d))


def render_bumper(job, plan, kind, width, work):
    b = plan.get("bumpers", {})
    brand = dict(plan.get("brand", {}))
    brand["catchphrase"] = b.get("catchphrase", brand.get("catchphrase", "Your brand line"))
    if b.get("catchphrase2"): brand["catchphrase2"] = b["catchphrase2"]
    if b.get("handle"): brand["handle"] = b["handle"]
    bp = {"kind": kind, "theme": plan.get("theme"), "lang": plan.get("lang"), "fps": plan.get("fps", 30),
          "duration": 3.0 if kind == "outro" else 2.0, "brand": brand,
          "follow": b.get("follow"), "platforms": b.get("platforms"), "themeOverrides": plan.get("themeOverrides")}
    bp = {k: v for k, v in bp.items() if v is not None}
    pp = os.path.join(work, f"bumper_{kind}.json"); json.dump(bp, open(pp, "w"), ensure_ascii=False)
    silent = os.path.abspath(os.path.join(work, f"bumper_{kind}_v.mp4"))
    args = ["render", "src/index.jsx", "Bumper", silent, "--codec", "h264", "--crf", "16", "--muted"]
    if width < 1080: args += ["--scale", str(width / 1080)]
    remotion(args, job, pp)
    logo = os.path.join(work, f"logo_{kind}.wav")
    subprocess.run([sys.executable, os.path.join(HERE, "sound_logo.py"), logo, "--kind", kind, "--theme", plan.get("theme", "bold"),
                    "--duration", str(bp["duration"])], check=True)
    out = os.path.join(work, f"bumper_{kind}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", logo, "-filter_complex", f"[1:a]volume={LOGO_GAIN_DB}dB[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "pcm_s16le", "-shortest", out.replace(".mp4", ".mov")], check=True)
    return out.replace(".mp4", ".mov")


def vdur(path):
    """Exact picture length (frames / fps) - every part's audio is cut or padded to this, so joins never drift."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets,r_frame_rate", "-of", "json", path], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return int(s["nb_read_packets"]) * int(d) / int(n)


def pcm(path, start, dur, sr=16000):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", path, "-t", f"{dur:.3f}", "-vn", "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32)


def sync_check(out, video, offset, n=5, win=3.0, t0=0.0, t1=None):
    """Lip sync check: the voice inside the joined file must sit exactly where it sits in the rendered video
    (Remotion renders picture and sound together, so matching the video's audio = matching his lips).
    Cross-correlates n windows of the video's [t0, t1] (placed at `offset` + t in the joined file); fails if any is off
    by more than 20 ms (about half a frame)."""
    import numpy as np
    total = (t1 if t1 is not None else vdur(video)) - t0; worst = 0.0
    if total < win + 2.5: return
    for k in range(n):
        t = t0 + 1.0 + (total - win - 2.0) * k / max(1, n - 1)
        a = pcm(video, t, win); b = pcm(out, offset + t - 0.25, win + 0.5)
        if np.abs(a).max() < 1e-3: continue
        c = np.correlate(b, a, mode="valid"); lag = (int(np.argmax(c)) / 16000.0) - 0.25
        worst = max(worst, abs(lag)); print(f"sync at {t:6.1f}s: {lag * 1000:+.1f} ms")
    if worst > 0.02: raise SystemExit(f"Audio/video out of sync by {worst * 1000:.0f} ms - do not deliver.")
    print(f"sync ok: worst {worst * 1000:.1f} ms")


def render_insert(job, plan, ins, k, width, work):
    """One insert card (Bumper kind "insert") with the clip's own sound, levelled to sit with his voice (-16 LUFS)."""
    src = os.path.join(job, "public", ins["src"]); dur = vdur(src)
    bp = {"kind": "insert", "theme": plan.get("theme"), "lang": plan.get("lang"), "fps": plan.get("fps", 30), "duration": round(dur, 3),
          "brand": plan.get("brand", {}), "themeOverrides": plan.get("themeOverrides"), "look": plan.get("look"),
          **{x: ins[x] for x in ("src", "kicker", "headline", "quote", "tag", "clipBox") if ins.get(x)}}
    bp = {x: v for x, v in bp.items() if v is not None}
    pp = os.path.join(work, f"insert_{k}.json"); json.dump(bp, open(pp, "w"), ensure_ascii=False)
    raw = os.path.abspath(os.path.join(work, f"insert_{k}_raw.mp4"))
    args = ["render", "src/index.jsx", "Bumper", raw, "--codec", "h264", "--crf", "16"]
    if width < 1080: args += ["--scale", str(width / 1080)]
    remotion(args, job, pp)
    out = os.path.join(work, f"insert_{k}.mov")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
                    "-c:v", "copy", "-c:a", "pcm_s16le", "-ac", "2", out], check=True)
    return out


def cut_opener(video, start, end, work):
    out = os.path.join(work, "bumper_opener.mov")
    d = end - start
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", video, "-t", f"{d:.3f}",
                    "-af", f"afade=t=in:d=0.04,afade=t=out:st={max(0, d - 0.15):.3f}:d=0.15",
                    "-c:v", "libx264", "-crf", "16", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", out], check=True)
    return out


def styled_opener(job, plan, video, width, work):
    """The edited opener (same template every video): his footage + voice for the line, slow push-in,
    the line in big kinetic type, no header / bar / other elements. Needs opener.text (+ text2, emph, words)."""
    o = dict(plan["bumpers"]["opener"]); start, end = float(o["start"]), float(o["end"])
    o.setdefault("src", plan.get("source")); o["from"] = start
    o["words"] = [{"w": w["w"], "s": round(float(w["s"]) - start, 3)} for w in o.get("words", [])]
    bp = {"kind": "opener", "theme": plan.get("theme"), "lang": plan.get("lang"), "fps": plan.get("fps", 30),
          "duration": end - start, "opener": o, "themeOverrides": plan.get("themeOverrides")}
    bp = {k: v for k, v in bp.items() if v is not None}
    pp = os.path.join(work, "bumper_opener.json"); json.dump(bp, open(pp, "w"), ensure_ascii=False)
    silent = os.path.abspath(os.path.join(work, "bumper_opener_v.mp4"))
    args = ["render", "src/index.jsx", "Bumper", silent, "--codec", "h264", "--crf", "16", "--muted"]
    if width < 1080: args += ["--scale", str(width / 1080)]
    remotion(args, job, pp)
    cut = cut_opener(video, start, end, work)  # his voice (and the bed) for the same seconds
    out = os.path.join(work, "bumper_opener_styled.mov")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", cut, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "pcm_s16le", "-shortest", out], check=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("--video", required=True); ap.add_argument("--plan"); ap.add_argument("--name")
    a = ap.parse_args()
    job = a.job; plan = json.load(open(a.plan or os.path.join(job, "plan.json")))
    video = a.video if os.path.isabs(a.video) else os.path.join(job, a.video)
    b = plan.get("bumpers", {})
    work = os.path.join(job, "work"); os.makedirs(work, exist_ok=True)
    w, h, fps = probe(video)
    parts = []
    if b.get("opener"):
        op = b["opener"]
        parts.append(styled_opener(job, plan, video, w, work) if op.get("text") else
                     cut_opener(video, float(op["start"]), float(op["end"]), work))
    has = bool(plan.get("bumpers"))
    if has and b.get("intro", True): parts.append(render_bumper(job, plan, "intro", w, work))
    parts = [(p, 0.0, vdur(p)) for p in parts]
    # the video itself, split where inserts pause it (cut on whole frames)
    vtotal = vdur(video); prev = 0.0; core = []
    for k, ins_ in enumerate(sorted(plan.get("inserts") or [], key=lambda x: x["at"])):
        at = round(float(ins_["at"]) * fps) / fps
        core.append(len(parts)); parts.append((video, prev, at - prev))
        card = render_insert(job, plan, ins_, k, w, work); parts.append((card, 0.0, vdur(card))); prev = at
    core.append(len(parts)); parts.append((video, prev, vtotal - prev))
    if has and b.get("outro", True):
        o = render_bumper(job, plan, "outro", w, work); parts.append((o, 0.0, vdur(o)))
    ins, fc = [], ""
    durs = [d for _, _, d in parts]
    for i, (p, st, d) in enumerate(parts):
        ins += ["-i", p]
        fc += (f"[{i}:v]scale={w}:{h},fps={fps},setsar=1,format=yuv420p,trim=start={st:.4f}:duration={d:.4f},setpts=PTS-STARTPTS[v{i}];"
               f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=start={st:.4f}:duration={d:.4f},asetpts=PTS-STARTPTS[a{i}];")
    fc += "".join(f"[v{i}][a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[v][a]"
    joined = os.path.join(work, "bumpers_joined.mp4"); wav = os.path.join(work, "bumpers_joined.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "18" if w >= 1080 else "24", "-preset", "medium", "-c:a", "pcm_s16le", joined.replace(".mp4", ".mov")], check=True)
    joined = joined.replace(".mp4", ".mov")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-vn", wav], check=True)
    norm = wav.replace(".wav", "_n.wav"); loudnorm_2pass(wav, norm)
    name = a.name or os.path.splitext(os.path.basename(video))[0] + "_bumpers"
    out = os.path.join(job, "out", f"{name}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", norm, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], check=True)
    for f in (joined, wav, norm): os.remove(f)
    for i in core:   # every piece of the video, after the opener, intro and any insert before it
        _, st, d = parts[i]
        sync_check(out, video, sum(durs[:i]) - st, t0=st, t1=st + d)
    print("video with opener/intro/outro:", out)


if __name__ == "__main__":
    main()
