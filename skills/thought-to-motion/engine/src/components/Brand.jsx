import React from "react";
import { AbsoluteFill, Img, random, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// Safe area for 9:16 feeds, strictest of TikTok / Instagram Reels / YouTube Shorts (checked Oct 2026):
// platform UI covers the top 220px, the bottom 500px (Reels captions), the left 60px and the right 180px
// (TikTok's button column). Everything we draw stays inside SAFE. See references/safe-zones.md.
export const SAFE = { top: 220, bottom: 1420, left: 60, right: 900 };

// The wordmark in the header: brand.wordmark in the theme's ink (replace with your own logo treatment).
export const Badge = ({ t, text, size = 28, ls = 0.18 }) => (
  <span style={{ display: "inline-block", fontFamily: t.ui, fontWeight: 800, fontSize: size, lineHeight: 1, letterSpacing: `${ls}em`,
    color: t.ink, textTransform: "uppercase" }}>{text}</span>
);

// The series label. Short all-capital words inside it are set heavier so an I reads as a capital, not an l.
export const SeriesLabel = ({ text, weight = 500 }) => (
  <>{String(text).split(/(\b[A-Z]{1,3}\b)/).map((part, i) => /^[A-Z]{1,3}$/.test(part)
    ? <span key={i} style={{ fontWeight: Math.max(700, weight + 200), margin: "0 0.12em" }}>{part}</span> : <React.Fragment key={i}>{part}</React.Fragment>)}</>
);

export const Header = ({ t, brand, surface }) => {
  if (!brand?.wordmark) return null;
  const chip = surface === "overlay";
  return (
    <div style={{ position: "absolute", top: SAFE.top + 12, left: SAFE.left, display: "flex", alignItems: "center", gap: 14,
      ...(chip ? { background: t.paper, padding: "10px 22px 10px 10px", borderRadius: 16, boxShadow: "0 6px 24px rgba(0,0,0,0.18)" } : {}) }}>
      <Badge t={t} text={brand.wordmark} />
      {brand.series && <span style={{ fontFamily: t.ui, fontWeight: 500, fontSize: 26, color: t.accent }}><SeriesLabel text={brand.series} /></span>}
    </div>
  );
};

// The signature: profile picture + name + handle. brand.avatar = a file in the job's public folder.
export const Signature = ({ t, brand, size = 64, style = {} }) => {
  if (!brand?.avatar) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: Math.round(size * 0.25), ...style }}>
      <Img src={staticFile(brand.avatar)} style={{ width: size, height: size, borderRadius: size / 2, objectFit: "cover" }} />
      <div style={{ textAlign: "left", lineHeight: 1.15 }}>
        <div style={{ fontFamily: t.ui, fontWeight: 800, fontSize: Math.round(size * 0.44), color: t.ink }}>{brand.name || brand.wordmark}</div>
        <div style={{ fontFamily: t.ui, fontWeight: 500, fontSize: Math.round(size * 0.36), color: t.accent }}>{brand.handle || ""}</div>
      </div>
    </div>
  );
};

// "Soundtrack bar": a progress line with a play triangle, on the bottom edge of the safe area.
export const ProgressBar = ({ t, surface }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = frame / Math.max(1, durationInFrames - 1);
  const W = SAFE.right - SAFE.left - 50;
  const track = surface === "overlay" ? "rgba(255,255,255,0.45)" : "rgba(127,127,127,0.3)";
  return (
    <div style={{ position: "absolute", top: SAFE.bottom - 26, left: SAFE.left, width: SAFE.right - SAFE.left, display: "flex", alignItems: "center", gap: 22 }}>
      <svg width="28" height="32" viewBox="0 0 30 34"><path d="M2 2 L28 17 L2 32 Z" fill={surface === "overlay" ? t.paper : t.accent} /></svg>
      <div style={{ position: "relative", width: W, height: 5, background: track, borderRadius: 3 }}>
        <div style={{ position: "absolute", left: 0, top: 0, height: 5, width: W * p, background: t.accent, borderRadius: 3 }} />
        <div style={{ position: "absolute", left: W * p - 10, top: -7.5, width: 20, height: 20, borderRadius: 10, background: t.accent,
          border: surface === "overlay" ? `3px solid ${t.paper}` : "none" }} />
      </div>
    </div>
  );
};

