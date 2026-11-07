"""Animate one HTML slide into a short looping MP4 (carousel slides, the speaker 2026-11-03).

The slide's layout stays exactly as designed; a small per-slide JS file moves elements frame by frame.

  animate_slide.py --html slide.html --js slide_anim.js --out slide.mp4 [--size 1080x1350] [--dur 6] [--fps 30]

The JS file defines  window.__setup = () => {...}  (find elements, store end states) and
window.__t = (t) => {...}  (set every animated element for time t in seconds). Helpers injected first:
  ease(x)            cubic ease-out, clamped to 0..1  (calm motion: decelerating entrances, no bounce)
  win(t, a, b)       eased progress of the window a..b seconds
  $(sel) / $$(sel)   querySelector / querySelectorAll as an array
Rules: text the reader needs stays still; ONE live panel per slide shows the real thing working (counters, bars,
log lines appearing, a prompt typing). Every number shown is real. First slide moves within the first second.
Fonts must load from file:// URLs (the slide is opened with goto, not set_content).
"""
import argparse, asyncio, os, shutil, subprocess, tempfile
from playwright.async_api import async_playwright

HELPERS = r"""
window.ease = x => 1 - Math.pow(1 - Math.min(Math.max(x, 0), 1), 3);
window.win = (t, a, b) => ease((t - a) / (b - a));
window.$ = s => document.querySelector(s);
window.$$ = s => [...document.querySelectorAll(s)];
"""

async def run(a):
    w, h = map(int, a.size.lower().split("x"))
    tmp = tempfile.mkdtemp(prefix="anim_")
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=os.environ.get("BROWSER_EXECUTABLE"))
            pg = await b.new_page(viewport={"width": w, "height": h})
            await pg.goto("file://" + os.path.abspath(a.html)); await pg.evaluate("document.fonts.ready")
            # ";0" so Playwright doesn't treat a script ending in an arrow function as a function to call
            await pg.evaluate(HELPERS + ";0"); await pg.evaluate(open(a.js).read() + "\n;0"); await pg.evaluate("window.__setup()")
            n = int(round(a.fps * a.dur))
            for i in range(n):
                await pg.evaluate(f"window.__t({i / a.fps})")
                await pg.screenshot(path=os.path.join(tmp, f"{i:04d}.png"))
            await b.close()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", os.path.join(tmp, "%04d.png"),
                        "-c:v", "libx264", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], check=True)
        print(f"animated slide -> {a.out} ({w}x{h}, {a.dur}s, {a.fps} fps)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True); ap.add_argument("--js", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1350"); ap.add_argument("--dur", type=float, default=6.0)
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--crf", type=int, default=18)
    asyncio.run(run(ap.parse_args()))
