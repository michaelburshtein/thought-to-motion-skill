import React from "react";
import { AbsoluteFill, Audio, Freeze, Img, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useAudioData, visualizeAudio } from "@remotion/media-utils";
import { EASE, bidiText, clamp, isRtl, sec, spring, useEnter, useWindow } from "../lib/util";
import { Icon } from "./Icons";
import { SAFE } from "./Brand";
import { Diagram } from "./Diagrams";

// Text in a plan can be in the video's language. RTL-aware wrapper.
const T = ({ plan, children, style }) => {
  const rtl = isRtl(plan.lang) && /[֐-׿؀-ۿ]/.test(children || "");
  return <span dir={rtl ? "rtl" : "ltr"} style={style}>{rtl ? bidiText(children) : children}</span>;
};
const Kicker = ({ t, children, color }) => (
  <div style={{ fontFamily: t.ui, fontWeight: 800, fontSize: 30, letterSpacing: "0.16em", color: color || t.accent, textTransform: "uppercase" }}>{children}</div>
);
const headFont = (t, rtlText) => (rtlText ? t.rtl : t.headline);
const hasRtl = (s) => /[֐-׿؀-ۿ]/.test(s || "");

// ---------- title: opening card ----------
const Title = ({ el, t, plan, surface }) => {
  const { s, o, visible, frame, fps } = useWindow(el.start, el.end);
  if (!visible) return null;
  const m = interpolate(frame, [sec(el.start, fps) + 10, sec(el.start, fps) + 26], [0, 1], { ...clamp, easing: EASE.move });
  const parts = (el.text || "").split(el.emphasis || "\u0000");
  const big = surface === "canvas";
  return (
    <div style={{ position: "absolute", top: big ? 380 : (el.top ?? 300), left: 72, right: 1080 - SAFE.right, opacity: o, transform: `translateY(${(1 - s) * 40}px)` }}>
      {el.kicker && <div style={{ marginBottom: 14, textShadow: big ? "none" : "0 2px 12px rgba(0,0,0,0.6)" }}>
        <Kicker t={t} color={big ? t.accent : "#fff"}>{el.kicker}</Kicker></div>}
      <div style={{ display: "inline-block", position: "relative", fontFamily: headFont(t, hasRtl(el.text)), fontWeight: t.headlineWeight,
        fontSize: el.size || (big ? 150 : 112), lineHeight: 1.0, color: t.ink,
        ...(big ? {} : { background: t.paper, padding: "8px 24px", borderRadius: 12 }) }}>
        {parts.length > 1 ? (<>
          {parts[0]}
          <span style={{ position: "relative", fontStyle: "italic", whiteSpace: "nowrap" }}>
            <span style={{ position: "absolute", left: -6, right: -6, bottom: "12%", height: "34%", background: t.marker,
              transform: `scaleX(${m})`, transformOrigin: "left", zIndex: -1 }} />{el.emphasis}</span>
          {parts.slice(1).join(el.emphasis)}
        </>) : <T plan={plan}>{el.text}</T>}
      </div>
      {el.subtitle && <div style={{ marginTop: 28, fontFamily: t.headline, fontStyle: "italic", fontSize: big ? 46 : 38,
        color: big ? t.ink : "#fff", opacity: 0.85, textShadow: big ? "none" : "0 2px 10px rgba(0,0,0,0.6)" }}>{el.subtitle}</div>}
    </div>
  );
};

