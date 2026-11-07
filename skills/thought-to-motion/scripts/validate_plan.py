"""Check a plan before rendering. Exits non-zero on errors; prints warnings.

Usage: validate_plan.py <jobdir>/plan.json [--job <jobdir>]
Checks: schema basics, element types, times inside the video, overlapping scenes, caption reading speed,
text inside safe zones (length heuristics), local media/sfx files exist, flashing limits.
"""
import argparse
import json
import os
import sys

TYPES = {"title", "keyword", "compare", "icon", "image", "endcard", "list", "sfx", "punchin", "lightleak", "media", "silence", "logo", "cutaway", "flow",
         "diagram", "behind"}
DIAGRAMS = {  # engine/src/components/Diagrams.jsx: kind -> the fields it needs
    "balance": ("left", "right"), "link": ("from", "to"), "steps": ("items",), "table": ("rows",), "device": ("items",),
    "beforeafter": ("before", "after"), "cycle": ("items",), "funnel": ("items",), "timeline": ("items",)}
SCENES = {"title", "keyword", "compare", "icon", "image", "endcard", "list"}  # occupy the main stage
ICONS = {"tv", "paws", "burst", "question", "quote", "lightbulb", "chat", "check", "clock", "heart", "growth", "coffee", "book", "laptop",
         "wand", "film", "code", "palette", "scissors", "zoom", "rocket", "people", "tag", "mute", "gear", "loop", "gap", "sparkle",
         "doc", "envelope", "card", "lace", "balloon", "pen", "gift", "calendar", "shield", "globe", "coins", "music", "phone"}
SOUNDS = {"pop", "whoosh", "ding", "tick", "rise"}


# Safe area (strictest of TikTok / Reels / Shorts, Oct 2026): keep everything inside x 60-900, y 220-1420.
SAFE = dict(left=60, top=220, right=900, bottom=1420)
CAPTION_BOTTOM = SAFE["bottom"] - 40
MOVABLE = {"title", "keyword", "icon", "compare", "endcard", "list", "logo"}
SLOTS = {"tl": (60, 300), "tr": (680, 300), "ml": (60, 720), "mr": (680, 720)}


def slot_xy(slot, w):
    if isinstance(slot, list): return slot
    if isinstance(slot, str) and slot.startswith("row") and "-" in slot:
        n, k = int(slot[3]), int(slot.split("-")[1])
        return (SAFE["left"] + (k - 1) * ((SAFE["right"] - SAFE["left"] - w) / max(1, n - 1)), 292)
    return SLOTS.get(slot, SLOTS["tl"])


def text_w(s, size):
    return sum(size * (0.36 if c == " " else 0.58) for c in (s or ""))


def est_box(e):
    """Approximate on-screen box (x, y, w, h) of an overlay element, matching engine/src/components/Elements.jsx."""
    t, top = e["type"], e.get("top", 300)
    if t == "title":
        sz = e.get("size", 112); w = min(828, text_w(e.get("text", ""), sz) * 0.92 + 48); h = 44 + (sz if w < 828 else 2 * sz) + 16
        return (72, top, w, h + (50 if e.get("subtitle") else 0))
    if t == "keyword":
        accent = e.get("tone") != "light"
        w = min(820, max(text_w(e.get("title", ""), 40 if accent else 56), text_w(e.get("subtitle", ""), 34 if accent else 26)) + 52)
        return (72, top, w, 32 + (48 if accent else 66) + (42 if e.get("subtitle") else 0))
    if t == "icon":
        return (72, top, 200 + (40 + text_w(e.get("label", ""), 52) if e.get("label") else 0), 200)
    if t == "compare":
        return (72, top, 828, 112 * len(e.get("options", [])) + (70 if e.get("note") else 0))
    if t == "endcard":
        return (72, top, min(828, text_w(e.get("text", ""), 66) + 64), 70 + 76 + (44 if e.get("cta") else 0))
    if t == "list":
        return (72, top, 828, (50 if e.get("kicker") else 0) + 90 * len(e.get("items", [])))
    if t == "media":
        w = e.get("width", 220); x, y = slot_xy(e.get("slot"), w); return (x, y, w, w * 16 / 9 + 30)
    if t == "logo":
        w = e.get("width", 560); h = w * e.get("ratio", 0.28)
        x, y = e["slot"] if isinstance(e.get("slot"), list) else (60 + (840 - w) / 2, e.get("top", 320)); return (x, y, w, h)
    return None


