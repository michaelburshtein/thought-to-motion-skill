# thought-to-motion

**A Claude skill that turns a talking-head clip, a voice note or plain text into a video with motion design timed to what you say.**

The thought is the product. Everything else (captions, cards, reveals, the design) is a layer.
This skill does the layers: it transcribes you with word-level timing, finds the beats in what you said,
plans motion around them, asks for your approval twice, and renders a 1080×1920 (9:16) or 1920×1080 (16:9) video
ready for Reels, TikTok, Shorts, YouTube or LinkedIn.

- **Talking-head mode**: your footage stays; captions, keyword cards, A/B reveals and a punch-in go on top.
- **Voice mode**: no camera needed. A branded full-frame canvas with scenes, big kinetic captions and a waveform of your actual voice.
- **Text mode**: no recording at all. Plain text becomes timed kinetic captions and scenes, with music.
- **Virtual cameras**: one fixed shot reads as a wide / medium / close multi-camera edit, cut on your pauses and anchored on your face. No AI-generated angles.
- **Original music**: a generated, copyright-free bed (calm / warm / pulse) that ducks under your voice. Nothing to be claimed.
- **Hebrew and English** (and other Whisper languages). Hebrew uses the [ivrit.ai](https://huggingface.co/ivrit-ai) model, with proper RTL captions that keep embedded English in order.
- **Studio-clean voice.** [DeepFilterNet3](https://github.com/Rikorose/DeepFilterNet) removes wind and background noise (about 20 dB quieter between words), then EQ, de-essing, compression and -14 LUFS loudness. Lip sync is preserved.
- **Background replacement** with light matching: local portrait matting (MODNet) plus a clean-plate difference matte (film the empty room first, in the same clip or a separate one), the person relit to the new room, light wrap and one shared grade, optional before/after wipe, and a QA pass that compares every other frame with the original.
- **Animated diagrams**: when you talk about a list, steps, a process, a comparison or a change over time, it becomes a diagram that builds as you say each part (balance, link with a timer, steps, then vs now, a phone that fills up, before/after, cycle, funnel, timeline).
- **A word behind your head**: one key word placed in the scene, behind your head and shoulders, from a single take.
- **Your own logo** can pop out where you point when you name your venture (only with your OK).
- **Show other videos on screen** as picture-in-picture panels that pop in when you point and play muted.
- **Everything runs locally.** No footage, audio or text leaves your machine.

## How it works

```
recording ──► prep.py ─────────► transcript with word timings (faster-whisper / ivrit.ai)
              (9:16, cut pauses,  │
               -14 LUFS)          ▼
                       Claude reads it, fixes recognition errors, writes captions,
                       finds the beats (hook, references, contrast, reveal, question)
                                  │
                         ┌────────▼────────┐
                         │ GATE 1: you OK  │  motion plan table
                         └────────┬────────┘
                       plan.json ─► validate_plan.py
                                  │
                         ┌────────▼────────┐
                         │ GATE 2: you OK  │  contact sheet of key frames
                         └────────┬────────┘
                       render.py video (Remotion + ffmpeg finishing pass) ──► MP4
```

## Install

```bash
npx skills add michaelburshtein/thought-to-motion-skill    # or copy skills/thought-to-motion into your .claude/skills
cd .claude/skills/thought-to-motion && bash scripts/setup.sh
```
Requirements: ffmpeg, Node 18+, Python 3.10+. Setup installs everything inside the skill folder
(a Python venv, `engine/node_modules` from the lockfile). Speech models download once from Hugging Face.

Then copy `brand.example.json` to `brand.json` and fill in your own name, handle and brand line.

Then ask Claude something like: *"Edit this video with thought-to-motion, Hebrew captions plus an English version"*
or *"Turn this voice note into a Reel."*

## What's inside

| path | what |
|---|---|
| `skills/thought-to-motion/SKILL.md` | the workflow Claude follows (setup → prep → plan → gate → stills → gate → render) |
| `references/plan-schema.md` | every element (title, keyword, compare, icon, image, list, diagram, behind, media, logo, endcard, punchin, sfx, lightleak, silence) and the plan options (mode, aspect, music, motion, shots) |
| `references/motion-rules.md`, `references/prompts/` | research-based motion rules and the six stage prompts (story, motion, captions, sound, independent reviewer, text-to-video) |
| `references/design-rules.md` | how spoken beats map to motion, rhythm, honesty and rights rules |
| `engine/` | a Remotion 4 project (pinned) that renders any plan in any mode; 3 neutral starter themes (light, dark, bold) and mix-and-match looks, to be replaced with your own brand |
| `scripts/` | `setup.sh`, `prep.py`, `prep_text.py`, `clean_audio.py`, `transcribe.py`, `faces.py`, `background.py`, `plate_from_clip.py`, `bg_qa.py`, `shots.py`, `snaps.py`, `behind.py`, `validate_plan.py`, `render.py`, `bumpers.py`, `make_music.py`, `make_sfx.py`, `sound_logo.py`, `animate_slide.py` |
| `brand.example.json` | your brand in one file: wordmark, series label, handle, brand line, theme. Copy it to `brand.json` |
| `examples/` | example plans (voice mode and talking-head) and test plans for every diagram pattern |

## Design choices (and why)

- **Two human gates.** Nothing renders until you approve the plan, and the final render waits for your OK on the stills.
- **No made-up content.** The skill never invents facts, numbers or quotes; added on-screen facts are listed for approval.
- **Licence-clean by construction.** Sound effects are generated from math. Icons are drawn in code. Fonts are bundled (OFL).
  No meme sounds, no recognisable characters or third-party logos.
- **Pinned and local.** Exact package versions, a lockfile, no global installs, no cloud APIs, no telemetry.

## Licences

- This repository: MIT, © 2026 Michael Burshtein.
- [Remotion](https://www.remotion.dev/license) has its own licence: free for individuals and companies of up to 3 people; larger companies need a company licence.
- Portrait matting: MODNet (Apache-2.0), ONNX build from Hugging Face (Xenova/modnet).
- Speech cleanup: DeepFilterNet3 (MIT / Apache-2.0), downloaded from its official GitHub release and checksum-verified.
- Speech models: OpenAI Whisper large-v3-turbo (MIT) and ivrit.ai whisper-large-v3-turbo-ct2 (Apache-2.0). Fonts: Inter, Heebo (SIL OFL 1.1).

Built with Claude by [Michael Burshtein](https://michaelburshtein.com), from a conversation about posting thoughts instead of formats.
A step-by-step guide for beginners: [michaelburshtein.com/thought-to-motion](https://michaelburshtein.com/thought-to-motion/).
