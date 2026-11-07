# plan.json

One JSON object. Times are seconds on the CUT timeline (the one `prep.py` produced and transcribed).

```jsonc
{
  "mode": "talking-head",        // or "voice" or "text" (no recording: captions timed by prep_text.py)
  "aspect": "9:16",              // or "16:9" (same plan, wide stage)
  "music": { "style": "calm" },  // optional generated bed: calm | warm | pulse; "seed", "level" (dB) optional. Omit for none
  "motion": "calm",              // optional: softer, slower springs everywhere (default: lively)
  "lang": "he",                  // caption language; drives RTL layout and fonts
  "theme": "light",      // light | dark | bold
  "themeOverrides": {},          // optional: any theme key, e.g. {"accent": "#E4572E"}
  "fps": 30,
  "duration": 50.78,             // from <job>/job.json
  "source": "source.mp4",        // talking-head: source.mp4, voice: voice.wav (inside <job>/public); text mode: none
  "brand": { "wordmark": "YOUR NAME", "series": "notes" },   // or omit for no header
  "showCaptions": true,
  "waveform": true,              // voice mode only
  "keywords": ["Mandela", "Einstein"], // voice mode: words highlighted in the kinetic captions
  "lang2": "en",                 // optional: second caption language shown under the first (bilingual)
  "shots": [ { "start": 0, "end": 5.46, "cam": "A", "zoom": 1.0, "x": 0, "y": 0, "drift": 0 } ],
                                 // optional, talking-head: virtual cameras written by scripts/shots.py (x/y = crop top-left, source px)
  "captions": [ { "start": 0.0, "end": 1.3, "text": "יצאתי להליכה", "text2": "I went for a walk" } ],
  "captionStyle": "kinetic",      // optional (branch kinetic-type): words light up as said; cue.emph = the word that carries the point
  "elements": [ ... ],
  "bumpers": {                    // opener -> 2 s brand intro -> the video -> 3 s outro (recommended)
    "opener": { "start": 20.7, "end": 23.2,          // the video's catchphrase: his own line; end in the pause after the last word
                "text": "...", "text2": "...",        // the line (and the second-language line under it)
                "emph": "...",                        // the one word that lights up
                "words": [ { "w": "...", "s": 20.89 } ] },  // word starts on the cut timeline (check against the audio)
    "intro": true, "outro": true,
    "catchphrase": "Your brand line",      // brand line, a title: no full stop. Hebrew videos: Hebrew line
    "catchphrase2": null,                              // smaller second line (e.g. the English under the Hebrew)
    "follow": "Follow"                                 // outro first line; Hebrew videos: "עקבו אחריי"
  }
}
```

## Elements

Every visual element has `start` and `end`. On the **overlay** (talking-head) elements are cards over the
footage; on the **canvas** (voice and text) they become full scenes. On the canvas scenes must not overlap
(the validator enforces this).

