"""Local transcription with word timestamps (faster-whisper).

Hebrew uses the ivrit.ai fine-tuned model, which is far more accurate on Hebrew than stock Whisper.
Other languages use Whisper large-v3-turbo. Language is auto-detected unless --lang is given.

Usage: transcribe.py <audio.wav 16k mono> <out.json> [--lang auto|he|en|...] [--model NAME]
Models download once from huggingface.co into <skill>/.cache/hf. Audio never leaves the machine.
"""
import argparse
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.environ.setdefault("HF_HOME", os.path.join(ROOT, ".cache", "hf"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # plain HTTPS download; works behind strict proxies

import soundfile as sf  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

MODELS = {"he": "ivrit-ai/whisper-large-v3-turbo-ct2"}
DEFAULT = "large-v3-turbo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio"); ap.add_argument("out")
    ap.add_argument("--lang", default="auto"); ap.add_argument("--model")
    a = ap.parse_args()
    audio, _ = sf.read(a.audio, dtype="float32")
    t0 = time.time()

    lang = None if a.lang == "auto" else a.lang
    if lang is None:
        det = WhisperModel(DEFAULT, device="cpu", compute_type="int8")
        _, info = det.transcribe(audio[: 16000 * 30], beam_size=1)
        lang = info.language
    name = a.model or MODELS.get(lang, DEFAULT)
    model = WhisperModel(name, device="cpu", compute_type="int8")
    segs, info = model.transcribe(audio, language=lang, word_timestamps=True, beam_size=5, vad_filter=False)
    res = {"language": lang, "model": name, "segments": []}
    for s in segs:
        res["segments"].append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                                "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)}
                                          for w in (s.words or [])]})
    json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
    low = [w["w"] for s in res["segments"] for w in s["words"] if w["p"] < 0.5]
    print(f"{lang} via {name} in {round(time.time() - t0)}s; {len(res['segments'])} segments; low-confidence words: {low[:30]}")


if __name__ == "__main__":
    main()
