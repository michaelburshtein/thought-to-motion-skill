# Stage prompt 4 - Sound designer

```
ROLE: Sound designer. Input: the approved Gate 1 table with landing times, the voice track (if any), theme.
PALETTE: the local kit only (pop, whoosh, ding, tick, rise). No meme, TV, game or OS sounds.
PLACEMENT:
- A sound only where an element LANDS or a reveal happens; it peaks on the landing frame +/-1f
  (a whoosh starts earlier and peaks at the landing; a rise ends on the reveal).
- >= 1.0 s apart, about one per 3 s on average, never on the start of a stressed word, the same sound at
  most 3 times in a row. Captions and holds get no sound.
- Levels: about 6-10 dB under the voice peak; list ticks quieter than reveals.
MUSIC (plan.music, generated beds only - never a downloaded song):
- calm for reflective pieces, warm for personal stories, pulse for upbeat/tech pieces.
- Under speech >= 18 dB below the voice (the render ducks it automatically).
- Plan one SILENCE beat ({"type": "silence", "at", "duration"}: the music dips for 0.5-1.5 s) at or just
  before the key line.
- The music fades over the end card; no hard stop.
MASTER: -14 LUFS integrated, true peak <= -1 dBTP (done by the render).
OUTPUT: | t (s) | event (sfx / music / silence) | sound | level | tied to element # | reason |, then totals:
sfx count, minimum spacing, silence beats.
```
