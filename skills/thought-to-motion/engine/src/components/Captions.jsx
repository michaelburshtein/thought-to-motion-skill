import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { bidiText, isRtl, sec, spring, tokens } from "../lib/util";
import { SAFE } from "./Brand";

const isKey = (w, keywords) => {
  const clean = w.replace(/[,.?!“”"']/g, "").toLowerCase();
  return keywords.some((k) => clean.includes(k.toLowerCase()));
};

// ---------- kinetic type (plan.captionStyle = "kinetic", 2026-10-22, branch kinetic-type) ----------
// The whole line is laid out at once (so it never reflows), upcoming words wait dimmed, and each word lights up on the
// frame it is SAID (cue.words = [{w, s}] from scripts/word_times.py; evenly spread if missing). The cue's emphasis word
// (cue.emph, or any plan.keywords match) is the point of the line: when said it takes the accent colour, the heaviest
// weight, grows ~14% and a marker sweeps under it, while the rest of the line steps back slightly. Calm, no bounce.
const clean = (w) => w.replace(/[,.?!:;“”"'׳״]/g, "");
const wordTimes = (cue, words) => {
  if (Array.isArray(cue.words) && cue.words.length === words.length) return cue.words.map((x) => x.s);
  const span = Math.max(0.3, (cue.end - cue.start) * 0.8);
  const total = words.reduce((n, w) => n + Math.max(2, w.length), 0);
  let acc = 0;
  return words.map((w) => { const st = cue.start + (span * acc) / total; acc += Math.max(2, w.length); return st; });
};
const isEmph = (w, cue, plan) => {
  const c = clean(w).toLowerCase();
  if (!c) return false;
  if (cue.emph) return clean(cue.emph).toLowerCase().split(/\s+/).includes(c);
  return isKey(w, plan.keywords || []);
};

export const KineticLine = ({ t, plan, cue, rtl, size }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const words = tokens(cue.text, rtl);
  const times = wordTimes(cue, words);
  const emphIdx = words.findIndex((w) => isEmph(w, cue, plan));
  const emphOn = emphIdx >= 0 ? spring({ frame: frame - sec(times[emphIdx], fps), fps, config: { damping: 200, stiffness: 140, overshootClamping: true } }) : 0;
  // series look (lib/theme.js SERIES_LOOK): B = marker behind the word, A = accent word with a soft glow, C = accent word only
  const look = t.look || {}; const emphStyle = look.emph || "marker"; const grow = look.emphScale ?? 0.14;
  const rise = look.enter === "wipe" ? 0.08 : look.enter === "snap" ? 0.12 : 0.22;   // A barely moves, words fade up
  return (
    <div dir={rtl ? "rtl" : "ltr"} style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: size * 0.26, rowGap: 2,
      fontFamily: rtl ? t.rtl : t.ui, fontSize: size, lineHeight: 1.16 }}>
      {words.map((w, i) => {
        const on = spring({ frame: frame - sec(times[i], fps), fps, config: { damping: 200, stiffness: 220, overshootClamping: true } });
        const emph = i === emphIdx;
        const back = emph ? 1 : 1 - 0.18 * emphOn;            // the rest of the line steps back while the point lands
        const col = emph && on > 0.01 ? t.accent : "#fff";
        return (
          // In a Hebrew line every word is laid out right-to-left, numbers and English words included: with dir="auto" a
          // token like "2019?" or "40." resolved left-to-right and its punctuation landed on the wrong side.
          <span key={i} dir={rtl ? "rtl" : "auto"} style={{ unicodeBidi: "isolate", display: "inline-block", position: "relative",
            fontWeight: emph ? 900 : (look.caption === "scrim" ? 700 : 800), color: col,
            opacity: (0.32 + 0.68 * on) * back,
            textShadow: emph && emphStyle === "glow" ? `0 0 ${Math.round(size * 0.45 * emphOn)}px ${t.accent}99, 0 3px 10px rgba(0,0,0,0.55)` : undefined,
            transform: `translateY(${(1 - on) * size * rise}px) scale(${emph ? 1 + grow * on : 1})`, transformOrigin: "50% 80%",
            // the emphasised word grows 14% from its centre: give it room on both sides in proportion to its own width,
            // or a long word (with its marker) touches its neighbour ("עקביות,שנה"; review 2026-10-27)
            margin: emph ? `0 ${size * (0.05 + (0.028 * grow / 0.14) * Math.max(2, w.length))}px` : 0 }}>
            {emph && emphStyle === "marker" && <span style={{ position: "absolute", left: -6, right: -6, bottom: "6%", height: "30%", borderRadius: 4,
              background: t.marker, opacity: 0.85, transform: `scaleX(${emphOn})`, transformOrigin: rtl ? "right" : "left", zIndex: -1 }} />}
            {w}
          </span>
        );
      })}
    </div>
  );
};

// Overlay captions for talking-head mode: one cue at a time, pops in, keywords tinted.
export const OverlayCaptions = ({ t, plan }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const time = frame / fps;
  const cue = plan.captions.find((c) => time >= c.start && time < c.end);
  if (!cue) return null;
  const rtl = isRtl(plan.lang);
  // back-to-back cue (the previous one ends on this one's first frame): keep the plate up instead of fading it in again,
  // or every cue change blinks for ~3 frames. The words still light up one by one.
  const joined = plan.captions.some((c) => c !== cue && Math.abs(c.end - cue.start) < 1.5 / fps);
  if (plan.captionStyle === "kinetic") {
    const two = plan.lang2 && cue.text2, rtl2 = isRtl(plan.lang2);
    const size = two ? (rtl ? 52 : 50) : (rtl ? 62 : 58);
    const s = joined ? 1 : spring({ frame: frame - sec(cue.start, fps), fps, config: { damping: 200, stiffness: 260, overshootClamping: true } });
    const cap = t.look?.caption || "plate";
    // B plate: rounded warm-dark plate. A scrim: no plate at all, the text sits on a soft dark band (CaptionScrim, drawn
    // once under the whole caption area). panel: a square panel with an accent edge.
    const box = cap === "scrim" ? { padding: "6px 10px", background: "none", textShadow: "0 2px 14px rgba(0,0,0,0.85), 0 1px 3px rgba(0,0,0,0.9)" }
      : cap === "panel" ? { padding: "10px 24px", borderRadius: 6, background: "rgba(15,27,45,0.78)", borderLeft: `5px solid ${t.accent}`,
        textShadow: "0 2px 8px rgba(0,0,0,0.5)" }
      : { padding: "10px 26px", borderRadius: 16, background: "rgba(20,16,14,0.58)", textShadow: "0 3px 10px rgba(0,0,0,0.55)" };
    return (
      <div style={{ position: "absolute", bottom: 1920 - (SAFE.bottom - 40), left: SAFE.left, width: SAFE.right - SAFE.left, display: "flex", justifyContent: "center" }}>
        <div style={{ ...box, maxWidth: SAFE.right - SAFE.left, textAlign: "center", opacity: Math.min(1, s * 2), isolation: "isolate" }}>
          <KineticLine t={t} plan={plan} cue={cue} rtl={rtl} size={size} />
          {two && (
            <div dir={rtl2 ? "rtl" : "ltr"} style={{ marginTop: 6, fontFamily: rtl2 ? t.rtl : t.ui, fontWeight: 700,
              fontSize: Math.min(36, Math.floor(780 / Math.max(1, cue.text2.length * 0.55))), whiteSpace: "nowrap",
              lineHeight: 1.15, color: cap === "scrim" ? t.ink : "rgba(255,255,255,0.82)", opacity: cap === "scrim" ? 0.86 : 1,
              ...(cap === "scrim" ? { fontWeight: 600, letterSpacing: "0.01em" } : {}) }}>
              {rtl2 ? bidiText(cue.text2) : cue.text2}
            </div>
          )}
        </div>
      </div>
    );
  }
  const s = joined ? 1 : spring({ frame: frame - sec(cue.start, fps), fps, config: { damping: 16, stiffness: 260 } });
  // Bilingual: plan.lang2 + cue.text2 adds a smaller second line in the other language.
  const two = plan.lang2 && cue.text2;
  const rtl2 = isRtl(plan.lang2);
  return (
    <div style={{ position: "absolute", bottom: 1920 - (SAFE.bottom - 40), left: SAFE.left, width: SAFE.right - SAFE.left, display: "flex", justifyContent: "center" }}>
      <div style={{ padding: "10px 26px", borderRadius: 16, background: "rgba(20,16,14,0.58)", maxWidth: SAFE.right - SAFE.left, textAlign: "center",
        textShadow: "0 3px 10px rgba(0,0,0,0.55)", transform: `scale(${0.88 + 0.12 * s})`, opacity: Math.min(1, s * 2) }}>
        <div dir={rtl ? "rtl" : "ltr"} style={{ fontFamily: rtl ? t.rtl : t.ui, fontWeight: 800, fontSize: two ? (rtl ? 52 : 50) : (rtl ? 62 : 58),
          lineHeight: 1.16, color: "#fff" }}>
          {rtl ? bidiText(cue.text) : cue.text}
        </div>
        {two && (
          // the translation always stays on ONE line (auto-shrinks), so captions never climb onto the face
          <div dir={rtl2 ? "rtl" : "ltr"} style={{ marginTop: 6, fontFamily: rtl2 ? t.rtl : t.ui, fontWeight: 700,
            fontSize: Math.min(36, Math.floor(780 / Math.max(1, cue.text2.length * 0.55))), whiteSpace: "nowrap",
            lineHeight: 1.15, color: "rgba(255,255,255,0.82)" }}>
            {rtl2 ? bidiText(cue.text2) : cue.text2}
          </div>
        )}
      </div>
    </div>
  );
};

// Kinetic captions for voice mode: big words appear across the cue; keywords get the marker.
export const KineticCaptions = ({ t, plan }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const time = frame / fps;
  const cue = plan.captions.find((c) => time >= c.start && time < c.end);
  if (!cue) return null;
  const rtl = isRtl(plan.lang);
  const words = tokens(cue.text, rtl);
  const span = Math.max(0.35, (cue.end - cue.start) * 0.75);
  const keywords = plan.keywords || [];
  return (
    <div dir={rtl ? "rtl" : "ltr"} style={{ position: "absolute", top: 1050, left: 90, width: SAFE.right - 90, height: 200,
      display: "flex", flexWrap: "wrap", alignContent: "flex-start", columnGap: 22, rowGap: 6 }}>
      {words.map((w, i) => {
        const wt = cue.start + (span * i) / words.length;
        const s = spring({ frame: frame - sec(wt, fps), fps, config: { damping: 14, stiffness: 220 } });
        const key = cue.emph ? isEmph(w, cue, plan) : isKey(w, keywords);
        return (
          <span key={i} dir="auto" style={{ unicodeBidi: "isolate", display: "inline-block",
            fontFamily: rtl ? t.rtl : t.ui, fontWeight: 800, fontSize: rtl ? 80 : 74, lineHeight: 1.15,
            color: key ? t.accent : t.ink, opacity: Math.min(1, s * 1.6), transform: `translateY(${(1 - s) * 30}px)`,
            textShadow: key && t.look?.emph === "glow" ? `0 0 26px ${t.accent}80` : "none",
            background: key && (t.look?.emph || "marker") === "marker" ? `linear-gradient(transparent 65%, ${t.marker} 65%)` : "none" }}>{w}</span>
        );
      })}
      {plan.lang2 && cue.text2 && (
        <div dir={isRtl(plan.lang2) ? "rtl" : "ltr"} style={{ position: "absolute", top: 205, left: 0, right: 0,
          // on a dark scrim the ink reads better than accent2 for small text
          fontFamily: isRtl(plan.lang2) ? t.rtl : t.ui, fontWeight: 700, fontSize: 36, color: t.look?.caption === "scrim" ? t.ink : t.accent2,
          textAlign: rtl ? "right" : "left",
          opacity: Math.min(1, spring({ frame: frame - sec(cue.start, fps), fps }) * 1.5) }}>
          {isRtl(plan.lang2) ? bidiText(cue.text2) : cue.text2}
        </div>
      )}
    </div>
  );
};
