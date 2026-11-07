"""Test plans for the diagram templates (not for publishing): one text-mode plan per series, 3 diagrams each, 5.5 s per
diagram. Run in an empty folder, then: render.py video <name> --plan <name>/plan.json. Every pattern in Diagrams.jsx."""
import json, os, sys
D = 5.5
def cap(s, e, text, text2=None, words=None):
    c = {"start": s, "end": e, "text": text}
    if text2: c["text2"] = text2
    ws = text.split(); c["words"] = words or [{"w": w, "s": round(s + i * (e - s) * 0.8 / len(ws), 3)} for i, w in enumerate(ws)]
    return c
def seg(i): return i * D
SETS = {
 "dark": ("dark", "notes", [
   ("balance", {"kicker": "Consuming vs creating", "left": {"text": "Consuming", "icon": "film", "at": 0.3}, "right": {"text": "Creating", "icon": "sparkle", "at": 1.0},
     "tipWord": "change", "tip": "right"}, "The balance is going to change", "המאזן עומד להשתנות"),
   ("link", {"kicker": "Idea to song", "from": {"text": "An idea", "icon": "lightbulb", "at": 0.2}, "to": {"text": "A song", "icon": "music", "at": 0.7},
     "fillAt": 1.2, "doneAt": 3.4, "timer": {"from": 0, "to": 52, "suffix": " s"}, "result": {"text": "Under a minute", "at": 3.6}}, "An idea to a song in under a minute", "מרעיון לשיר בפחות מדקה"),
   ("steps", {"kicker": "How it works", "items": [{"text": "Lyrics", "at": 0.3}, {"text": "Style", "at": 1.1}, {"text": "One click", "at": 1.9}],
     "fan": {"items": ["Version 1", "Version 2", "Version 3"], "at": 3.0}}, "Lyrics, style, one click, versions", "מילים, סגנון, קליק אחד, כמה גרסאות")]),
 "light": ("light", "notes", [
   ("table", {"kicker": "Then and now", "columns": ["Then", "Today"], "rows": [{"then": "A studio", "now": "A phone", "at": 0.3}, {"then": "A band", "now": "One prompt", "at": 1.1},
     {"then": "Months", "now": "Minutes", "at": 1.9}], "nowAt": 3.0}, "A studio, a band, months. Today?", "אולפן, להקה, חודשים. היום?"),
   ("device", {"at": 0.2, "items": [{"text": "Studio", "icon": "music", "at": 1.2}, {"text": "Band", "icon": "people", "at": 1.9}, {"text": "Editor", "icon": "film", "at": 2.6},
     {"text": "Your idea", "icon": "lightbulb", "at": 3.4}]}, "It all fits in your pocket now", "הכל נכנס לכיס עכשיו"),
   ("beforeafter", {"before": {"text": "I listen to music", "at": 0.3}, "after": {"text": "I make music", "at": 2.4}}, "I used to listen. Now I make it", "פעם הקשבתי. עכשיו אני יוצר")]),
 "bold": ("bold", "notes", [
   ("cycle", {"kicker": "The loop", "items": [{"text": "Prompt", "at": 0.3}, {"text": "Generate", "at": 1.0}, {"text": "Listen", "at": 1.7}, {"text": "Tweak", "at": 2.4}],
     "closeAt": 3.2}, "Prompt, generate, listen, tweak, again", "פרומפט, יצירה, הקשבה, שיפור, שוב"),
   ("funnel", {"kicker": "From 20 to 1", "items": [{"text": "20 versions", "at": 0.3}, {"text": "5 good ones", "at": 1.2}, {"text": "2 favourites", "at": 2.1}, {"text": "1 song", "at": 3.0}]},
     "Twenty versions down to one song", "עשרים גרסאות עד שיר אחד"),
   ("timeline", {"kicker": "How it changed", "items": [{"when": "2015", "text": "Buy a song", "at": 0.3}, {"when": "2020", "text": "Stream it", "at": 1.2},
     {"when": "Today", "text": "Make it", "at": 2.1}]}, "Buy it, stream it, make it", "לקנות, להזרים, ליצור")]),
}
for name, (theme, series, items) in SETS.items():
    caps, els = [], []
    for i, (kind, fields, line, line2) in enumerate(items):
        a = seg(i)
        f = json.loads(json.dumps(fields))
        def shift(o):
            if isinstance(o, dict):
                for k, v in list(o.items()):
                    if (k == "at" or k.endswith("At")) and isinstance(v, (int, float)): o[k] = round(v + a, 3)
                    else: shift(v)
            elif isinstance(o, list):
                for v in o: shift(v)
        shift(f)
        els.append({"type": "diagram", "kind": kind, "start": round(a + 0.05, 3), "end": round(a + D - 0.1, 3), **f})
        caps.append(cap(a + 0.1, a + D - 0.3, line, line2))
    p = {"mode": "text", "aspect": "9:16", "lang": "en", "lang2": "he", "theme": theme, "fps": 30, "duration": D * len(items),
         "brand": {"wordmark": "YOUR NAME", "series": series}, "music": False, "motion": "calm", "captionStyle": "kinetic",
         "captions": caps, "keywords": [], "elements": els}
    os.makedirs(f"{name}/public", exist_ok=True)
    json.dump(p, open(f"{name}/plan.json", "w"), ensure_ascii=False, indent=1)
    print(name, len(els))