export const PaperBackground = ({ t }) => {
  const frame = useCurrentFrame(); const { width, height } = useVideoConfig();
  // a slow-drifting glow (upper middle), plus the mood's fixed marks: B = top bar, C = faint 60px grid
  const glow = t.glow || t.marker;
  const cx = width / 2 + Math.sin(frame / 90) * width * 0.2, cy = height * 0.36 + Math.cos(frame / 110) * height * 0.08;
  const r = Math.max(width, height) * 0.45;
  return (
    <AbsoluteFill style={{ background: t.paper }}>
      {t.grid && <AbsoluteFill style={{ backgroundImage: `linear-gradient(${t.grid} 2px, transparent 2px), linear-gradient(90deg, ${t.grid} 2px, transparent 2px)`,
        backgroundSize: "60px 60px", opacity: 0.9 }} />}
      <div style={{ position: "absolute", left: cx - r, top: cy - r, width: 2 * r, height: 2 * r, borderRadius: r,
        background: `radial-gradient(circle, ${glow}AA 0%, ${glow}00 70%)` }} />
      {t.topBar !== false && <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 14, background: t.accent }} />}
    </AbsoluteFill>
  );
};

// Review guides for stills (plan.guides = true): non-safe zones in red, the presenter's face in green.
export const Guides = ({ plan }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  if (!plan.guides) return null;
  const t = frame / fps;
  let box = (plan.faces?.boxes || []).reduce((best, b) => (b[1] != null && Math.abs(b[0] - t) < Math.abs((best?.[0] ?? 1e9) - t) ? b : best), null);
  const shot = (plan.shots || []).find((s) => t >= s.start && t < s.end);
  if (box && shot && shot.zoom > 1) {  // the face as the current virtual camera sees it
    const z = shot.zoom; box = [box[0], (box[1] - shot.x) * z, (box[2] - shot.y) * z, box[3] * z, box[4] * z];
  }
  const red = "rgba(255,40,40,0.28)";
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: SAFE.top, background: red }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: SAFE.bottom, bottom: 0, background: red }} />
      <div style={{ position: "absolute", left: 0, width: SAFE.left, top: SAFE.top, height: SAFE.bottom - SAFE.top, background: red }} />
      <div style={{ position: "absolute", left: SAFE.right, right: 0, top: SAFE.top, height: SAFE.bottom - SAFE.top, background: red }} />
      {box && <div style={{ position: "absolute", left: box[1], top: box[2], width: box[3], height: box[4], border: "6px solid #22e06b", borderRadius: 12 }} />}
    </AbsoluteFill>
  );
};

// Series texture (lib/theme.js SERIES_LOOK): film grain + edge vignette, the dark theme only. Drawn over his footage and over
// the canvas, under the captions and cards. Grain is seeded per 2 frames so it shimmers like film, not like video noise.
export const Texture = ({ t, under = false }) => {
  const frame = useCurrentFrame(); const { width, height } = useVideoConfig();
  const look = t.look || {};
  if (!look.grain && !look.vignette) return null;
  const seed = Math.floor(frame / 2); const dots = [];
  const n = Math.round(900 * (look.grain || 0) / 0.07);
  for (let i = 0; i < n; i++) {
    dots.push(<div key={i} style={{ position: "absolute", left: random(`gx${seed}-${i}`) * width, top: random(`gy${seed}-${i}`) * height,
      width: 2, height: 2, background: random(`gc${seed}-${i}`) > 0.5 ? "#FFFFFF" : "#000", opacity: 0.22 }} />);
  }
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {look.vignette ? <AbsoluteFill style={{ background: `radial-gradient(ellipse 78% 62% at 50% 42%, rgba(0,0,0,0) 55%, rgba(0,0,0,${look.vignette}) 100%)` }} /> : null}
      {dots}
    </AbsoluteFill>
  );
};

// the dark theme captions sit on no plate: a soft dark band rises from the bottom behind them instead.
export const CaptionScrim = ({ t }) => {
  if (t.look?.caption !== "scrim") return null;
  return <AbsoluteFill style={{ pointerEvents: "none", background:
    "linear-gradient(to bottom, rgba(0,0,0,0) 52%, rgba(10,8,6,0.55) 64%, rgba(10,8,6,0.72) 76%, rgba(10,8,6,0.55) 100%)" }} />;
};