// Level stickers for the "rule" and "bracket" looks. No tilt, no pop: they read as a lower-third / a label,
// not as a sticker on a fridge. Same palette and fonts as the series; only the shape and the motion change.
const Brackets = ({ color, size = 18, w = 3 }) => (
  <>
    {[["top", "left"], ["top", "right"], ["bottom", "left"], ["bottom", "right"]].map(([v, h]) => (
      <div key={v + h} style={{ position: "absolute", [v]: -6, [h]: -6, width: size, height: size,
        [`border${v[0].toUpperCase() + v.slice(1)}`]: `${w}px solid ${color}`, [`border${h[0].toUpperCase() + h.slice(1)}`]: `${w}px solid ${color}` }} />
    ))}
  </>
);
const KeywordLevel = ({ el, t, plan, o, accent, kind }) => {
  const { style } = useEnter(t, el.start);
  const rule = kind === "rule";
  const title = (
    <div style={{ fontFamily: rule ? headFont(t, hasRtl(el.title)) : t.headline, fontWeight: t.headlineWeight,
      fontSize: el.size || (rule ? 58 : 50), lineHeight: 1.05, letterSpacing: rule ? 0 : "-0.01em",
      color: accent ? t.accent : t.ink }}><T plan={plan}>{el.title}</T></div>
  );
  return (
    <div style={{ position: "absolute", top: el.top ?? 300, left: 72, opacity: o, ...style }}>
      <div style={{ position: "relative", maxWidth: 820, padding: rule ? "14px 26px 16px 24px" : "14px 24px",
        background: rule ? `${t.paper}E0` : `${t.paper}EB`, borderRadius: rule ? 3 : 0,
        borderLeft: rule ? `6px solid ${t.accent}` : "none", boxShadow: rule ? "0 14px 40px rgba(0,0,0,0.45)" : "0 8px 24px rgba(0,0,0,0.3)" }}>
        {!rule && <Brackets color={t.accent} />}
        {title}
        {el.subtitle && <div style={{ fontFamily: t.ui, fontWeight: 700, fontSize: 24, letterSpacing: "0.16em", textTransform: "uppercase",
          color: rule ? t.ink : t.accent, opacity: rule ? 0.75 : 1, marginTop: 6 }}><T plan={plan}>{el.subtitle}</T></div>}
      </div>
    </div>
  );
};

// ---------- keyword: a sticker (overlay) or a headline scene (canvas) ----------
const Keyword = ({ el, t, plan, surface }) => {
  const { s, o, visible, frame, fps } = useWindow(el.start, el.end);
  if (!visible) return null;
  if (surface === "canvas") {
    const drift = Math.sin((frame - sec(el.start, fps)) / 9) * 10;
    const ghost = el.ghost ? interpolate(frame, [sec(el.start, fps) + 10, sec(el.start, fps) + 30], [0, 0.35], clamp) : 0;
    const head = (style) => (
      <div style={{ fontFamily: headFont(t, hasRtl(el.title)), fontWeight: t.headlineWeight, fontSize: el.size || 140, lineHeight: 0.98, color: t.ink, ...style }}>
        <T plan={plan}>{el.title}</T></div>
    );
    return (
      <AbsoluteFill style={{ opacity: o }}>
        <div style={{ position: "absolute", top: 330, left: 90, right: 1080 - SAFE.right, transform: `translateY(${(1 - s) * 60}px)` }}>
          {el.kicker && <Kicker t={t}>{el.kicker}</Kicker>}
          <div style={{ position: "relative", marginTop: 24 }}>
            {ghost > 0 && head({ position: "absolute", top: 0, left: drift, color: t.accent, opacity: ghost })}
            {ghost > 0 && head({ position: "absolute", top: 0, left: -drift * 0.7, color: t.accent2, opacity: ghost * 0.8 })}
            {head({ position: "relative" })}
          </div>
          {el.subtitle && <div style={{ marginTop: 36, fontFamily: t.headline, fontStyle: "italic", fontWeight: 500, fontSize: 44, color: t.ink, opacity: 0.8 }}>
            <T plan={plan}>{el.subtitle}</T></div>}
        </div>
      </AbsoluteFill>
    );
  }
  const accent = el.tone !== "light";
  const kind = t.look?.sticker || "tilt";
  if (kind !== "tilt") return <KeywordLevel el={el} t={t} plan={plan} o={o} accent={accent} kind={kind} />;
  return (
    <div style={{ position: "absolute", top: el.top ?? 300, left: 72, opacity: o,
      transform: `scale(${0.6 + 0.4 * s}) rotate(${el.rotate ?? -3}deg)`, transformOrigin: "left center" }}>
      <div style={{ background: accent ? t.accent : t.paper, color: accent ? t.paper : t.ink, borderRadius: 14, padding: "16px 26px",
        boxShadow: "0 10px 30px rgba(0,0,0,0.25)", maxWidth: 820 }}>
        <div style={{ fontFamily: accent ? t.ui : headFont(t, hasRtl(el.title)), fontWeight: 800, fontSize: el.size || (accent ? 40 : 56),
          letterSpacing: accent ? "0.1em" : 0, textTransform: accent ? "uppercase" : "none" }}><T plan={plan}>{el.title}</T></div>
        {el.subtitle && <div style={{ fontFamily: accent ? t.headline : t.ui, fontStyle: accent ? "italic" : "normal", fontWeight: accent ? 500 : 700,
          fontSize: accent ? 34 : 26, letterSpacing: accent ? 0 : "0.12em", color: accent ? t.paper : t.accent2, marginTop: 4 }}>
          <T plan={plan}>{el.subtitle}</T></div>}
      </div>
    </div>
  );
};

