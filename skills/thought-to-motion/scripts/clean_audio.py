"""Speech cleanup: DeepFilterNet3 noise removal + a light "studio" chain (EQ, de-ess, compression, -14 LUFS).

Usage: clean_audio.py <in.wav|in.mp4> <out.wav> [--strength gentle|full|off]
  gentle: removes up to 20 dB of noise, keeps some room tone (natural; default)
  full:   removes as much noise as possible (studio-dry; can sound processed on very noisy clips)
  off:    only the studio chain

Runs locally with the deep-filter binary that setup.sh downloads into tools/. DeepFilterNet adds a
fixed 30 ms latency; this script removes it so lips stay in sync.
"""
import argparse
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DF = os.path.join(ROOT, "tools", "deep-filter")
DF_LATENCY = 0.03
STUDIO = ("highpass=f=80,equalizer=f=250:width_type=o:w=1:g=-2,equalizer=f=3500:width_type=o:w=1.5:g=3,"
          "deesser=i=0.4,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,loudnorm=I=-14:TP=-1.5:LRA=9")


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout.strip())


def clean(src, out, strength="gentle"):
    tmp = tempfile.mkdtemp()
    try:
        mono = os.path.join(tmp, "a.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "48000", mono], check=True)
        chain, inp = STUDIO, mono
        if strength != "off":
            if not os.path.exists(DF):
                raise SystemExit("tools/deep-filter missing: run scripts/setup.sh (or use --strength off)")
            od = os.path.join(tmp, "o")
            subprocess.run([DF, "-a", "20" if strength == "gentle" else "100", "-o", od, mono], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            inp = os.path.join(od, "a.wav")
            chain = f"atrim=start={DF_LATENCY},asetpts=PTS-STARTPTS,apad,{STUDIO}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", inp, "-af", chain, "-t", f"{duration(src):.3f}",
                        "-ac", "2", "-ar", "48000", out], check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--strength", choices=["gentle", "full", "off"], default="gentle")
    a = ap.parse_args(); clean(a.src, a.out, a.strength); print("clean audio:", a.out)