def caption_lines(text, size, rtl):
    per = 788 / (size * (0.6 if rtl else 0.52))
    return max(1, -(-len(text) // int(per)))


def caption_box(c, p):
    """Overlay caption box, matching engine/src/components/Captions.jsx (anchored to the bottom of the safe area)."""
    rtl = p.get("lang") in ("he", "ar", "fa", "yi")
    two = bool(p.get("lang2") and c.get("text2"))
    size = (52 if rtl else 50) if two else (62 if rtl else 58)
    h = 20 + caption_lines(c["text"], size, rtl) * size * 1.16 + (6 + 36 * 1.15 if two else 0)
    return (SAFE["left"], CAPTION_BOTTOM - h, SAFE["right"] - SAFE["left"], h)


# ---- caption fit, measured with the fonts the engine bundles ----
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine", "node_modules", "@fontsource")
_font_cache = {}
def _font(rtl, size, weight=800):
    key = (rtl, size, weight)
    if key not in _font_cache:
        from PIL import ImageFont
        f = os.path.join(FONTS, "heebo/files/heebo-hebrew-%d-normal.woff2" % weight) if rtl else os.path.join(FONTS, "inter/files/inter-latin-%d-normal.woff2" % weight)
        try: _font_cache[key] = ImageFont.truetype(f, size)
        except Exception: _font_cache[key] = None
    return _font_cache[key]

def word_w(w, rtl, size):
    f = _font(rtl, size)
    return f.getlength(w) if f else len(w) * size * (0.6 if rtl else 0.56)

def wrap_lines(text, rtl, size, avail, gap):
    """Greedy flex-wrap like the engine: words separated by `gap` px, no spaces. Returns the number of lines."""
    lines, cur = 1, 0.0
    for w in (text or "").split():
        ww = word_w(w, rtl, size)
        if cur and cur + gap + ww > avail: lines += 1; cur = ww
        else: cur = ww if not cur else cur + gap + ww
    return lines

def overlay_fits(c, p):
    """Two-language kinetic overlay captions: the box has room for ONE line above the translation line. Returns (fits, lines)."""
    rtl = p.get("lang") in ("he", "ar", "fa", "yi"); two = bool(p.get("lang2") and c.get("text2"))
    size = (52 if rtl else 50) if two else (62 if rtl else 58)
    pad = {"scrim": 20, "panel": 48, "plate": 52}.get(p.get("look", {}).get("caption") or {"dark": "scrim", "bold": "panel"}.get(p.get("theme"), "plate"), 52)
    emph = size * (0.05 + 0.028 * max(2, len(c.get("emph") or ""))) * 2 if c.get("emph") else 0
    n = wrap_lines(c["text"], rtl, size, 840 - pad - emph, size * 0.26)
    return (n == 1 if two else n <= 2), n

def canvas_lines(c, p):
    """Canvas captions (cutaways, voice/text): 74 px (80 px Hebrew) in x 90-900; two lines, then the translation line."""
    rtl = p.get("lang") in ("he", "ar", "fa", "yi")
    return wrap_lines(c["text"], rtl, 80 if rtl else 74, 810, 22)

HEB_HYPHEN = __import__("re").compile(r"[\u05D0-\u05EA]-[A-Za-z0-9]")


def word_time(p, word, start):
    """Same lookup as Diagrams.jsx wordTime: the first caption word that starts with `word`, said at/after `start`."""
    import re
    if not word: return None
    norm = lambda x: re.sub(r"[^\w]+", "", (x or "").lower())
    w = norm(word)
    for c in p.get("captions", []):
        for x in c.get("words") or []:
            if x["s"] >= start - 0.25 and norm(x["w"]).startswith(w): return x["s"]
    return None


def cam_faces(faces, shots):
    """faces.json as the virtual cameras see it (plan.shots): each sample scaled/cropped by the shot it falls in."""
    if not shots: return faces
    out = []
    for b in faces["boxes"]:
        s = next((s for s in shots if s["start"] <= b[0] < s["end"]), None)
        if b[1] is None or not s or s["zoom"] <= 1.0001: out.append(b); continue
        z = s["zoom"]; out.append([b[0], (b[1] - s["x"]) * z, (b[2] - s["y"]) * z, b[3] * z, b[4] * z])
    return {**faces, "boxes": out}


def face_typical(faces, a, b):
    """Median face box between a and b (for captions, which follow speech, not long windows)."""
    import statistics as st
    bs = [x for x in faces["boxes"] if x[1] is not None and a - 0.3 <= x[0] <= b + 0.3]
    if not bs: return None
    return tuple(st.median(x[k] for x in bs) for k in (1, 2, 3, 4))


def face_at(faces, a, b):
    """Union of tracked face boxes between a and b, padded 6% so hair, chin and gestures near the face stay clear."""
    bs = [x for x in faces["boxes"] if x[1] is not None and a - 0.3 <= x[0] <= b + 0.3]
    if not bs: return None
    x0 = min(x[1] for x in bs); y0 = min(x[2] for x in bs); x1 = max(x[1] + x[3] for x in bs); y1 = max(x[2] + x[4] for x in bs)
    px, py = (x1 - x0) * 0.06, (y1 - y0) * 0.06
    return (x0 - px, y0 - py, x1 - x0 + 2 * px, y1 - y0 + 2 * py)


def overlap(r, s):
    return max(0, min(r[0] + r[2], s[0] + s[2]) - max(r[0], s[0])) * max(0, min(r[1] + r[3], s[1] + s[3]) - max(r[1], s[1]))


def outside_safe(r):
    return r[0] < SAFE["left"] - 2 or r[1] < SAFE["top"] - 2 or r[0] + r[2] > SAFE["right"] + 2 or r[1] + r[3] > SAFE["bottom"] + 2


def in_cutaway(p, e):
    """True when the element starts inside a cutaway: it is drawn full-screen on the canvas, not over the footage."""
    t = e.get("start", e.get("at", -1))
    return e.get("type") != "cutaway" and any(c.get("type") == "cutaway" and c["start"] - 0.05 <= t < c["end"] for c in p.get("elements", []))


def layout_check(p, job, fix):
    errs, warns, moved = [], [], []
    fpath = os.path.join(job, "faces.json")
    faces = json.load(open(fpath)) if p["mode"] == "talking-head" and os.path.exists(fpath) else None
    selfie = False
    if faces:
        import statistics as st
        hs = [b[4] for b in faces["boxes"] if b[1] is not None]
        selfie = bool(hs) and st.median(hs) > 0.33 * 1920
        faces = cam_faces(faces, p.get("shots"))
    if p["mode"] == "talking-head" and not faces:
        warns.append("no faces.json: run scripts/faces.py <job> so content can be kept off the presenter's face")
    for i, e in enumerate(p["elements"]):
        if p["mode"] != "talking-head" or p.get("aspect") == "16:9" or e["type"] not in MOVABLE | {"media"}: continue
        if in_cutaway(p, e): continue  # drawn on the full-screen canvas, the face isn't on screen
        r = est_box(e)
        if not r: continue
        a0, b0 = e.get("start", 0), e.get("end", 0)
        fb = face_at(faces, a0, b0) if faces else None
        bad_safe, bad_face = outside_safe(r), (fb is not None and overlap(r, fb) > 0.04 * r[2] * r[3])
        if e["type"] == "media" and faces and bad_face:
            # A panel stays up for many seconds while the speaker moves: the union of every face position is far too
            # strict and pushes panels away from where he points. Count instead how often it really covers his face
            # (the tracked face itself, unpadded): OK if it touches less than 15% of the face in at least 85% of samples.
            bs = [b for b in faces["boxes"] if b[1] is not None and a0 <= b[0] <= b0]
            hits = sum(1 for b in bs if overlap(r, (b[1], b[2], b[3], b[4])) > 0.15 * b[3] * b[4])
            bad_face = bool(bs) and hits / len(bs) > 0.15
            if not bad_face and hits:
                warns.append(f"element {i} (media) brushes the face in {hits} of {len(bs)} samples (he leans toward it); allowed")
        if not (bad_safe or bad_face): continue
        what = " and ".join(x for x, y in (("outside the safe area", bad_safe), ("covers the presenter's face", bad_face)) if y)
        if fix and e["type"] in MOVABLE:
            # candidate tops: above the face first (under the header), then below it (above the captions)
            caps_top = min([caption_box(c, p)[1] for c in p["captions"] if c["end"] > a0 and c["start"] < b0] or [CAPTION_BOTTOM])
            cands = list(range(300, 1400, 20))
            ok = [y for y in cands if not outside_safe((r[0], y, r[2], r[3])) and y + r[3] <= caps_top - 16
                  and (fb is None or overlap((r[0], y, r[2], r[3]), fb) == 0)]
            if ok:
                best = min(ok, key=lambda y: abs(y - r[1]))
                e["top"] = best; moved.append(f"element {i} ({e['type']}) {what}: moved to top={best}")
                continue
        msg = f"element {i} ({e['type']}) {what} at {a0:.1f}-{b0:.1f}s (box x{int(r[0])} y{int(r[1])} w{int(r[2])} h{int(r[3])}" + \
              (f"; face x{int(fb[0])} y{int(fb[1])} w{int(fb[2])} h{int(fb[3])})" if fb else ")")
        errs.append(msg + ("" if fix else " - run with --fix, or set 'top'/'slot'/'width'"))
    if p.get("captionStyle", "box") not in ("box", "kinetic"): errs.append("captionStyle must be box or kinetic")
    if p.get("captionStyle") == "kinetic":
        if not any(c.get("words") for c in p["captions"]): warns.append("kinetic captions without word timings: run scripts/word_times.py <job> (words are spread evenly until then)")
        n_emph = sum(1 for c in p["captions"] if c.get("emph"))
        if n_emph > p["duration"] / 2.5: warns.append(f"{n_emph} emphasised words in {p['duration']:.0f}s; about one every 3 s, or nothing stands out")
        for i, c in enumerate(p["captions"]):
            if c.get("emph") and c["emph"].strip(",.?!:;") not in c["text"]: errs.append(f"caption {i}: emph '{c['emph']}' is not in '{c['text']}'")
    if faces:
        for i, c in enumerate(p["captions"]):
            fb = face_typical(faces, c["start"], c["end"]); cb = caption_box(c, p)
            if fb and overlap(cb, fb) > 0.10 * cb[2] * cb[3]:
                errs.append(f"caption {i} would sit over the presenter's chin/mouth ({c['start']:.1f}s); split it into shorter cues")
    if selfie and errs:  # the face fills the frame: nothing can avoid it, so report once instead of per element
        warns.append(f"close-up selfie: the face fills most of the frame, so {len(errs)} cards/captions overlap it "
                     "(unavoidable in 9:16; the 16:9 layout or a wider framing keeps the face clear)")
        errs = []
    return errs, warns, moved


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("--job")
    ap.add_argument("--fix", action="store_true", help="move cards that cover the face or leave the safe area")
    a = ap.parse_args()
    p = json.load(open(a.plan)); job = a.job or os.path.dirname(os.path.abspath(a.plan))
    errs, warns = [], []
    for k in ("mode", "lang", "duration", "captions", "elements") + (() if p.get("mode") == "text" else ("source",)):
        if k not in p: errs.append(f"missing '{k}'")
    if p.get("aspect", "9:16") not in ("9:16", "16:9"): errs.append("aspect must be 9:16 or 16:9")
    if errs: print("\n".join("ERROR " + e for e in errs)); sys.exit(1)
    D = p["duration"]
    if p.get("source") and not os.path.exists(os.path.join(job, "public", p["source"])): errs.append(f"source not found: public/{p['source']}")
    if p.get("music") and not isinstance(p["music"], bool) and (p["music"] if isinstance(p["music"], str) else p["music"].get("style", "calm")) not in ("calm", "warm", "pulse"):
        errs.append("music style must be calm, warm or pulse (or true = the theme default)")

    for i, c in enumerate(p["captions"]):
        if c["end"] <= c["start"]: errs.append(f"caption {i} ends before it starts")
        cps = len(c["text"]) / max(0.01, c["end"] - c["start"])
        if cps > 20: warns.append(f"caption {i} is too fast to read ({cps:.0f} chars/s, max 20): '{c['text'][:40]}'")
        elif cps > 17 and p.get("mode") == "text": warns.append(f"caption {i} reads fast for text mode ({cps:.0f} chars/s, aim <= 17)")
        if c["end"] - c["start"] < 0.83 and len(c["text"]) > 8: warns.append(f"caption {i} is on screen < 0.83 s")
        if c["end"] - c["start"] > 7.0: warns.append(f"caption {i} stays > 7 s; split it")
        if len(c["text"]) > 60: warns.append(f"caption {i} is long ({len(c['text'])} chars); split it")
        if p.get("lang2") and not c.get("text2"): warns.append(f"caption {i} has no text2 but lang2 is set")
        if c.get("text2") and len(c["text2"]) > 44: warns.append(f"caption {i} text2 is long ({len(c['text2'])} chars); it will shrink to fit one line")
        if caption_lines(c["text"], 52 if p.get("lang2") else 62, p.get("lang") in ("he", "ar", "fa", "yi")) > 2:
            warns.append(f"caption {i} needs 3+ lines; split it into two cues")
        # Hebrew prefix glued to a Latin word with a hyphen ("ב-Suno") renders in the wrong order
        for k in ("text", "text2"):
            m = HEB_HYPHEN.search(c.get(k) or "")
            if m: errs.append(f"caption {i} {k}: '{m.group(0)}...' (Hebrew prefix + hyphen + Latin word) renders in the wrong order; reword it (e.g. 'בסונו', 'בעזרת AI')")
        mid = (c["start"] + c["end"]) / 2
        on_canvas = p.get("mode") in ("voice", "text") or any(e.get("type") == "cutaway" and e["start"] + 0.3 <= mid < e["end"] - 0.25 for e in p["elements"])
        if p.get("captionStyle") == "kinetic" and p.get("aspect", "9:16") == "9:16":
            if on_canvas:
                n = canvas_lines(c, p)
                if n > 2: errs.append(f"caption {i} needs {n} lines on the canvas (max 2 at y 1050, the translation line sits at ~1255): '{c['text']}'")
            elif p.get("mode") == "talking-head":
                ok, n = overlay_fits(c, p)
                if not ok: errs.append(f"caption {i} wraps to {n} lines in the overlay box and lands on the translation line: '{c['text']}' "
                                       f"({len(c['text'])} chars; keep two-language overlay cues to ~26 or split the cue)")

    stage = []
    for i, e in enumerate(p["elements"]):
        t = e.get("type")
        if t not in TYPES: errs.append(f"element {i}: unknown type '{t}'"); continue
        a0 = e.get("start", e.get("at", 0)); b0 = e.get("end", a0 + e.get("duration", 0))
        if a0 < 0 or b0 > D + 0.05: errs.append(f"element {i} ({t}) outside 0..{D}s")
        if t in ("title", "keyword", "compare", "icon", "image", "endcard", "list", "punchin") and b0 - a0 < 1.2:
            warns.append(f"element {i} ({t}) is on screen < 1.2s; too short to read")
        if t == "icon" and e.get("icon") not in ICONS: errs.append(f"element {i}: unknown icon '{e.get('icon')}' (have: {sorted(ICONS)})")
        if t == "sfx" and e.get("sound") not in SOUNDS: errs.append(f"element {i}: unknown sound '{e.get('sound')}' (have: {sorted(SOUNDS)})")
        if t == "media" and not os.path.exists(os.path.join(job, "public", e.get("src", ""))): errs.append(f"element {i}: media not found public/{e.get('src')}")
        if t == "image" and not os.path.exists(os.path.join(job, "public", e.get("src", ""))): errs.append(f"element {i}: image not found public/{e.get('src')}")
        if t == "compare" and e.get("reveal") and not (0 <= e["reveal"].get("correct", -1) < len(e.get("options", []))):
            errs.append(f"element {i}: reveal.correct out of range")
        if t == "diagram":
            if e.get("kind") not in DIAGRAMS: errs.append(f"element {i}: unknown diagram kind '{e.get('kind')}' (have: {sorted(DIAGRAMS)})")
            else:
                for f in DIAGRAMS[e["kind"]]:
                    if not e.get(f): errs.append(f"element {i}: diagram '{e['kind']}' needs '{f}'")
                parts = [x for f in ("items", "rows") for x in (e.get(f) or [])] + [e[f] for f in ("left", "right", "from", "to", "before", "after", "result", "fan") if isinstance(e.get(f), dict)]
                if len(e.get("items") or e.get("rows") or []) > 5: warns.append(f"element {i}: diagram shows at most 5 items/rows (the rest are dropped)")
                for x in parts:
                    tt = x.get("at") if isinstance(x.get("at"), (int, float)) else word_time(p, x.get("word"), a0)
                    if x.get("word") and tt is None: errs.append(f"element {i}: diagram word '{x['word']}' is not said after {a0}s (check the caption words / run word_times.py)")
                    elif tt is not None and not (a0 - 0.05 <= tt < b0): warns.append(f"element {i}: diagram part '{x.get('text', '')}' lands at {tt:.2f}s, outside {a0}-{b0}s")
                    if x.get("icon") and x["icon"] not in ICONS: errs.append(f"element {i}: unknown icon '{x['icon']}'")
        if t == "behind":
            if not e.get("text"): errs.append(f"element {i}: behind needs 'text'")
            if p["mode"] != "talking-head": errs.append(f"element {i}: behind is for talking-head footage")
            elif not e.get("cutout") or not os.path.isdir(os.path.join(job, "public", e.get("cutout", ""))):
                errs.append(f"element {i}: behind has no cut-outs; run scripts/behind.py <job> after the timings are final")
            elif e.get("frames") and (e["frames"][0] > round(a0 * p.get("fps", 30)) or e["frames"][1] < round(b0 * p.get("fps", 30))):
                errs.append(f"element {i}: behind cut-outs don't cover {a0}-{b0}s (the timing changed); re-run scripts/behind.py")
            if not 1.5 <= b0 - a0 <= 4.5: warns.append(f"element {i}: behind word lasts {b0 - a0:.1f}s; about 3 s reads best")
            if len(e.get("text", "")) > 8: warns.append(f"element {i}: behind word '{e.get('text')}' is long; one short word reads best behind the head")
            if in_cutaway(p, e): errs.append(f"element {i}: behind can't be inside a cutaway (it needs his footage)")
        if t in SCENES and not (t == "image" and e.get("full")): stage.append((a0, b0, i, t))  # a full image is a backdrop

    # In voice/text mode every scene uses the whole stage, so scenes must not overlap.
    # In talking-head mode, warn when more than one card is up at once.
    stage.sort()
    for (a1, b1, i1, t1), (a2, b2, i2, t2) in zip(stage, stage[1:]):
        if a2 < b1 - 0.05:
            msg = f"elements {i1} ({t1}) and {i2} ({t2}) overlap {a2:.2f}-{b1:.2f}s"
            (errs if p["mode"] in ("voice", "text") else warns).append(msg)

    # ---- virtual cameras (scripts/shots.py) ----
    sh = p.get("shots") or []
    if sh and p["mode"] != "talking-head": errs.append("shots are only for talking-head videos")
    cap = 1.75 if p.get("aspect") == "16:9" else 1.45
    for i, x in enumerate(sh):
        if x["zoom"] > cap: errs.append(f"shot {i} zooms {x['zoom']}x; max {cap}x for this format (the picture goes soft)")
        if i and abs(x["start"] - sh[i - 1]["end"]) > 0.01: errs.append(f"shot {i} doesn't start where shot {i - 1} ends")
        if i and x["cam"] == sh[i - 1]["cam"]: warns.append(f"shots {i - 1} and {i} use the same camera (reads as a jump cut)")
        if x["end"] - x["start"] < 2.0: warns.append(f"shot {i} is under 2 s")
    if sh and (sh[0]["start"] > 0.01 or abs(sh[-1]["end"] - D) > 0.05): warns.append("shots don't cover the whole video")

    # ---- motion rules (references/motion-rules.md) ----
    VIS = ("title", "keyword", "compare", "icon", "image", "endcard", "list", "media", "punchin", "logo", "flow", "diagram", "behind")
    vis = sorted((e.get("start", 0), e.get("end", 0)) for e in p["elements"] if e.get("type") in VIS)
    if vis and vis[0][0] > 0.5: warns.append(f"first visual element starts at {vis[0][0]:.1f}s; frame 0 should be content (start by 0.5 s)")
    edge = 0.0
    for a1, b1 in vis + [(D, D)]:
        if a1 - edge > 6.0 and a1 - edge < D: warns.append(f"no visual event for {a1 - edge:.1f}s ({edge:.1f}-{a1:.1f}s); aim for one every 2-5 s")
        edge = max(edge, b1) if a1 <= edge else b1
    for t0 in sorted({a for a, _ in vis}):
        on = sum(1 for e in p["elements"] if e.get("type") in VIS and e.get("type") != "punchin" and e["start"] <= t0 < e["end"])
        if on > 2: warns.append(f"{on} graphics on screen at {t0:.1f}s; keep <= 2 besides captions (one focal point)")
    pins = sorted((e["start"], e.get("scale", 1.08)) for e in p["elements"] if e.get("type") == "punchin")
    for st, k in pins:
        if k > 1.25: errs.append(f"punch-in at {st}s scales {k}x; max 1.25x")
    for (x, _), (y, _) in zip(pins, pins[1:]):
        if y - x < 8: warns.append(f"punch-ins at {x}s and {y}s are < 8 s apart")
    for e in p["elements"]:
        if e.get("type") == "lightleak":
            if p["mode"] == "talking-head" and e.get("opacity", 0.35) > 0.35: warns.append(f"light leak at {e['at']}s: opacity > 0.35 over a face")
            if e.get("duration", 1.2) < 1.0: warns.append(f"light leak at {e['at']}s: shorter than 1 s (flash risk)")
        if e.get("type") == "silence":
            if not p.get("music"): warns.append(f"silence beat at {e.get('at')}s has no music to dip")
            if not 0.5 <= e.get("duration", 1.0) <= 1.5: warns.append(f"silence beat at {e.get('at')}s: aim for 0.5-1.5 s")
    sfx = sorted((e["at"], e.get("sound")) for e in p["elements"] if e.get("type") == "sfx")
    for (x, sx), (y, _) in zip(sfx, sfx[1:]):
        if y - x < 1.0 and sx != "rise": warns.append(f"sound effects at {x}s and {y}s are < 1 s apart")
    for k in range(len(sfx) - 3):
        if len({sfx[j][1] for j in range(k, k + 4)}) == 1: warns.append(f"'{sfx[k][1]}' used 4 times in a row from {sfx[k][0]}s")

    flashes = sorted(e["at"] for e in p["elements"] if e.get("type") == "lightleak")
    for x, y in zip(flashes, flashes[1:]):
        if y - x < 1.0: warns.append(f"light leaks at {x}s and {y}s are < 1s apart (flashing)")
    n_sfx = sum(1 for e in p["elements"] if e.get("type") == "sfx")
    if n_sfx > max(3, D / 6): warns.append(f"{n_sfx} sound effects in {D:.0f}s may feel busy")

    # ---- cutaways: full-screen animation over his voice (talking-head 9:16) ----
    cuts = sorted((e for e in p["elements"] if e.get("type") == "cutaway"), key=lambda e: e["start"])
    if cuts and (p["mode"] != "talking-head" or p.get("aspect") == "16:9"): errs.append("cutaways work only in 9:16 talking-head videos")
    for c in cuts:
        d = c["end"] - c["start"]
        if not 2.5 <= d <= 9: warns.append(f"cutaway at {c['start']}s lasts {d:.1f}s; aim for 2.5-9 s (long enough to explain, short enough to come back to him)")
        if c["start"] < 3: errs.append(f"cutaway at {c['start']}s: the first 3 s stay on his face (the hook)")
        if c["end"] > p["duration"] - 2: errs.append(f"cutaway at {c['start']}s: the video ends on his face")
        for e in p["elements"]:
            if e.get("type") in ("media", "logo", "punchin") and e.get("start", 0) < c["end"] and e.get("end", 0) > c["start"]:
                errs.append(f"cutaway at {c['start']}s overlaps a {e['type']} at {e['start']}s (he is pointing/showing something - stay on him)")
        inside = [e for e in p["elements"] if e.get("type") not in ("sfx", "silence", "cutaway")
                  and c["start"] - 0.05 <= e.get("start", e.get("at", -1)) < c["end"]]
        if not inside: errs.append(f"cutaway at {c['start']}s has no scene in it (add a keyword/icon/list/compare/flow starting inside)")
        for e in inside:
            if e["type"] not in ("keyword", "icon", "list", "compare", "flow", "title", "image", "diagram"): errs.append(f"{e['type']} at {e.get('start')}s can't be drawn in a cutaway")
            if e.get("end", 0) > c["end"] + 0.05: warns.append(f"{e['type']} at {e.get('start')}s outlasts its cutaway (ends {e['end']}s, cutaway ends {c['end']}s)")
    for a_, b_ in zip(cuts, cuts[1:]):
        if b_["start"] - a_["end"] < 6: warns.append(f"cutaways at {a_['start']}s and {b_['start']}s are < 6 s apart; let him be seen between them")
    if cuts and sum(c["end"] - c["start"] for c in cuts) > 0.3 * p["duration"]:
        warns.append("cutaways cover > 30% of the video; it's his face that builds trust - keep them for the ideas that need a picture")
    for e in p["elements"]:
        if e.get("type") == "flow" and p["mode"] == "talking-head" and not in_cutaway(p, e): errs.append(f"flow at {e.get('start')}s: only inside a cutaway (or in voice/text modes)")
        if e.get("type") == "diagram" and p["mode"] == "talking-head" and not in_cutaway(p, e): errs.append(f"diagram at {e.get('start')}s: only inside a cutaway (or in voice/text modes)")

    # ---- layout: safe area + presenter's face (talking-head) ----
    lay_e, lay_w, moved = layout_check(p, job, a.fix)
    errs += lay_e; warns += lay_w
    if moved:
        json.dump(p, open(a.plan, "w"), ensure_ascii=False, indent=1)
        for m in moved: print("FIXED", m)

    for w in warns: print("WARN ", w)
    for e in errs: print("ERROR", e)
    print("OK" if not errs else f"{len(errs)} error(s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
