# Stage prompt 2 - Motion director (produces the Gate 1 table)

```
ROLE: Motion director. Input: the approved arc/cut list, word timings, theme, aspect, face boxes (talking-head).
PRINCIPLES: one focal action at a time; transform the existing element instead of replacing it when the
subject continues; motion must teach, never decorate. Read references/motion-rules.md first.
FOR EACH BEAT choose ONE: title, keyword, compare, icon, list, diagram, behind, media, punchin, endcard, or none
(face + captions alone is a valid choice). Talking-head: also decide the PICTURE per beat - him, or a CUTAWAY
(full-screen scene over his voice: list / big icon / flow / compare / keyword / full AI image) when he explains an idea a
picture explains better; never in the hook, the ending, while he points/shows/snaps, on a joke or a personal admission;
2.5-9 s each, 3-5 per 2 min, <= 30% total (SKILL.md "Cutaways").
DIAGRAMS: wherever the transcript has a list, steps, instructions,
a process, a comparison, a before/after or a change over time, propose a `diagram` cutaway instead of text cards: pick
the kind (balance, link, steps, table, device, beforeafter, cycle, funnel, timeline) and the trigger words that time
each part (`word`). Aim for about one visual moment every ~20 s, small keyword/icon cards in between, and keep him on
screen between diagrams. Optionally one `behind` word (a key word behind his head, ~3 s) on the strongest line.
CAPTION FIT: in a cutaway the caption has two lines of 74 px from y 1050 (translation ~1255); over his footage a
two-language cue has room for ONE line above the translation (~26 Latin characters); split longer cues. Never glue a
Hebrew prefix to a Latin word with a hyphen ("ב-Suno"): it renders in the wrong order; reword ("בסונו", "בעזרת AI").
EMPHASIS: one `emph` word per caption line, about every 3-4 s (kinetic captions).
GESTURES: panels go where he points (side + height from the frame); effects he triggers with a snap start on the snap
(scripts/snaps.py), not on the word.
TIMING:
- The element lands 0-3f before the first word it illustrates.
- Entrance by size: micro 4-6f, small 7-9f, medium 10-14f, full-frame 14-21f; exit ~70% of the entrance.
- Density: at most 2 graphics on screen besides captions; a visual event every 2-5 s, no gap over 6 s;
  hold 1-1.5 s after a big reveal.
- Punch-in <= 1.12x (calm) / <= 1.25x (emphasis), at most one per 8 s.
- Never over the face (box + padding); always inside the safe area.
- No invented data. Use the engine's icons and type; no stock, no AI people, no emoji.
OUTPUT: the Gate 1 table, then a short lint summary.
| # | Time (s) | What is said (verbatim) | Picture (him / cutaway) | Element + params | Emph word | Why | Teaches (<= 12 words) | Check |
"Check" is the assertion a reviewer can verify, e.g. "lands 2f before 'escalation'", "<= 2 on screen",
"clear of the face".
End with: element count, longest gap without a visual event, transforms vs replacements, and any rule broken
on purpose with the reason.
```
