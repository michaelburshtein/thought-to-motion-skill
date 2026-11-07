"""Speed test for this machine: how long the two heavy steps take, on a synthetic 20 s clip (nothing personal used).

  bench.py [--seconds 20]
1. background matte (MODNet) on 1080x1920 frames - GPU if set up, else CPU
2. full-quality render (1080x1920, Remotion) of the example talking-head plan over that clip
Prints seconds per step and per second of video, so machines can be compared.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seconds", type=int, default=20); a = ap.parse_args()
    d = a.seconds
    job = tempfile.mkdtemp(prefix="ttm_bench_"); pub = os.path.join(job, "public"); os.makedirs(pub); os.makedirs(os.path.join(job, "work"))
    src = os.path.join(pub, "source.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate=30:duration={d}",
         "-f", "lavfi", "-i", f"sine=frequency=220:duration={d}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", src])
    plate = os.path.join(job, "plate.png")
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "gradients=size=1080x1920:duration=1", "-frames:v", "1", plate])
    shutil.copytree(os.path.join(ROOT, "engine", "sfx"), os.path.join(pub, "sfx"), dirs_exist_ok=True)
    print(f"cores: {os.cpu_count()}  clip: {d} s")

    t0 = time.time()
    run([PY, os.path.join(HERE, "background.py"), job, plate, "--desk", "off"], stdout=subprocess.DEVNULL)
    tb = time.time() - t0
    print(f"background matte: {tb:6.1f} s  ({tb / d:.2f} s per second of video)")

    plan = json.load(open(os.path.join(ROOT, "examples", "talking-head.he.plan.json")))
    plan["source"] = "source_bg.mp4" if os.path.exists(os.path.join(pub, "source_bg.mp4")) else "source.mp4"
    plan["duration"] = d; plan.pop("music", None)
    plan["elements"] = [e for e in plan["elements"] if e.get("start", e.get("at", 0)) < d - 1 and e["type"] != "lightleak"]
    plan["captions"] = [c for c in plan.get("captions", []) if c["start"] < d - 0.5]
    pp = os.path.join(job, "plan.json"); json.dump(plan, open(pp, "w"), ensure_ascii=False)
    t0 = time.time()
    run([PY, os.path.join(HERE, "render.py"), "video", job, "--plan", pp, "--name", "bench", "--final"], stdout=subprocess.DEVNULL)
    tr = time.time() - t0
    print(f"HD render:        {tr:6.1f} s  ({tr / d:.2f} s per second of video)")
    print(f"take 2 (139 s) would take about: background {tb / d * 139 / 60:.0f} min, HD render {tr / d * 146 / 60:.0f} min")
    shutil.rmtree(job, ignore_errors=True)


if __name__ == "__main__":
    main()
