import React from "react";
import { Easing, interpolate, spring as remotionSpring, useCurrentFrame, useVideoConfig } from "remotion";

// Motion style. "calm" = critically damped springs: elements settle without bounce (plan.motion = "calm").
export const MOTION = { calm: false };
export const spring = (opts) =>
  remotionSpring(MOTION.calm ? { ...opts, config: { damping: 200, stiffness: 110, mass: 1, overshootClamping: true } } : opts);

// Motion tokens (references/motion-rules.md): entrances decelerate, exits accelerate, on-screen moves use standard easing.
export const EASE = {
  enter: Easing.bezier(0.05, 0.7, 0.1, 1),
  calmEnter: Easing.bezier(0, 0, 0.3, 1),
  exit: Easing.bezier(0.3, 0, 0.8, 0.15),
  move: Easing.bezier(0.2, 0, 0, 1),
};
// Entrance durations in frames by element size; exits take ~70% of the entrance.
export const DUR = { micro: 5, small: 8, medium: 12, large: 18 };

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };
export const sec = (s, fps) => Math.round(s * fps);

// Enter with a spring at `start`, fade out over `outFrames` before `end`.
export const useWindow = (start, end, outFrames = 8, cfg = { damping: 15, stiffness: 170 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = sec(start, fps), b = sec(end, fps);
  const s = spring({ frame: frame - a, fps, config: cfg });
  const out = interpolate(frame, [b - outFrames, b], [1, 0], { ...clamp, easing: EASE.exit });
  return { frame, fps, s, o: Math.min(1, s * 1.4) * out, visible: frame >= a - 1 && frame <= b };
};

export const isRtl = (lang) => ["he", "ar", "fa", "yi"].includes(lang);

// Latin runs inside RTL text (e.g. an English quote in a Hebrew sentence) are kept together
// and isolated as LTR, so word order and trailing "?" stay correct.
const LATIN_RUN = /[A-Za-z“”"'][A-Za-z0-9“”"' ,.?!-]*[A-Za-z0-9?!.”]|[A-Za-z]/g;

export const bidiText = (txt) => {
  const out = []; let last = 0, m, k = 0;
  const re = new RegExp(LATIN_RUN.source, "g");
  while ((m = re.exec(txt))) {
    if (m.index > last) out.push(<span key={k++}>{txt.slice(last, m.index)}</span>);
    out.push(<span key={k++} dir="ltr" style={{ unicodeBidi: "isolate" }}>{m[0]}</span>);
    last = m.index + m[0].length;
  }
  if (last < txt.length) out.push(<span key={k++}>{txt.slice(last)}</span>);
  return out;
};

// Tokens for word-by-word animation. In RTL text, each Latin run is one token.
export const tokens = (txt, rtl) =>
  rtl ? (txt.match(new RegExp(LATIN_RUN.source + "|[^\\s]+", "g")) || []) : txt.split(/\s+/).filter(Boolean);

// Series entrance (lib/theme.js SERIES_LOOK.enter) for an overlay element that starts at `start` (seconds).
// Returns { p, style }: p = 0..1 progress, style = the transform / clip for the wrapper.
//   pop  (B): scale + small rotate, the existing sticker pop      wipe (A): left-to-right reveal, slow, barely moves
//   snap (C): short fast slide from the left, no scale
export const useEnter = (t, start, { rotate = 0, origin = "left center" } = {}) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const look = t.look || {}; const a = sec(start, fps); const n = look.enterFrames || 12;
  if (look.enter === "wipe") {
    const p = interpolate(frame, [a, a + n], [0, 1], { ...clamp, easing: EASE.calmEnter });
    return { p, style: { clipPath: `inset(-20% ${(1 - p) * 100}% -20% -4%)`, transform: `translateX(${(1 - p) * 18}px)` } };
  }
  if (look.enter === "snap") {
    const p = interpolate(frame, [a, a + n], [0, 1], { ...clamp, easing: EASE.enter });
    return { p, style: { transform: `translateX(${(1 - p) * -36}px)`, clipPath: p < 0.04 ? "inset(0 100% 0 0)" : "none" } };
  }
  const p = spring({ frame: frame - a, fps, config: { damping: 15, stiffness: 170 } });
  return { p, style: { transform: `scale(${0.6 + 0.4 * p}) rotate(${rotate}deg)`, transformOrigin: origin } };
};