// ---------- compare: A/B options that appear as said, then a reveal ----------
const Compare = ({ el, t, plan, surface }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const { o, visible } = useWindow(el.start, el.end);
  if (!visible) return null;
  const big = surface === "canvas";
  const rev = el.reveal ? sec(el.reveal.at, fps) : Infinity;
  const revealed = frame >= rev;
  // a compare without a reveal (the answer comes later, e.g. back on the speaker) never animates the reveal
  const strike = el.reveal ? interpolate(frame, [rev, rev + 10], [0, 1], { ...clamp, easing: EASE.move }) : 0;
  const ans = el.reveal ? spring({ frame: frame - rev, fps, config: { damping: 12, stiffness: 200 } }) : 0;
  const tagFor = (i) => {
    if (revealed && el.reveal) return i === el.reveal.correct ? el.reveal.correctTag : el.reveal.wrongTag;
    const m = (el.marks || []).filter((mk) => mk.option === i && frame >= sec(mk.at, fps)).pop();
    return m?.text;
  };
  return (
    <div style={{ position: "absolute", top: big ? 420 : (el.top ?? 300), left: 72, right: 1080 - SAFE.right, opacity: o }}>
      {big && <div style={{ marginBottom: 26 }}><Kicker t={t}>{revealed ? el.reveal?.kicker || "" : el.kicker || ""}</Kicker></div>}
      {el.options.map((opt, i) => {
        const s = spring({ frame: frame - sec(opt.at ?? el.start, fps), fps, config: { damping: 15, stiffness: 170 } });
        if (frame < sec(opt.at ?? el.start, fps) - 1) return null;
        const right = revealed && el.reveal && i === el.reveal.correct;
        const wrong = revealed && el.reveal && i !== el.reveal.correct;
        const tag = tagFor(i);
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 22, padding: big ? "28px 32px" : "18px 26px", borderRadius: 20,
            background: right ? t.accent2 : big ? "rgba(255,255,255,0.9)" : t.paper, marginBottom: big ? 24 : 16,
            opacity: Math.min(1, s * 1.5) * (wrong ? 1 - 0.38 * strike : 1),
            transform: `translateX(${(1 - s) * -80}px) scale(${right ? 1 + 0.05 * ans : 1})`, transformOrigin: "left center",
            boxShadow: "0 10px 30px rgba(0,0,0,0.18)" }}>
            <div style={{ width: big ? 72 : 56, height: big ? 72 : 56, borderRadius: 40, flexShrink: 0, background: right ? t.paper : t.ink,
              color: right ? t.accent2 : t.paper, fontFamily: t.ui, fontWeight: 800, fontSize: big ? 36 : 28,
              display: "flex", alignItems: "center", justifyContent: "center" }}>
              {right ? "✓" : wrong && strike > 0.5 ? "✕" : String.fromCharCode(65 + i)}</div>
            <div style={{ position: "relative", fontFamily: headFont(t, hasRtl(opt.text)), fontWeight: t.headlineWeight, fontStyle: "italic",
              fontSize: big ? 72 : 58, color: right ? t.paper : t.ink }}>
              <T plan={plan}>{opt.text}</T>
              {wrong && <div style={{ position: "absolute", left: -4, top: "54%", height: 7, width: `${strike * 104}%`, background: t.accent, borderRadius: 4 }} />}
            </div>
            {tag && <div style={{ marginLeft: "auto", fontFamily: t.ui, fontWeight: 700, fontSize: big ? 26 : 22, letterSpacing: "0.08em", whiteSpace: "nowrap",
              textTransform: "uppercase", color: right ? t.paper : t.accent }}>{tag}</div>}
          </div>
        );
      })}
      {el.note && frame >= sec(el.note.at, fps) && (() => {
        const ns = spring({ frame: frame - sec(el.note.at, fps), fps, config: { damping: 9, stiffness: 140 } });
        return (
          <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: big ? 20 : 6, transform: `scale(${ns})`, transformOrigin: "left center" }}>
            {el.note.icon && <Icon name={el.note.icon} t={t} size={big ? 110 : 80} p={ns} start={el.note.at} fps={fps} />}
            <div style={{ fontFamily: headFont(t, hasRtl(el.note.text)), fontStyle: "italic", fontWeight: t.headlineWeight, fontSize: big ? 66 : 46,
              color: big ? t.accent : "#fff", textShadow: big ? "none" : "0 3px 12px rgba(0,0,0,0.6)" }}><T plan={plan}>{el.note.text}</T></div>
          </div>
        );
      })()}
    </div>
  );
};

