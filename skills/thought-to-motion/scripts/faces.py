"""Track the presenter's face so on-screen content never covers it.

Usage: faces.py <job> [--video public/source.mp4] [--step 0.25]
Writes <job>/faces.json: {"w":1080,"h":1920,"step":0.25,"boxes":[[t, x, y, w, h] | [t, null], ...]}
(boxes in 1080x1920 coordinates, the largest face per sample). Uses YuNet (MIT, OpenCV Zoo), local, CPU.
"""
import argparse
import json
import os
import subprocess
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODEL_URL = "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx"
MODEL = os.path.join(ROOT, ".cache", "models", "yunet.onnx")
W, H, SW, SH = 1080, 1920, 540, 960


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("job")
    ap.add_argument("--video", default=os.path.join("public", "source.mp4")); ap.add_argument("--step", type=float, default=0.25)
    a = ap.parse_args()
    import cv2
    if not os.path.exists(MODEL):
        os.makedirs(os.path.dirname(MODEL), exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL + ".part"); os.replace(MODEL + ".part", MODEL)
    det = cv2.FaceDetectorYN.create(MODEL, "", (SW, SH), 0.6)
    src = os.path.join(a.job, a.video)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={1 / a.step},scale={SW}:{SH}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    boxes, i, n = [], 0, SW * SH * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        img = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
        _, f = det.detect(img)
        t = round(i * a.step, 2)
        if f is None or len(f) == 0:
            boxes.append([t, None])
        else:
            x, y, w, h = max(f, key=lambda r: r[2] * r[3])[:4]
            k = W / SW
            boxes.append([t, round(x * k), round(y * k), round(w * k), round(h * k)])
        i += 1
    found = [b for b in boxes if b[1] is not None]
    json.dump({"w": W, "h": H, "step": a.step, "boxes": boxes}, open(os.path.join(a.job, "faces.json"), "w"))
    if found:
        arr = np.array([b[1:] for b in found], float)
        print(f"faces: {len(found)}/{len(boxes)} samples; typical box x{int(np.median(arr[:,0]))} y{int(np.median(arr[:,1]))} "
              f"w{int(np.median(arr[:,2]))} h{int(np.median(arr[:,3]))}")
    else:
        print("faces: none found (voice mode or no presenter on screen)")


if __name__ == "__main__":
    main()
