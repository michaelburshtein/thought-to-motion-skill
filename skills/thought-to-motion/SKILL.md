---
name: thought-to-motion
description: Turn a talking-head clip, a voice recording or plain text into a vertical (9:16) or wide (16:9) video with motion design timed to what is said - word-timed captions (Hebrew/RTL and English), keyword cards, A/B reveals, icons, end card, brand theme, optional copyright-free music. Runs fully locally (Whisper/ivrit.ai + Remotion + ffmpeg) with two human approval gates. Use when asked to edit, caption, add motion graphics or "After Effects" to a short social video, voice note or text.
---

# thought-to-motion

The idea is the product; everything else is a layer. This skill takes a recording (a talking-head
video or just a voice note), finds the beats in what was said, and designs motion around them:
captions in the spoken language, cards on the keywords, a reveal on the twist, a closing question.

Three modes:
- **talking-head**: the footage stays; cards, captions and punch-ins sit on top of it.
- **voice**: no footage needed (an audio file, or the audio extracted from a video); a full-frame branded canvas
  with scenes, kinetic captions and a live waveform.
- **text**: no recording at all; plain text becomes timed kinetic captions and scenes on the branded canvas,
  usually with background music.

Two formats: **9:16** (default; Reels, TikTok, Shorts) and **16:9** (`"aspect": "16:9"`; YouTube, LinkedIn, web).
The same plan renders in both: in 16:9 the 9:16 layout is placed on a wide stage (talking-head: the speaker
framed on the right, motion design on the left).

Everything runs on this machine. No footage, audio or text is uploaded anywhere.

## 0. Setup (once per machine)

From the skill folder:
```bash
bash scripts/setup.sh          # venv + pinned packages + engine/node_modules from the lockfile + local sound kit
```
Needs ffmpeg, Node 18+, Python 3.10+. First transcription downloads models from `huggingface.co`
(plus its file CDN `*.hf.co`) into `.cache/hf`. If network access is allow-listed, those hosts must be allowed.
If a Chrome/Chromium headless shell already exists, set `BROWSER_EXECUTABLE=/path/to/headless_shell`;
otherwise Remotion downloads its own into `engine/node_modules` on first render.
Run Python scripts with `.venv/bin/python`.

### Your brand (once)
Copy `brand.example.json` to `brand.json` and fill it in: wordmark (your name or brand), series label, handle,
brand line, theme (`light`, `dark` or `bold`: neutral starting points in engine/src/lib/theme.js; add your own colours
and fonts there, and pick a look with `plan.look`, see "Looks").
Every plan's `brand`, `theme` and `bumpers` fields come from it. No brand.json -> no header, no intro or outro.

## 1. Intake (ask only what you can't infer)

- The source. Video with a person talking -> talking-head; audio only, or a video where only the voice matters
  -> voice (prep extracts the audio); plain text -> text mode.
- Format: 9:16, 16:9, or both (two renders of the same plan with a different `aspect`).
- Music: on or off. Only the built-in generated beds are embedded (calm / warm / pulse, no copyright, nothing to
  be claimed); each theme has a default bed. If the user wants a specific song, leave music off; they add it in the app.
- Caption language(s): default = the spoken language. Two options for a second language: **bilingual**
  (one video, the spoken language on top and a smaller translation under it: `lang2` + `text2`) or a separate render.
- Theme (`light` / `dark` / `bold`, or your own, see engine/src/lib/theme.js),
  brand wordmark + series label (or none), and the closing question / CTA if they have one.
- Voice mode: any of their own photos to use (put them in `<job>/public/`).

## 2. Prepare

Text mode (no recording):
```bash
.venv/bin/python scripts/prep_text.py <text.txt | "inline text"> <job> [--lang he|en] [--wpm 150] [--aspect 9:16|16:9]
```
Splits the text into caption-sized lines on phrase boundaries, times them at a comfortable reading pace and writes
`plan.draft.json` (mode "text", music calm, motion calm). Don't rewrite the user's words; only split and time them.
Then design the scenes (section 4) as for voice mode. Skip to section 4.