// A / C overlay icon: the icon sits in a framed tile joined to its label, like a title card (A) or a UI chip (C),
// instead of a big free-floating icon with a shadowed label (B).
const IconLevel = ({ el, t, plan, o, fps }) => {
  const { p, style } = useEnter(t, el.start);
  const rule = t.look?.sticker === "rule";
  return (
    <div style={{ position: "absolute", top: el.top ?? 300, left: 72, opacity: o, ...style }}>
      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 22, padding: "12px 26px 12px 12px",
        background: `${t.paper}E0`, borderRadius: rule ? 3 : 0, borderLeft: rule ? `6px solid ${t.accent}` : "none",
        boxShadow: "0 14px 40px rgba(0,0,0,0.45)" }}>
        {!rule && <Brackets color={t.accent} />}
        <div style={{ width: 132, height: 132, flexShrink: 0, borderRadius: rule ? 2 : 0, border: `2px solid ${t.accent}66`,
          display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Icon name={el.icon} t={t} size={112} p={p} start={el.start} fps={fps} />
        </div>
        {el.label && <div style={{ fontFamily: headFont(t, hasRtl(el.label)), fontWeight: t.headlineWeight, fontSize: 50, lineHeight: 1.04,
          color: t.ink, maxWidth: 520 }}><T plan={plan}>{el.label}</T></div>}
      </div>
    </div>
  );
};

// ---------- icon scene (canvas) / icon badge (overlay) ----------
const IconEl = ({ el, t, plan, surface }) => {
  const { s, o, visible, fps } = useWindow(el.start, el.end);
  if (!visible) return null;
  const big = surface === "canvas";
  if (!big && (t.look?.sticker || "tilt") !== "tilt") return <IconLevel el={el} t={t} plan={plan} o={o} fps={fps} />;
  return (
    <AbsoluteFill style={{ opacity: o }}>
      {big && el.kicker && <div style={{ position: "absolute", top: 330, left: 90 }}><Kicker t={t}>{el.kicker}</Kicker></div>}
      <div style={{ position: "absolute", top: big ? 400 : (el.top ?? 300), left: big ? 90 : 72, display: "flex", alignItems: "center", gap: 40,
        transform: `scale(${0.85 + 0.15 * s})`, transformOrigin: "left top" }}>
        <Icon name={el.icon} t={t} size={big ? 420 : 200} p={s} start={el.start} fps={fps} />
        {el.label && <div style={{ fontFamily: headFont(t, hasRtl(el.label)), fontWeight: t.headlineWeight, fontSize: big ? 84 : 52,
          lineHeight: 1.02, color: big ? t.ink : "#fff", maxWidth: big ? 300 : 520,
          textShadow: big ? "none" : "0 3px 12px rgba(0,0,0,0.6)" }}><T plan={plan}>{el.label}</T></div>}
      </div>
      {big && el.caption && <div style={{ position: "absolute", top: 960, left: 90, right: 1080 - SAFE.right, fontFamily: t.ui, fontWeight: 700,
        fontSize: 30, letterSpacing: "0.12em", color: t.accent2, textTransform: "uppercase" }}>{el.caption}</div>}
    </AbsoluteFill>
  );
};