| type | fields | use for |
|---|---|---|
| `title` | `kicker`, `text`, `emphasis` (a substring shown italic with a marker sweep), `subtitle` | the hook, first 2-3 s |
| `keyword` | `title`, `subtitle`, `kicker`, `tone` ("accent" or "light", overlay), `top`, `rotate`, `ghost` (canvas: doubled, drifting headline), `size` (title font px; on the overlay too, e.g. 96 for the one word that must land when it is not spoken) | a concept or named reference the moment it is said |
| `compare` | `options: [{text, at}]`, `marks: [{option, at, text}]`, `reveal: {at, correct, correctTag, wrongTag, kicker}`, `kicker`, `note: {at, text, icon}` | A vs B, myth vs fact, "I thought X, it's Y" |
| `icon` | `icon`, `label`, `kicker`, `caption`, `top` | a visual anchor for a beat. Icons: tv, paws, burst, question, quote, lightbulb, chat, check, clock, heart, growth, coffee, book, laptop, wand, film, code, palette, scissors, zoom, rocket, people, tag, mute, gear, loop, gap, sparkle, doc, envelope, card, lace, balloon, pen, gift, calendar, shield, globe, coins, music, phone. Over a bright background prefer a `keyword` chip (white labels lose contrast) |
| `image` | `src` (file in `<job>/public`), `full` (full-bleed, e.g. inside a cutaway), `diagram` (with `full`: a pre-rendered diagram - no push, no gradient, theme colours kept), `move` (push, pull, rise, drift), `dim` (0..1, darkens the picture when a list sits on it), `focus` | voice mode: the speaker's own photo, slow push-in. With `full`, `src` can also be a short mp4 (a living-photo loop made from a still), played muted from the element's start |
| `list` | `kicker`, `items: [{text, at, icon}]` (`icon`: any icon name, drawn on a paper tile instead of the dot), `size` (item font px; e.g. 54 for 7 items in a cutaway), `top` | steps or points, each appearing as it is said |
| `diagram` | `kind` (balance, link, steps, table, device, beforeafter, cycle, funnel, timeline) + its fields (SKILL.md "Diagrams"), `kicker`, `size`; every timed part takes `at` or `word` | lists, steps, processes, comparisons, change over time - animated, inside a cutaway (canvas only) |
| `behind` | `text`, `start`, `end`, `size`?, `x`?/`y`? (centre; written by scripts/behind.py with `cutout` and `frames`) | one key word behind his head (talking-head footage), ~3 s |
| `endcard` | `kicker`, `text`, `cta` | the closing question / call to action |
| `media` | `src` (video in `<job>/public`), `slot` (tl, tr, ml, mr, bl, br or `[x, y]`), `width` (default 220), `label`, `playAt` (starts playing muted; before that it shows a still), `from` (seconds into the clip), `rotate`, `spawn: [x, y]` (where the speaker points: the panel pops out there and glides to its slot) | show other videos on screen ("here's what it made"), appearing as the speaker points |
| `logo` | `src` (png in `<job>/public`), `width` (default 560), `ratio` (h/w, default 0.28), `slot` `[x, y]` or `top`, `spawn: [x, y]`, `opacity`, `shadow: false` (flat, e.g. a website address on the wall) | a venture's own logo popping out where the speaker points (only with the brand owner's OK) |
| `punchin` | `start`, `end`, `scale` (1.05-1.12) | talking-head: emphasise the reveal |
| `sfx` | `at`, `sound` (pop, whoosh, ding, tick, rise), `volume` (0-1, default 0.5) | accents; keep it sparse |
| `lightleak` | `at`, `duration`, `seed`, `hueShift`, `opacity` (default 0.35) | one warm flourish, usually on the title |
| `silence` | `at`, `duration` (0.5-1.5 s) | a music dip (about -9 dB) just before the key line; needs `music` |

Text fields can be in the video's language; Hebrew/Arabic text is laid out RTL automatically and
embedded English runs stay in order.

## Layout (1080x1920; also used inside 16:9)

Everything stays inside the safe area x 60-900, y 220-1420 (see safe-zones.md). Overlay cards default to
`top: 300` (the band under the header, above a typical head); set `top` yourself or run
`validate_plan.py --fix` to place them off the face. Panels: `slot` tl/tr/ml/mr, or `rowN-k` to spread N small
panels in one row above the head.

16:9 needs no extra coordinates: the 9:16 content band (y 280-1420) is scaled to 0.75 onto the left of the wide
frame, captions sit at full size (talking-head: lower left; voice/text: right), and the talking-head footage is
framed on the right. Check the wide stills anyway; the safe-area validator only checks 9:16.

## Music

`"music": {"style": "calm"}` mixes a generated, copyright-free bed (`scripts/make_music.py`, deterministic per
`seed`) under the video at render time: about -27 dB under a voice with sidechain ducking, about -17 LUFS in
text mode. Styles: `calm` (soft pads, slow arpeggio), `warm` (adds a gentle pulse), `pulse` (light beat).
Never put downloaded songs in a plan.