Video or audio:
```bash
.venv/bin/python scripts/prep.py <media> <job> [--mode voice] [--lang he|en|auto] [--no-cut]
```
Normalises to 1080x1920 30fps (or audio), cuts pauses > 0.45s without ever dropping a word (silences at -40 dB, every
word Whisper hears is added back, gaps < 0.25 s merged; `--no-protect` = the plain -32 dB cut), keeps 1-2 s of quiet
head and tail "like in cinema" up to where the speaker reaches for the phone (`--tight` = cut on the first word),
checks lip sync on every 3rd piece by raw-waveform correlation over 2.5 s, cleans the speech
(DeepFilterNet3 noise removal + EQ, de-ess, compression, -14 LUFS; `--clean gentle` by default,
`full` for very noisy outdoor clips, `off` for studio recordings), copies the sound kit, and transcribes
the CUT timeline with word timings -> `<job>/transcript.json`.
Hebrew uses the ivrit.ai model automatically. The script prints low-confidence words: check those first.

### Optional: replace the background (talking-head)

**Best results - film a clean plate.** Before you sit down, film 3-5 seconds of the empty room, then walk in and
start. Lock the phone on a tripod and lock exposure and focus (on iPhone: long-press the screen until "AE/AF LOCK"),
so the room doesn't brighten or darken when you enter. Don't zoom or move the camera. prep.py detects the empty
opening automatically, saves it as the exact background reference (`work/clean_plate.png`) and cuts it (and the
walk-in) out of the video. Without a clean plate the engine has to guess the room behind the head and torso.
The empty room can also be a **separate clip** filmed from the same locked phone position (before or after the talk):
```bash
.venv/bin/python scripts/plate_from_clip.py <job> <empty_room_clip>
```
It uses only the still, empty opening of that clip (stops when someone walks in), aligns it to the talk's own
background (ECC, affine) and matches exposure and colour per channel. Check `work/plate_check.jpg` (talk | plate |
difference) and the printed match numbers before processing.

```bash
.venv/bin/python scripts/background.py <job> <plate.jpg> --draft [--reveal SECONDS]   # drafts: half resolution, ~4x faster
.venv/bin/python scripts/background.py <job> <plate.jpg> [--reveal SECONDS]           # final: full resolution
# options: [--match 0.65] [--wrap 0.35] [--preview SECONDS]
```
Local portrait matting (MODNet) combined with a clean-room difference matte: with a static camera, the median of
the clip is the empty room, and anything that differs from it (fast hands, hair, arms) is kept as the person.
The empty room is learned only from frames where each spot is actually empty (the person is masked out first),
so the real wall next to the head is never mistaken for the person. Semi-transparent edges (hair) are
decontaminated against that empty room, so no rim of the old wall shows. Everything below the **desk line**
(`--desk auto`: about 1.2 face-heights under the chin; or a fraction like `0.9`; `off` for standing shots) is
in front of the person - the desk and resting forearms - and is kept as filmed, relit to match.
Use `--moving-camera` for handheld footage (model only). A plain or green wall behind the speaker gives the
cleanest result. Then the person is relit to the plate's brightness and colour, the plate's light
wraps onto their edges, and one vignette + grain goes over both so they share one camera. `--reveal` keeps the
real room until that moment and wipes to the new one (great when the speaker asks for it on camera).
Always run `--preview` on 1-2 frames and show the user before processing the whole clip. After processing, run
`scripts/bg_qa.py <job>`: it compares the original and the new video every other frame and reports where the
person was lost (red) or the old room leaked through (yellow), per second, with a sheet of the worst frames
(`work/bg_qa_sheet.jpg`). Fix or flag every failing second before the user sees the video. Known false positive:
an object that moved between the clean plate and the take (a chair, a door) is counted as "person"; look at the
sheet before acting on those seconds. The plate should match
the scene: indoor/outdoor, time of day, warm/cool light, camera height. Writes `public/source_bg.mp4`.

## 3. Read the transcript, fix it, write captions

- Fix obvious recognition errors (names, slang, mixed-language words). **List every correction for the user**;
  never change meaning silently. If unsure what was said, ask.
- Drop fillers ("um", "אה"). Captions: one idea per cue, <= ~42 characters, at most 2 lines,
  readable speed (<= ~20 chars/s), cue times from the word timestamps.
- Second language: translate the cues yourself, keeping the speaker's voice and the same timings
  (as `text2` for bilingual captions; keep the translation short enough for one line).
- In RTL captions keep quoted English as one run ("כי אני זוכר Is that cheese") - the engine isolates it.

## 4. Motion plan -> GATE 1 (approval)

Read references/motion-rules.md first. Then run the stage prompts in references/prompts/ in order, as your own
working steps (they produce material for the gates; they never replace them):
1. **Story & hook editor** (1-story-hook-editor.md): hook candidates, the open question and where it closes,
   the arc, a cut list. Verbatim spans only. Text mode: use 6-text-to-video-writer.md instead.
