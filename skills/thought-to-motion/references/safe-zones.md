# Safe area, non-safe zones, and the presenter's face

## The safe area (9:16, 1080x1920)

Short-video apps draw their own UI over the video: the top bar (Following / For You, Reels header), the
right-hand button column (like, comment, share, profile), and the bottom block (username, caption text,
music line, CTA buttons). Those parts of the frame are the **non-safe zones** (also called UI overlap
areas or out-of-bounds zones). Anything placed there is covered or cluttered on at least one platform.

Measured margins on a 1080x1920 frame (sources below, checked Oct 2026):

| | top | bottom | left | right |
|---|---|---|---|---|
| TikTok | ~140-220 | ~400-480 | ~60 | ~180 |
| Instagram Reels | ~140-220 | ~450-500 | ~60 | ~130 |
| YouTube Shorts | ~150-160 | ~320-400 | ~60 | ~150 |
| **This skill (strictest of all three)** | **220** | **500** | **60** | **180** |

So the **safe area is x 60-900, y 220-1420**. Platforms change their UI; when in doubt, preview the upload
in each app before publishing.

## Rules the skill enforces

1. Everything the engine draws (header, captions, cards, panels, progress bar) stays inside the safe area.
   The engine constants live in `engine/src/components/Brand.jsx` (`SAFE`), the checker in `scripts/validate_plan.py`.
2. Nothing covers the presenter's face. `prep.py` tracks the face (YuNet, local) into `<job>/faces.json`;
   `validate_plan.py` checks every card and panel against the face during its time on screen and fails the plan
   if it overlaps. `--fix` moves movable cards (title, keyword, icon, compare, endcard, list) to the nearest clear
   spot: first the band above the head under the header, then between the chin and the captions.
3. Captions sit at the bottom of the safe area and never climb onto the chin/mouth: the translation line in
   bilingual captions stays on one line (auto-shrinks), and a caption that would reach the face fails validation
   until it is split into shorter cues.
4. Gate 2 stills show the guides: non-safe zones tinted red, the tracked face outlined green. Use
   `render.py stills <job> --clean-stills` for stills without guides.

## Layout hints for talking-head framing

- Close-up framing (face fills the middle third): use the band y 290-590 above the head for cards and
  small panels (`slot: "row4-1".."row4-4"`, width <= 150), and keep cards short (one line).
- Mid shot (face in the upper third): cards fit between the chin and the captions; let `--fix` place them.
- Hands and gestures may pass over cards; the face may not.

Sources: wildandfreetools.com "Vertical Video Safe Zones 2026" (TikTok 220/480, Reels 220/450, Shorts 150/400);
brandeal.ai "TikTok Safe Zone 2026" (TikTok right ~180, Reels bottom ~500, left ~60); openclip.app "Safe zones"
(general 10-15% side margins, top ~12%, bottom 20-25%).
