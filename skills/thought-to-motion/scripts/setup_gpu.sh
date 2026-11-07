#!/usr/bin/env bash
# Optional: run the background matte (MODNet) on an NVIDIA GPU. Works on Linux and WSL2 (the Windows NVIDIA driver
# is used; nothing NVIDIA is installed inside Linux). CUDA 12 + cuDNN 9 come as pip wheels inside .venv.
# Undo: .venv/bin/pip uninstall -y onnxruntime-gpu && .venv/bin/pip install onnxruntime==1.23.2
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; cd "$HERE"
command -v nvidia-smi >/dev/null || { echo "no NVIDIA driver visible (nvidia-smi missing)"; exit 1; }
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
.venv/bin/pip uninstall -y -q onnxruntime || true
.venv/bin/pip install -q --disable-pip-version-check "onnxruntime-gpu[cuda,cudnn]==1.23.2"
.venv/bin/python - <<'PY'
import onnxruntime as ort
ort.preload_dlls()
p = ort.get_available_providers(); print("providers:", p)
assert "CUDAExecutionProvider" in p, "CUDA provider not available"
PY
echo "GPU setup OK: background.py now runs the matte on the GPU (TTM_GPU=0 forces the CPU)."
