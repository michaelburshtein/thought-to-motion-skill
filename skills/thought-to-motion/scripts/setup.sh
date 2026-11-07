#!/usr/bin/env bash
# One-time setup. Everything installs INSIDE this skill folder:
#   .venv/                 Python venv (pinned faster-whisper, soundfile, pillow, numpy)
#   engine/node_modules/   Remotion + fonts, from the committed package-lock.json
# Nothing is installed globally. Speech models download once from huggingface.co into .cache/hf.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

command -v ffmpeg >/dev/null || { echo "ffmpeg is required (apt install ffmpeg / brew install ffmpeg)"; exit 1; }
command -v node >/dev/null || { echo "Node.js 18+ is required"; exit 1; }
command -v python3 >/dev/null || { echo "Python 3.10+ is required"; exit 1; }

if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install --quiet --disable-pip-version-check -r scripts/requirements.txt

(cd engine && npm ci --ignore-scripts --no-audit --no-fund --silent)

.venv/bin/python scripts/make_sfx.py engine/sfx

# DeepFilterNet3 speech cleanup (MIT/Apache-2.0), official release binary, checksum-verified where known.
DF_VER=0.5.6
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)  DF_ASSET="deep-filter-${DF_VER}-x86_64-unknown-linux-musl"; DF_SHA="70775e251eee44c0f2451a1e833326cf8bcbbe304d3e7cd12851e6fce72ef7da" ;;
  Darwin-arm64)  DF_ASSET="deep-filter-${DF_VER}-aarch64-apple-darwin"; DF_SHA="" ;;
  Darwin-x86_64) DF_ASSET="deep-filter-${DF_VER}-x86_64-apple-darwin"; DF_SHA="" ;;
  *) DF_ASSET="" ;;
esac
mkdir -p tools
if [ -n "$DF_ASSET" ] && [ ! -x tools/deep-filter ]; then
  curl -fsSL -o tools/deep-filter "https://github.com/Rikorose/DeepFilterNet/releases/download/v${DF_VER}/${DF_ASSET}"
  GOT=$( (sha256sum tools/deep-filter 2>/dev/null || shasum -a 256 tools/deep-filter) | cut -d' ' -f1)
  if [ -n "$DF_SHA" ] && [ "$GOT" != "$DF_SHA" ]; then rm -f tools/deep-filter; echo "deep-filter checksum mismatch; aborting"; exit 1; fi
  [ -z "$DF_SHA" ] && echo "note: deep-filter for this platform is not checksum-pinned yet (sha256 $GOT)"
  chmod +x tools/deep-filter
fi
[ -x tools/deep-filter ] || echo "note: no deep-filter binary for this platform; use prep.py --clean off"
echo "Setup OK. Next: scripts/prep.py <media> <jobdir>"
