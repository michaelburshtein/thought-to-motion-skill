# Motion rules (what makes these videos work)

Testable rules distilled from platform data, caption and accessibility standards and motion-system guidelines
(sources at the end). **[MUST]** rules are enforced by `validate_plan.py` where marked *auto*; **[SHOULD]** rules
are judgement calls for the planner and the reviewer. Frames at 30 fps: 3f = 100 ms, 6f = 200 ms, 12f = 400 ms.
Numbers marked *(convention)* are working defaults, not measured data.

## Story & hook
1. [MUST] Frame 0 is content (no logo, black or slate). The first element starts by 0.5 s; the promise is on screen by 3 s. *auto*
2. [MUST] The hook is a real line from the source: the belief people get wrong, the most surprising line, or the stake. Move it, never rewrite it.
3. [SHOULD] Open one question in the first 5 s and close it at 60-90% of the runtime; the payoff gets its own beat.
4. [MUST] One idea per scene; every element can say what it teaches in <= 12 words (the Gate 1 "Teaches" column).
5. [SHOULD] Follow an arc: question -> model -> proof -> turn -> payoff (or hook -> tension -> insight -> takeaway). Strongest material early.
6. [SHOULD] End on the takeaway or loop back to the opening line. End card <= 2-3.5 s; no "thanks for watching".
7. [MUST] The video works muted: the visuals and captions alone carry the claim.

## Pacing & rhythm
8. [SHOULD] A visual change every 2-5 s; no gap over 6 s without an element (captions alone don't count). *auto (warn)*
9. [MUST] Elements land on the word they illustrate: the entrance finishes 0-3f before that word starts.
10. [SHOULD] Pauses over 0.6 s are trimmed (prep does this) unless kept on purpose as a silence beat.
11. [SHOULD] Hold 1-1.5 s after a big reveal: nothing new enters.

## Motion & easing
12. [MUST] No linear easing on position or scale (linear only for fades, slow drifts, progress bars).
13. [MUST] Entrances decelerate, exits accelerate, moves on screen use standard easing. The engine's tokens:
    enter `bezier(0.05, 0.7, 0.1, 1)` (calm: `(0, 0, 0.3, 1)`), exit `(0.3, 0, 0.8, 0.15)`, move `(0.2, 0, 0, 1)`.
14. [MUST] Duration grows with size: micro (word, tick) 4-6f; small (icon, chip) 7-9f; medium (card, list, compare,
    panel) 10-14f; full-frame (transition, punch-in) 14-21f. Exits take ~70% of the entrance. Nothing under 3f, no entrance over 24f.
15. [MUST] Calm springs by default: no visible bounce (overshoot clamped). Small "pops" may overshoot <= 5%.
16. [MUST] One focal action at a time: at most 2 graphic elements on screen besides captions and the face. *auto*
17. [SHOULD] Group items enter 2-4f apart, or each on its own spoken word (lists already do this).
18. [SHOULD] Transform, don't replace: when the next beat is about the same thing, evolve the element (A vs B -> the winner) instead of exiting and entering a new one.
19. [SHOULD] Anticipate big reveals: a short setup (slight dim, a "rise" sound) 3-6f before.
20. [MUST] Punch-ins <= 1.12x for calm moments, <= 1.25x for emphasis, at most one per 8 s. *auto*
21. [MUST] No flashing: never more than 3 flashes a second; light leaks fade over >= 0.5 s at <= 0.35 opacity over a face, and >= 1 s apart. *auto*

## Typography & captions
22. [MUST] Reading speed <= 17 characters/s (hard max 20), counting spaces. *auto*
23. [MUST] Line length: <= 32 characters per line on 9:16, <= 42 on 16:9, at most 2 lines (1 line when a bilingual second line is shown).
24. [MUST] Each caption stays 0.83 s to 7 s. Break after punctuation or before a conjunction/preposition; never split
    article+noun, first+last name, or a verb from its negation/auxiliary. *auto (duration)*
25. [MUST] Contrast >= 4.5:1 between caption text and what is directly behind it (3:1 for large bold display text).
26. [SHOULD] At most one emphasised word per caption and about one every 3 s: the noun or number carrying the claim, by colour or weight, never a size jump.
27. [MUST] Hebrew/RTL: `dir="rtl"`, English and number runs isolated as LTR (the engine does this), punctuation at the correct edge.

## Sound
28. [MUST] Master at -14 LUFS integrated, true peak <= -1 dBTP (the render does a two-pass normalisation).
29. [MUST] Music sits >= 18 dB under the voice while speaking (ducked, ~150 ms attack, ~400 ms release).
30. [MUST] A sound effect peaks on the frame the element lands (+/-1f), not when it starts moving.
31. [SHOULD] Sound effects sparingly: >= 1 s apart, about one per 3 s on average, never on a stressed word, the same sound at most 3 times in a row. *auto (spacing)*
32. [SHOULD] One silence beat per video: the music dips 0.5-1.5 s at or just before the key line (`silence` element).

## Composition & checks
33. [MUST] Never cover the face (face box + padding); everything inside the platform safe area (references/safe-zones.md). *auto*
34. [MUST] Before Gate 2, an independent reviewer (prompts/5-reviewer.md) runs: first-3-seconds test, muted watch,
    audio-only listen, squint test (one dominant element per frame), phone-size legibility, safe area/face, truth check.
    It reports PASS/FIX; it never replaces the user's approval.

## Sources
Material 3 motion (easing and duration tokens, via the Android and Flutter docs); IBM Carbon motion; Apple Human Interface
Guidelines (motion); Remotion `spring` docs; Netflix Timed Text Style Guides (42 characters, 17/20 cps, 5/6 s-7 s);
BBC subtitle guidelines (160-180 wpm); WCAG 2.2 (1.4.3 contrast, 2.3.1 three flashes; technique G56: background audio
20 dB under speech); W3C inline bidi markup; Spotify loudness normalisation (-14 LUFS, -1 dBTP); TikTok creative best
practices (proposition in the first 3 s); Facebook mobile video research (value concentrated in the first 3-10 s);
YouTube audience-retention help; a study of 160 films on shortening shot lengths; information-gap theory of curiosity;
TikTok and Meta safe-zone compilations (third-party, re-check against current specs).