2. **Caption designer** (3-caption-designer.md): chunking, reading speed, emphasis words, RTL.
3. **Motion director** (2-motion-director.md): one element per beat, landing on its word, one focal point at a
   time, transform rather than replace.
4. **Sound designer** (4-sound-designer.md): sparse sounds on landings, music style, one silence beat.

Find the beats (see references/design-rules.md): hook, named references (shows, people, places, products),
the key concept, contrasts or choices, lists, numbers the speaker actually said, the twist/reveal, the question/CTA.
Map each beat to an element (references/plan-schema.md). Present a table to the user:

| # | time | what is said | element | why | teaches | check |
|---|---|---|---|---|---|---|

Also propose the **video catchphrase** (the main idea of the video, a line the speaker actually says, about 2-3 s) for the opener.
Also list: caption corrections, any on-screen facts you added (e.g. a show's years) with a source,
theme, sounds. **Stop and wait for approval.** Nothing is rendered before this.

## 5. Write and validate the plan

Write `<job>/plan.json` (schema in references/plan-schema.md, example in examples/). Then:
```bash
.venv/bin/python scripts/validate_plan.py <job>/plan.json
```
Fix every ERROR. Read the WARNs and fix what matters. Besides the schema it lints the motion rules: content by 0.5 s,
no gap over 6 s without a visual event, at most 2 graphics at once, reading speed (max 20 chars/s), caption
duration, punch-in limits, light-leak safety, sound-effect spacing, silence beats. Break a rule only on purpose
and say why at Gate 2.
The validator also enforces the **safe area** (x 60-900, y 220-1420: the parts of the frame no app UI covers)
and **keeps every card and panel off the presenter's face** (tracked in `faces.json`). Add `--fix` to move
cards automatically. See references/safe-zones.md.

### Virtual cameras (talking-head, automatic)

```bash
.venv/bin/python scripts/shots.py <job> [--plan plan.json]
```
Makes one fixed shot read as a multi-camera edit: camera A (wide, the original framing), B (medium, ~1.2x) and
C (close, ~1.4x; up to 1.7x in 16:9), cropped from the same frame and anchored on the tracked face. Camera changes
land on the pause cuts prep made (hiding the jump), else on sentence ends; shots last 3-8 s; never the same camera
twice; wide while cards need room, close on punch-ins and reveals; each zoomed shot pushes in ~1.5% (calm). Every
camera is tested against the cards and captions so the face stays clear. Close-up selfies (face taller than a
third of the frame) get no virtual cameras in 9:16 - there is no room to go closer. No AI-generated angles: the
footage stays real and local. Add a "camera" column (A/B/C) to the Gate 1 table.

## 6. Stills -> GATE 2 (approval)

```bash
.venv/bin/python scripts/render.py stills <job>        # key moments -> <job>/stills/sheet.jpg
```
The sheet shows guides: non-safe zones in red, the tracked face in green.
Look at it yourself first: everything inside the safe area, nothing covering the face/mouth,
Hebrew/English order correct, fonts loaded (no Times-like fallback), no overlaps.
Then run the **independent reviewer** (references/prompts/5-reviewer.md) as a separate agent that has not seen
your reasoning: give it only the stills, plan.json and transcript. Fix its blockers, and show its verdict to the
user with the stills. **Stop and wait for approval.** The reviewer never approves on the user's behalf.

## 7. Render, check, deliver

```bash
.venv/bin/python scripts/render.py video <job> --name <NAME>            # 540x960 draft (default, fast) for review
.venv/bin/python scripts/render.py video <job> --name <NAME> --final    # full 1080x1920, highest quality
```
Every review render is a **half-resolution draft (540x960)**. Render `--final` only for the approved final version.
One render per caption language (change `lang` + `captions` in the plan). After rendering, check:
duration matches, audio present, a few frames look right. Deliver the MP4s (1080x1920 or 1920x1080 H.264 high profile,
faststart; fine for Reels, TikTok, Shorts, YouTube, LinkedIn) and the `.srt` caption files written next to them
(one per caption language). With `"music"` in the plan, the bed is mixed in at render time and ducks under
the voice automatically. Rendering takes a few minutes per minute of video on 2 CPUs.
`--final` also writes `<NAME>_social.mp4`: the same picture at about 10 Mbps (small enough for scheduler APIs,
e.g. Instagram's ~300 MB limit) with the audio re-measured and normalised to -14 LUFS / -1 dBTP on the final file.
Deliver that copy for posting and keep the high-bitrate master as the archive. Measure the delivered file
(`ffmpeg -i <file> -af ebur128=peak=true -f null -`) and report its loudness.
The video keeps 1-2 quiet seconds after the last spoken word (prep keeps that tail), so the last word is never clipped.
Before any draft goes to the user: `render.py captions <job>` makes one still per caption from the draft (the caption
band, numbered); look at every tile for overlap, and run it again after every caption change.
With `"bumpers"` in the plan, render.py joins opener -> intro -> video -> outro (scripts/bumpers.py), shifts the .srt
files by the opener + intro length, and stops if sound and picture are out of sync (see Opener, intro and outro).

## Rules (non-negotiable)

- Never invent facts, numbers, quotes or stories. On-screen facts beyond the transcript (dates, titles)
  must be verified and shown to the user at Gate 1.
- Don't draw recognisable characters, logos or copyrighted artwork; use type and the built-in generic icons.
  Exception: the `logo` element may show a real logo the user owns (their own venture), only with their explicit
  OK, built from the brand's own spec or files, once, at the moment they name it.
- Music only from the built-in generator (`scripts/make_music.py`). Never download or embed songs; if the user
  wants a song, they add it in the platform's own library after export.
- Sounds only from the local kit (pop, whoosh, ding, tick, rise - generated, licence-free). Never meme or
  TV/game/OS sounds, never sounds fetched from the web at render time.
- Nothing is uploaded: no cloud transcription, no hosted renderers, no AI avatars or voice cloning.
- Two gates, always: plan approval before stills; stills approval before the final render.
- Safe area always (9:16): nothing in the top 220 px, bottom 500 px, left 60 px or right 180 px (app UI lives there).
  16:9: keep 96 px side margins and clear of the bottom 90 px (player controls); the engine's wide stage does this.
- Never cover the presenter's face. Hands may pass over cards; cards may not cover the face or mouth.
- Max ~1 card per 5-8 seconds. No flashing (light leaks >= 1s apart).
- Zooms only via `punchin` elements (never ffmpeg zoompan).

### Kinetic captions (recommended)

`"captionStyle": "kinetic"` in a talking-head plan: the caption line is laid out at once (never reflows), upcoming
words wait dimmed and each word lights up on the frame it is said. Each cue may name ONE `emph` word - the word that
carries the point (about one every 3-4 s): when said it takes the accent colour, the heaviest weight, grows ~14% and
a marker sweeps under it while the rest of the line steps back. Run `scripts/word_times.py <job> [--plan P]` after the
captions are final (exact per-word times where the caption matches the transcript, otherwise spread over the speech).
Without `captionStyle` the captions are classic cue-by-cue captions. Pick `emph` words at Gate 1 (add an "emph" column).
Caption fit (validator errors, measured with the bundled fonts): over the footage a two-language cue has room for ONE
line above the translation line - keep those cues to ~26 Latin characters or split them; in a cutaway the caption has
two lines of 74 px from y 1050 and the translation line sits at ~1255 - a cue that needs a third line is split. A
Hebrew prefix glued to a Latin word with a hyphen ("ב-AI") renders in the wrong order: reword it ("בעזרת AI").

### Context elements: a visual every 2-5 s
Plan density is part of the quality, not decoration: for each idea he says, something on screen names it - an `icon`
(with a 1-3 word English label; 28 original icons incl. wand, film, code, palette, scissors, zoom, rocket, people, tag,
mute, gear, loop, gap, sparkle), a `keyword` sticker, a `list` or `compare`, a punch-in on the turn. Aim for 40-55
elements in a ~2:20 video, never a gap over 6 s. Labels must be short (the validator measures the width; long labels
run into the face or out of the safe area). In talking-head mode, icons/cards sit above the head (y 300-500); if a card
can't fit there, turn it into a smaller keyword sticker.

### Panels where he points
Read the frame at each pointing word ("here... and here") and put each panel on THAT side and height: e.g. right hand
high -> upper right, right hand low -> lower right; `spawn` = his hand position. The validator judges a pinned panel by
how often it really covers his face (OK if < 15% of the face in >= 85% of samples), so a panel may stay where he
pointed even if he leans toward it for a moment.

### Gesture sync: effects start on his snap
When he triggers an effect with a gesture (finger snap, clap) - the background change, panels starting to play, a
reveal - the effect starts on the frame of the snap, not on the word. Find it with
`scripts/snaps.py <job> --near <word time> [...]` (reads the un-cleaned cut audio work/joined.mp4: a snap is a ~5 ms
broadband click, much brighter than speech), then CHECK the frame at that time (his fingers mid-snap). Use it for
`background.py --reveal <snap>`, media `playAt`, and the punch-in/sfx on that beat. If no snap is found near the word,
look at the frames; if there is none, fall back to the word. Snaps can come seconds after the word.

### Cutaways: full-screen animation over the voice
`{"type": "cutaway", "start", "end"}` cuts the picture from him to the canvas layout (brand background, big scene,
kinetic captions) while his voice continues; soft circular reveal in and out. Elements starting inside the window are
drawn as full-screen scenes: `diagram` (preferred for lists, steps, processes, comparisons: see "Diagrams"), `list`
(items appear on the words), `icon` (big, with kicker + caption), `keyword`, `compare`, `flow` (problem card -> drawn
arrow -> answer card, up to 3 rows), `image` with `"full": true` (`"diagram": true` for a pre-rendered diagram).
CLAUDE DECIDES where (Gate 1 column "picture: him / cutaway"):
- YES when he is explaining an idea, a list, a process, a before/after, a number - something a picture explains better
  than his face; or a big emotional beat that an image can carry ("such a crazy time" -> a rocket launch).
- NO in the hook (first 3 s) or the last 2 s, while he points at or shows something (panels, logo, background reveal),
  on a punch-in, on a personal admission or a joke (his face sells it), or twice within 6 s.
- 2.5-9 s each, 3-5 per ~2-minute video, <= 30% of the running time in total (validator enforces).

### Diagrams: lists, steps, processes and comparisons as animated diagrams
Recommendation (judgement, not a hard rule): when the speaker talks about a list, steps, instructions, a process, a
comparison or a change over time, show it as an animated diagram in a cutaway, not as text cards; it makes the idea
easier to process. Keep the speaker on screen between diagrams: about one visual moment every ~20 s, with small keyword
and icon cards in between, works well in a 2-minute video.
`{"type": "diagram", "kind", "start", "end", "kicker"?, ...}` (engine/src/components/Diagrams.jsx), canvas only (inside a
cutaway; or voice/text modes). Every timed part takes `at` (s) or `word` (a word the speaker says, the first time after
the element's start, from the caption word times - run word_times.py first). Content stays in y 300-1000 (header above,
canvas captions from y 1050). Theme colours, fonts, card shape and entrance timing.

| kind | when the speaker says | fields |
|---|---|---|
| `balance` | one side wins over the other | `left`/`right` {text, icon?, at/word}, `tipAt`/`tipWord`, `tip` "left"/"right" (goes down) |
| `link` | A becomes B, with a time or a cost | `from`/`to` {text, icon?}, `fillAt`, `doneAt` (or `fillWord`/`doneWord`), `timer` {from, to, suffix} or {text}, `result` {text, at/word} |
| `steps` | steps, instructions, a recipe; the last step can fan out | `items` [{text, at/word}] (<= 5), `fan` {items [text], at/word} |
| `table` | then vs now, old way vs new way | `columns` [then, now], `rows` [{then, now, at/word}], `nowAt`/`nowWord` |
| `device` | "it all fits in your phone" | `at`/`word` (the phone rises), `items` [{text, icon?, at/word}] |
| `beforeafter` | one before, one after | `before`/`after` {title?, text, at/word} |
| `cycle` | a loop that repeats | `items` [{text, at/word}] (3-5), `closeAt`/`closeWord` |
| `funnel` | many narrowed down to one | `items` [{text, at/word}] (widest first) |
| `timeline` | how something changed over time | `items` [{when, text, at/word}] |

Pre-rendered diagrams (HTML animated with scripts/animate_slide.py) work as a full image with `"diagram": true`: no push
zoom, no dark gradient, and the theme colours are kept. At Gate 1 the motion director proposes a diagram (kind + trigger
words) for each list / steps / process / comparison / before-after in the transcript. Test plans for every pattern:
examples/diagram_test_plans.py.

### A word behind the speaker's head
`{"type": "behind", "text": "WORD", "start", "end"}` puts one big word INTO the scene: on the footage, behind the head
and shoulders (a MODNet portrait matte per frame, single take, no clean plate). After the timings are final run
`.venv/bin/python scripts/behind.py <job>`: it writes the cut-outs to public/behind/<n>/ and the word's position
(centred on the head, kept inside x 60-900 and under the header) into the plan; re-run it after any timing change (the
validator checks). Theme accent with a thin dark edge (reads on a light wall), about 3 s, once or twice per video, on a
key word. Talking-head only, not inside a cutaway. Moves with the virtual cameras and punch-ins.

### Looks
Each theme has a default look (engine/src/lib/theme.js `SERIES_LOOK`): caption style (plate / scrim / panel), emphasis
(marker / glow / solid), card shape (tilt / rule / bracket), entrance (pop / wipe / snap), cutaway transition (circle /
dissolve / wipe), film grain, vignette, picture grade, default music bed and sound-effect level. Mix your own per video
with `plan.look`, e.g. `{"caption": "scrim", "emph": "glow", "sticker": "rule", "cut": "dissolve", "grain": 0.06}`.

### Images in cutaways
For a cutaway an image explains better than an animation (a scene, a feeling, a metaphor), use the speaker's own photos
or images they have the rights to: put them in `<job>/public/`.
Plan: `{"type": "image", "full": true, "src", "start", "end", "move": push|pull|rise|drift, "focus"}` inside a cutaway,
plus at most one keyword/caption line on top. Show every image at Gate 2.
If an image is AI-generated: no people, no hands, no logos, no readable text; follow the generator's terms and switch on
the platform's "AI info" label when posting. Never use film/TV clips, in-app sticker or GIF libraries, or stock footage
you have no licence for.

### Upgrading the engine: always side by side
Build every upgrade on its own branch, opt-in (plans without the new field render exactly as main). Render the SAME
full plan of a real take both ways and join them: `ffmpeg -i A.mp4 -i B.mp4 -filter_complex "[0:v]pad=iw:ih+70:0:70,
drawtext=text='A current'...[a];[1:v]pad...[b];[a][b]hstack=2" -map 1:a ...`. The user decides; only then merge to main.
Keep the previous main as a `baseline-YYYY-MM-DD` branch. Test plans
must be full Gate-1 quality (density, emphasis, panels at gestures) or the comparison is meaningless.

### Opener, intro and outro (optional: `"bumpers"` in the plan)
Every video runs: **video catchphrase (opener) -> 2 s brand intro -> the full video -> 3 s outro**. No video opens on a logo.
- **Opener** = the video's catchphrase: the main idea of that one video, in the speaker's own words, picked by Claude at Gate 1.
  Same template every time (`Bumper` composition, kind "opener"): his footage and voice for that line, a slow push-in,
  the line once in big kinetic type with one word lit, the second-language line under it; nothing else on screen
  (no header, bar, icons or panels). End it in the pause AFTER the last word: check the audio envelope, because
  transcript word times can run 0.2-0.3 s early.
  Filming tip: decide the line before filming and leave a short pause before and after it.
- **Intro (2 s)**: the soundtrack bar draws, the play triangle presses in, the wordmark + series label land with the
  brand catchphrase, then everything fades and the video's header takes over.
- **Outro (3 s)**: the wordmark, "Follow" (Hebrew: "עקבו אחריי") + the handle (`bumpers.handle`), the brand catchphrase
  again, your website (`brand.site`, optional), platform names as small text (no logos); the bar runs to the end and the
  play triangle turns into pause.
- **Brand catchphrase** (`bumpers.catchphrase`, from brand.json): the user's own brand line, shown as a title, so no
  full stop. Hebrew (RTL) videos can put the Hebrew line first and the English one under it (`catchphrase2`).
- **Sound logo** (scripts/sound_logo.py): three notes, the same melody in every theme; pluck (light), piano (dark), synth (bold);
  the outro resolves to the octave on the pause.
- **Sync**: prep.py cuts on whole frames, keeps PCM sound exactly as long as each piece of picture, and checks the cut
  (fails above 20 ms), so the voice never drifts from the lips.
- **Joins**: bumpers.py cuts or pads every part's audio to its exact picture
  length (frames / fps) before joining, so nothing drifts, then cross-correlates the joined file against the rendered
  video at 5 points and refuses to deliver if any is off by more than 20 ms. render.py also checks that sound and
  picture are the same length. Before any final, watch the opener and two talking moments for lip sync.
- Hand-joined previews: `scripts/bumpers.py <job> --video out/<NAME>_draft540.mp4 --plan <plan>`.
