"""Text-to-video: turn plain text into a timed job (no recording needed).

Usage: prep_text.py <text.txt | "inline text"> <jobdir> [--lang he|en] [--cps 15] [--aspect 9:16|16:9]

Splits the text into caption-sized lines (one idea each, <= 42 characters, shown as up to two short lines), times them at
a comfortable reading pace (hold = 0.5 s + characters / 15, between 1.5 s and 6 s, +1 s on the last line, plus a short
breath between lines; references/motion-rules.md),
and writes <jobdir>/job.json and <jobdir>/plan.draft.json (mode "text", captions filled, elements empty,
music on). Claude then designs the scenes (see SKILL.md) before Gate 1.
"""
import argparse
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


BREAK_BEFORE = {"and", "or", "but", "so", "because", "to", "of", "for", "with", "that", "which", "when", "where",
                "while", "if", "then", "in", "on", "at", "from", "into", "about", "ו", "אבל", "כי", "ש", "אז", "עם", "על"}


def best_cut(phrase, maxlen):
    """Cut a too-long phrase into a fitting head and the rest: as balanced as possible, preferring a break before a
    connecting word, never leaving a one-word tail."""
    words = phrase.split(" "); best, score = None, None
    for k in range(1, len(words)):
        head, tail = " ".join(words[:k]), " ".join(words[k:])
        if len(head) > maxlen: break
        sc = abs(len(head) - min(len(tail), maxlen)) - (12 if words[k].lower().strip(",.") in BREAK_BEFORE else 0) \
             + (40 if len(words) - k == 1 else 0)
        if score is None or sc < score: best, score = k, sc
    if best is None: return phrase, ""
    return " ".join(words[:best]), " ".join(words[best:])


def split_lines(text, maxlen=42):
    """Sentence -> phrase chunks (commas, dashes, colons) -> captions of <= maxlen characters (shown as up to two
    lines), never splitting inside a phrase unless the phrase alone is too long."""
    text = re.sub(r"\s+", " ", text.strip())
    sentences = re.split(r"(?<=[.!?\u05c3])\s+", text)
    lines = []
    for s in sentences:
        phrases = [x.strip() for x in re.split(r"(?<=[,;:\u2013\u2014])\s+|\s+(?=[-\u2013\u2014]\s)", s) if x.strip()]
        cur = ""
        for ph in phrases:
            if not cur: cur = ph
            elif len(cur) + 1 + len(ph) <= maxlen: cur = f"{cur} {ph}"
            else: lines.append(cur); cur = ph
            while len(cur) > maxlen:
                head, cur = best_cut(cur, maxlen)
                if not cur: cur = head; break
                lines.append(head)
        if cur: lines.append(cur)
    # a dash that opened a phrase is punctuation, not content: never start a caption with it
    out = [re.sub(r"^[-\u2013\u2014]\s*", "", l) for l in lines]
    return [l for l in out if l]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text"); ap.add_argument("job")
    ap.add_argument("--lang", default=None); ap.add_argument("--cps", type=float, default=15, help="reading speed, characters/s")
    ap.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    a = ap.parse_args()
    text = open(a.text, encoding="utf-8").read() if os.path.exists(a.text) else a.text
    lang = a.lang or ("he" if re.search(r"[֐-׿]", text) else "en")
    os.makedirs(os.path.join(a.job, "public"), exist_ok=True)
    sfx = os.path.join(ROOT, "engine", "sfx")
    if os.path.isdir(sfx): shutil.copytree(sfx, os.path.join(a.job, "public", "sfx"), dirs_exist_ok=True)

    t, caps = 1.2, []  # leave ~1.2 s for the opening title to land
    lines = split_lines(text)
    for k, line in enumerate(lines):
        d = min(6.0, max(1.5, 0.5 + len(line) / a.cps)) + (1.0 if k == len(lines) - 1 else 0.0)
        caps.append({"start": round(t, 2), "end": round(t + d, 2), "text": line})
        t += d + 0.25
    duration = round(t + 2.5, 2)  # room for an end card
    job = {"mode": "text", "duration": duration, "fps": 30, "lines": len(caps), "lang": lang}
    json.dump(job, open(os.path.join(a.job, "job.json"), "w"), indent=1)
    plan = {"mode": "text", "lang": lang, "aspect": a.aspect, "theme": "light", "fps": 30, "duration": duration,
            "brand": {"wordmark": "YOUR NAME", "series": "notes"}, "music": True, "motion": "calm",
            "captions": caps, "keywords": [], "elements": []}
    json.dump(plan, open(os.path.join(a.job, "plan.draft.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(job))


if __name__ == "__main__":
    main()