// ---------- image scene: one of the creator's own photos with a slow push-in ----------
const ImageEl = ({ el, t, surface }) => {
  const { s, o, visible, frame, fps } = useWindow(el.start, el.end);
  if (!visible) return null;
  if (el.full) {
    // full-bleed still (e.g. an AI-generated scene in a cutaway) that moves like footage: `move` push (default) | pull |
    // rise | drift. A dark gradient top and bottom keeps the header and captions readable over any picture.
    const p = interpolate(frame, [sec(el.start, fps), sec(el.end, fps)], [0, 1], clamp);
    // `diagram: true` (a pre-rendered diagram, e.g. animate_slide.py): no push, no dark gradient, theme colours kept
    const mv = el.diagram ? [1, 1, 0, 0] : { push: [1.0, 1.14, 0, 0], pull: [1.14, 1.0, 0, 0], rise: [1.1, 1.1, 3, -3], drift: [1.1, 1.1, -3, 3] }[el.move || "push"];
    const k = mv[0] + (mv[1] - mv[0]) * p, ty = mv[2] + (mv[3] - mv[2]) * p;
    return (
      <AbsoluteFill style={{ opacity: Math.min(1, o * 1.4), overflow: "hidden" }}>
        {/\.(mp4|webm|mov)$/i.test(el.src) ? (
          // a living photo (short loop made from a still): plays from the element's start, muted
          <Sequence from={sec(el.start, fps)} layout="none">
            <OffthreadVideo src={staticFile(el.src)} muted style={{ width: "100%", height: "100%", objectFit: "cover",
              transform: `scale(${k}) translateY(${ty}%)`, transformOrigin: el.focus || "50% 50%" }} />
          </Sequence>
        ) : (
          <Img src={staticFile(el.src)} style={{ width: "100%", height: "100%", objectFit: "cover",
            transform: `scale(${k}) translateY(${ty}%)`, transformOrigin: el.focus || "50% 50%" }} />
        )}
        {!el.diagram && <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.65) 78%, rgba(0,0,0,0.75) 100%)" }} />}
        {/* `dim` (0..1): darken the whole picture when a list or text sits on a bright part of it */}
        {el.dim ? <AbsoluteFill style={{ background: `rgba(20,14,10,${el.dim})` }} /> : null}
      </AbsoluteFill>
    );
  }
  const k = interpolate(frame, [sec(el.start, fps), sec(el.end, fps)], [1.0, 1.08], clamp);
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", top: 330, left: 90, right: 1080 - SAFE.right, height: 680, borderRadius: 28, overflow: "hidden",
        transform: `translateY(${(1 - s) * 50}px)`, boxShadow: "0 18px 50px rgba(0,0,0,0.25)" }}>
        <Img src={staticFile(el.src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${k})` }} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- end card ----------
const EndCard = ({ el, t, plan, surface }) => {
  const { s, o, visible, frame, fps } = useWindow(el.start, el.end, 1);
  if (!visible) return null;
  const big = surface === "canvas";
  const bob = Math.sin((frame - sec(el.start, fps)) / 7) * 6;
  return (
    <div style={{ position: "absolute", top: big ? 400 : (el.top ?? 300), left: 72, right: 1080 - SAFE.right, opacity: o, transform: `translateY(${(1 - s) * 50}px)` }}>
      <div style={{ display: "inline-block", ...(big ? {} : { background: t.paper, borderRadius: 18, padding: "24px 32px", boxShadow: "0 10px 30px rgba(0,0,0,0.22)" }) }}>
        {el.kicker && <Kicker t={t}>{el.kicker}</Kicker>}
        <div style={{ marginTop: 10, fontFamily: headFont(t, hasRtl(el.text)), fontWeight: t.headlineWeight, fontSize: big ? 124 : 66, lineHeight: 1.03, color: t.ink }}>
          <T plan={plan}>{el.text}</T>
          {!el.cta && <span style={{ display: "inline-block", marginLeft: 16, transform: `translateY(${bob}px)`, color: t.accent }}>{"↓"}</span>}
        </div>
        {el.cta && <div style={{ marginTop: 30, fontFamily: t.ui, fontWeight: 700, fontSize: big ? 40 : 30, color: t.accent }}>
          <T plan={plan}>{el.cta}</T> <span style={{ display: "inline-block", transform: `translateY(${bob}px)` }}>{"↓"}</span></div>}
      </div>
    </div>
  );
};

// ---------- list: items appear as they're said ----------
const List = ({ el, t, plan, surface }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const { o, visible } = useWindow(el.start, el.end);
  if (!visible) return null;
  const big = surface === "canvas";
  const fs = el.size || (big ? 70 : 48), ic = Math.round(fs * (big ? 1.15 : 1.25)), gapY = el.size ? Math.round(fs * 0.22) : 18;
  return (
    <div style={{ position: "absolute", top: big ? (el.top ?? 360) : (el.top ?? 300), left: 72, right: 1080 - SAFE.right, opacity: o }}>
      {el.kicker && <div style={{ marginBottom: 22 }}><Kicker t={t} color={big ? t.accent : "#fff"}>{el.kicker}</Kicker></div>}
      {el.items.map((it, i) => {
        const s = spring({ frame: frame - sec(it.at, fps), fps, config: { damping: 15, stiffness: 180 } });
        if (frame < sec(it.at, fps) - 1) return null;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: gapY, opacity: Math.min(1, s * 1.5),
            transform: `translateX(${(1 - s) * -60}px)`, background: big ? "transparent" : t.paper, padding: big ? 0 : "12px 22px",
            borderRadius: (t.look?.sticker || "tilt") === "tilt" ? 14 : 3,
            borderLeft: !big && t.look?.sticker === "rule" ? `6px solid ${t.accent}` : undefined }}>
            {it.icon ? (
              // optional drawn icon per item (e.g. the things on a desk); falls back to the dot
              <div style={{ width: ic, height: ic, flexShrink: 0, padding: 6, borderRadius: 14, background: t.paper }}>
                <Icon name={it.icon} t={t} size={ic - 12} p={Math.min(1, s)} start={it.at} fps={fps} />
              </div>
            ) : t.look?.sticker === "rule" ? <div style={{ width: 34, height: 4, background: t.accent, flexShrink: 0, alignSelf: "flex-start", marginTop: fs * 0.62 }} />
              : t.look?.sticker === "bracket" ? <div style={{ width: 18, height: 18, background: t.accent, flexShrink: 0, alignSelf: "flex-start", marginTop: fs * 0.5 }} />
              : <div style={{ width: 22, height: 22, borderRadius: 11, background: t.accent, flexShrink: 0 }} />}
            <div style={{ fontFamily: headFont(t, hasRtl(it.text)), fontWeight: t.headlineWeight, fontSize: fs, color: t.ink }}><T plan={plan}>{it.text}</T></div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- waveform driven by the real audio (voice mode) ----------
export const Waveform = ({ t, src }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const audio = useAudioData(staticFile(src));
  if (!audio) return null;
  const vals = visualizeAudio({ fps, frame, audioData: audio, numberOfSamples: 64, smoothing: true }).slice(2, 34);
  return (
    // below the caption's translation line (y ~1255-1300) and above the soundtrack bar (y ~1394)
    <div style={{ position: "absolute", top: 1306, left: 90, right: 1080 - SAFE.right, height: 76, display: "flex", alignItems: "center", gap: 9 }}>
      {vals.map((v, i) => (
        <div key={i} style={{ flex: 1, height: 6 + 70 * Math.min(1, Math.sqrt(v * 14)), borderRadius: 6,
          background: i % 2 ? t.accent : t.ink, opacity: 0.85 }} />
      ))}
    </div>
  );
};

// ---------- sound effect at a moment (local, licence-clean files only) ----------
const Sfx = ({ el, t }) => {
  const { fps } = useVideoConfig();
  const fx = t?.look?.sfx || { swap: {}, gain: 1 };   // series sound: A swaps the playful pop for a soft tick, quieter
  const sound = el.keep ? el.sound : (fx.swap?.[el.sound] || el.sound);
  return (
    <Sequence from={sec(el.at, fps)} durationInFrames={sec(2, fps)}>
      <Audio src={staticFile(`sfx/${sound}.wav`)} volume={(el.volume ?? 0.5) * (fx.gain ?? 1)} />
    </Sequence>
  );
};

// ---------- media: another video shown in a panel (e.g. "here's what the skill made") ----------
// Appears at `start` (paused on a frame), plays muted from `playAt`, gone at `end`.
// Slots inside the safe area. "row4-1..4" = up to four small panels spread in one row above the presenter's head.
const SLOTS = { tl: [60, 300], tr: [680, 300], ml: [60, 720], mr: [680, 720] };
const slotXY = (slot, w) => {
  if (Array.isArray(slot)) return slot;
  const m = /^row(\d)-(\d)$/.exec(slot || "");
  if (m) { const n = +m[1], k = +m[2]; return [SAFE.left + (k - 1) * ((SAFE.right - SAFE.left - w) / Math.max(1, n - 1)), 292]; }
  return SLOTS[slot] || SLOTS.tl;
};
const Media = ({ el, t }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const { s, o, visible } = useWindow(el.start, el.end, 8, { damping: 13, stiffness: 190 });
  if (!visible) return null;
  const w = el.width || 220, h = Math.round(w * 16 / 9);
  const [x, y] = slotXY(el.slot, w);
  // `spawn: [x, y]` = where the speaker points (e.g. their hand). The panel pops out there and glides to its slot.
  const fly = el.spawn ? spring({ frame: frame - sec(el.start, fps), fps, config: { damping: 18, stiffness: 90 } }) : 1;
  const dx = el.spawn ? (el.spawn[0] - (x + w / 2)) * (1 - fly) : 0;
  const dy = el.spawn ? (el.spawn[1] - (y + h / 2)) * (1 - fly) : 0;
  const from = sec(el.from || 0, fps);
  const playAt = el.playAt != null ? sec(el.playAt, fps) : Infinity;
  const playing = frame >= playAt;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, opacity: o,
      transform: `translate(${dx}px, ${dy}px) scale(${(0.5 + 0.5 * s) * (el.spawn ? 0.35 + 0.65 * fly : 1)}) rotate(${(el.rotate ?? 0) * s}deg)`,
      transformOrigin: "center" }}>
      <div style={{ width: w, height: h, borderRadius: 18, overflow: "hidden", border: `5px solid ${t.paper}`,
        boxShadow: playing ? `0 0 0 3px ${t.accent}, 0 16px 40px rgba(0,0,0,0.45)` : "0 16px 40px rgba(0,0,0,0.45)", background: "#000" }}>
        {playing ? (
          <Sequence from={playAt} layout="none">
            <OffthreadVideo src={staticFile(el.src)} muted trimBefore={from} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </Sequence>
        ) : (
          <Freeze frame={from}>
            <OffthreadVideo src={staticFile(el.src)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </Freeze>
        )}
      </div>
      {el.label && <div style={{ position: "absolute", left: "50%", bottom: -22, transform: "translateX(-50%)", whiteSpace: "nowrap",
        background: playing ? t.accent : t.paper, color: playing ? t.paper : t.ink, borderRadius: 999, padding: w < 170 ? "6px 10px" : "8px 18px",
        fontFamily: t.ui, fontWeight: 800, fontSize: Math.min(22, Math.round(w * 0.12)), letterSpacing: w < 170 ? "0.06em" : "0.12em", boxShadow: "0 6px 16px rgba(0,0,0,0.3)" }}>{el.label}</div>}
    </div>
  );
};

// ---------- logo: an image (e.g. a venture's logo card) that pops out where the speaker points ----------
// `src` (png/svg in <job>/public), `width` (default 560), `ratio` (height/width, default 0.28), `slot` or [x, y],
// `spawn: [x, y]` (the pointing hand). Shown at its own proportions, no frame; a soft shadow lifts it off the video.
const Logo = ({ el }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const { s, o, visible } = useWindow(el.start, el.end, 8);
  if (!visible) return null;
  const w = el.width || 560, h = Math.round(w * (el.ratio || 0.28));
  const [x, y] = Array.isArray(el.slot) ? el.slot : [SAFE.left + (SAFE.right - SAFE.left - w) / 2, el.top ?? 320];
  const fly = el.spawn ? spring({ frame: frame - sec(el.start, fps), fps, config: { damping: 18, stiffness: 90 } }) : 1;
  const dx = el.spawn ? (el.spawn[0] - (x + w / 2)) * (1 - fly) : 0;
  const dy = el.spawn ? (el.spawn[1] - (y + h / 2)) * (1 - fly) : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, opacity: o * (el.opacity ?? 1),
      transform: `translate(${dx}px, ${dy}px) scale(${(0.6 + 0.4 * s) * (el.spawn ? 0.35 + 0.65 * fly : 1)})`, transformOrigin: "center",
      filter: el.shadow === false ? "none" : "drop-shadow(0 18px 36px rgba(0,0,0,0.45))" }}>
      <Img src={staticFile(el.src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
    </div>
  );
};

// ---------- flow: an explainer scene for cutaways / canvas modes ----------
// `kicker`, `rows: [{ from: {icon, text}, to: {icon, text}, at, at2 }]` - each row: the "from" card lands at `at`, an arrow
// draws itself across, the "to" card lands at `at2` (default at + 0.8). Up to 3 rows. Canvas surface only.
const FlowCard = ({ node, t, plan, s, accent }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 22, width: 620, minHeight: 116, boxSizing: "border-box", padding: "16px 26px", borderRadius: 24,
    background: accent ? t.accent : t.paper, border: accent ? "none" : `3px solid ${t.ink}`,
    boxShadow: "0 14px 34px rgba(0,0,0,0.18)", opacity: Math.min(1, s * 1.6), transform: `translateY(${(1 - s) * 40}px) scale(${0.9 + 0.1 * s})` }}>
    {node.icon && <div style={{ flexShrink: 0 }}><Icon name={node.icon} t={accent ? { ...t, ink: t.paper, accent: t.ink } : t} size={80} p={s} /></div>}
    <div style={{ fontFamily: headFont(t, hasRtl(node.text)), fontWeight: t.headlineWeight, fontSize: 52, lineHeight: 1.04,
      color: accent ? t.paper : t.ink }}><T plan={plan}>{node.text}</T></div>
  </div>
);
const Flow = ({ el, t, plan, surface }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const { o, visible } = useWindow(el.start, el.end);
  if (!visible || surface !== "canvas") return null;
  return (
    <div style={{ position: "absolute", top: 330, left: 72, right: 1080 - SAFE.right, opacity: o }}>
      {el.kicker && <div style={{ marginBottom: 30 }}><Kicker t={t}>{el.kicker}</Kicker></div>}
      {(el.rows || []).slice(0, 3).map((r, i) => {
        const a = sec(r.at, fps), b = sec(r.at2 ?? r.at + 0.8, fps);
        if (frame < a - 1) return null;
        const s1 = spring({ frame: frame - a, fps, config: { damping: 200, stiffness: 160, overshootClamping: true } });
        const arrow = interpolate(frame, [a + 6, b], [0, 1], { ...clamp, easing: EASE.move });
        const s2 = spring({ frame: frame - b, fps, config: { damping: 200, stiffness: 160, overshootClamping: true } });
        return (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginBottom: 26 }}>
            <FlowCard node={r.from} t={t} plan={plan} s={s1} />
            <svg width="140" height="54" viewBox="0 0 140 54" style={{ overflow: "visible", marginLeft: 70 }}>
              <path d="M30 4 C30 30 60 40 110 40" fill="none" stroke={t.accent} strokeWidth="9" strokeLinecap="round" pathLength={1}
                strokeDasharray="1 1" strokeDashoffset={1 - arrow} />
              <path d="M96 26 L114 40 L96 54" fill="none" stroke={t.accent} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round"
                opacity={arrow > 0.95 ? 1 : 0} />
            </svg>
            <div style={{ marginLeft: 200, marginTop: -30, minHeight: 116 }}>{frame >= b - 1 && <FlowCard node={r.to} t={t} plan={plan} s={s2} accent />}</div>
          </div>
        );
      })}
    </div>
  );
};

export const ELEMENTS = { diagram: Diagram, flow: Flow, title: Title, keyword: Keyword, compare: Compare, icon: IconEl, image: ImageEl, endcard: EndCard, list: List, sfx: Sfx, media: Media, logo: Logo };

export const RenderElements = ({ plan, t, surface }) =>
  (plan.elements || []).map((el, i) => {
    const C = ELEMENTS[el.type];
    return C ? <C key={i} el={el} t={t} plan={plan} surface={surface} /> : null;
  });
