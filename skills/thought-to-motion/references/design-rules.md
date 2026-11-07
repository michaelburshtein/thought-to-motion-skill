# Design rules: from what was said to what moves

Motion should explain or emphasise what the speaker is saying, at the moment they say it.
If an element doesn't do one of those two things, cut it.

## Finding the beats

Read the transcript once for structure, then mark:

1. **Hook** (first 2-3 s): the topic in a few words -> `title`. Use the speaker's framing, not a clickbait rewrite.
2. **Named references**: shows, books, people, places, products, concepts -> `keyword` on the word itself.
   Add a short factual subtitle only if it helps (years, what it is) and you have verified it.
3. **Contrast / choice / twist**: "was it X or Y", "I thought X, turns out Y", myth vs fact -> `compare`,
   options appearing when each is said, `marks` for "my memory"-type labels, `reveal` on the answer word,
   optional `punchin` + `ding` on the reveal.
4. **Lists and steps** -> `list`, one item per mention.
5. **Numbers the speaker says** -> a `keyword` with the number as the title. Never add numbers they didn't say.
6. **Emotion / reaction** ("my mind is blown", "I love this") -> a `note` on the current card or a short `icon`.
7. **Closing question / CTA** -> `endcard` over the last 3-4 s.

Voice mode needs a scene for every stretch of time (no empty stage longer than ~2 s): use `icon` scenes with a
kicker for connective parts (setting, mood), and the speaker's own photos (`image`) when they have them.

## Follow the speaker's gestures

When the speaker points ("here... and here"), place the content where they point. Look at frames around each
pointing word (a 0.3 s step), note the hand position in 1080x1920 coordinates, and:
- put the panel's `slot` as close to the hand as the safe area and the face allow (validate_plan.py checks both);
- set `spawn` to the hand position, so the panel visibly comes out of the hand even when its final spot has to
  move (e.g. the space beside the face is too narrow);
- time `start` to the moment the hand is at its peak, not the start of the word.
Tell the user which panels could not land exactly where they pointed, and why.

## Rhythm

- Element on screen >= 1.2 s; captions <= ~20 characters per second.
- Talking-head: at most ~1 card every 5-8 s, never two cards fighting for attention, face and mouth visible.
- Sound effects: <= 1 per ~6 s. Pop for cards, ding for a reveal, whoosh for the title. Volume 0.3-0.5.
- One light leak per video at most, usually on the title.

## Language

- Captions in the spoken language by default; offer a second language as a separate render.
- Card text may stay in the language the audience reads (e.g. English cards with Hebrew captions) - ask.
- Hebrew/Arabic: write naturally; keep quoted English as one run; the engine isolates it as LTR.

## Honesty and rights

- Show only what was said or what you verified. Put every added fact in the Gate 1 table.
- Generic icons and type only. No recognisable characters, logos, posters, or screenshots of other people's work.
- Sounds only from the local kit.
