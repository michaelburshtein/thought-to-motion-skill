"""Attach per-word timings to the plan's captions, for kinetic captions (plan.captionStyle = "kinetic").

Usage:
  word_times.py <job> [--plan plan.json]

Reads <job>/transcript.json (word timings from prep.py) and writes cue.words = [{"w", "s"}] into each caption, so
each word lights up on the frame it is said. Captions may be edited text (corrected names, punctuation, shortened
lines): words are matched to the transcript words whose start falls inside the cue. If the counts match, their times
are used one to one; otherwise the transcript's speech span inside the cue is spread over the caption's words by
length (still in sync with the speech, just not per word). Prints how many cues got exact timings.
Run it after the captions are final and again whenever they change.
"""
import argparse
import json
import os
import re

LATIN_RUN = re.compile(r"[A-Za-z“”\"'][A-Za-z0-9“”\"' ,.?!-]*[A-Za-z0-9?!.”]|[A-Za-z]")


def tokens(text, rtl):
    """Same split as engine/src/lib/util.js tokens(): Latin runs stay together inside RTL text."""
    if not rtl:
        return [w for w in re.split(r"\s+", text) if w]
    out, i = [], 0
    pat = re.compile(LATIN_RUN.pattern + r"|[^\s]+")
    for m in pat.finditer(text):
        out.append(m.group(0))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("job"); ap.add_argument("--plan")
    a = ap.parse_args()
    pp = a.plan or os.path.join(a.job, "plan.json")
    plan = json.load(open(pp))
    tr = json.load(open(os.path.join(a.job, "transcript.json")))
    tw = [w for s in tr["segments"] for w in s.get("words", [])]
    rtl = plan.get("lang") in ("he", "ar", "fa", "yi")
    exact = spread = 0
    for c in plan["captions"]:
        words = tokens(c["text"], rtl)
        inside = [w for w in tw if c["start"] - 0.05 <= w["s"] < c["end"]]
        if inside and len(inside) == len(words):
            c["words"] = [{"w": x, "s": round(max(c["start"], w["s"]), 3)} for x, w in zip(words, inside)]
            exact += 1
            continue
        a0 = max(c["start"], inside[0]["s"]) if inside else c["start"]
        a1 = min(c["end"], inside[-1]["s"] + 0.05) if inside else c["start"] + (c["end"] - c["start"]) * 0.8
        total = sum(max(2, len(x)) for x in words) or 1
        acc, ws = 0, []
        for x in words:
            ws.append({"w": x, "s": round(a0 + (a1 - a0) * acc / total, 3)}); acc += max(2, len(x))
        c["words"] = ws
        spread += 1
    json.dump(plan, open(pp, "w"), ensure_ascii=False, indent=1)
    print(f"word times: {exact} cues exact, {spread} cues spread over the speech span")


if __name__ == "__main__":
    main()
