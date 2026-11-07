import React from "react";
import { AbsoluteFill, Audio, Easing, Img, interpolate, OffthreadVideo, Solid, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { lightLeak } from "@remotion/effects/light-leak";
import { getTheme } from "./lib/theme";
import { clamp, MOTION, sec } from "./lib/util";
import { Badge, CaptionScrim, Guides, Header, PaperBackground, ProgressBar, SeriesLabel, Signature, Texture } from "./components/Brand";
import { KineticCaptions, OverlayCaptions } from "./components/Captions";
import { RenderElements, Waveform } from "./components/Elements";

export const isWide = (plan) => plan.aspect === "16:9";

// Punch-in zooms from the plan (type "punchin"). Done in Remotion, never with ffmpeg zoompan (shaky).
const usePunch = (plan) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  let z = 1;
  for (const p of (plan.elements || []).filter((e) => e.type === "punchin")) {
    const a = sec(p.start, fps), b = sec(p.end, fps), k = p.scale || 1.08;
    z *= interpolate(frame, [a - 6, a + 9, b - 12, b + 6], [1, k, k, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  }
  return z;
};

// Virtual cameras (plan.shots, from scripts/shots.py): each shot crops the same footage differently - a hard cut
// between "cameras", then a very slow push-in inside the shot. Returns the CSS transform for a 100%x100% layer.
export const shotAt = (plan, t) => (plan.shots || []).find((s) => t >= s.start && t < s.end) || null;
const useCamera = (plan) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const t = frame / fps; const s = shotAt(plan, t);
  if (!s || s.zoom <= 1.0001) return { transform: "none", zoomed: false };
  const p = Math.min(1, Math.max(0, (t - s.start) / Math.max(0.1, s.end - s.start)));
  const z = s.zoom * (1 + (s.drift || 0) * Easing.inOut(Easing.sin)(p));
  // keep the crop centred while it pushes in, and inside the frame
  const W = 1080, H = 1920, cx = s.x + W / (2 * s.zoom), cy = s.y + H / (2 * s.zoom);
  const x = Math.min(Math.max(cx - W / (2 * z), 0), W - W / z), y = Math.min(Math.max(cy - H / (2 * z), 0), H - H / z);
  return { transform: `scale(${z}) translate(${(-x / W) * 100}%, ${(-y / H) * 100}%)`, zoomed: true };
};

// A word behind the speaker's head: {"type": "behind", "text", "start", "end"} + "cutout"/"frames"/"x"/"y"
// written by scripts/behind.py. Drawn inside the camera layer, so it moves with the virtual cameras and punch-ins: the
// word sits on the footage and the cut-out of the person (MODNet matte) is drawn over it. Series accent, thin dark edge.
const pad5 = (n) => String(n).padStart(5, "0");
const BehindLayer = ({ plan, t, grade }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  return (plan.elements || []).filter((e) => e.type === "behind").map((e, i) => {
    const a = sec(e.start, fps), b = sec(e.end, fps);
    if (frame < a || frame > b) return null;
    const pin = interpolate(frame, [a, a + 12], [0, 1], { ...clamp, easing: Easing.bezier(0, 0, 0.3, 1) });
    const out = interpolate(frame, [b - 9, b], [1, 0], { ...clamp, easing: Easing.bezier(0.3, 0, 0.8, 0.15) });
    // fits inside the safe width (x 60-900, the app's buttons sit on the right) and under the header (y >= 300)
    const txt = e.text || ""; const size = e.size || Math.min(420, Math.round(840 / (0.72 * Math.max(1, txt.length))));
    const half = Math.min(420, 0.72 * size * txt.length / 2);
    const cx = Math.min(900 - half, Math.max(60 + half, e.x ?? 480)), cy = Math.max(300 + size * 0.62, e.y ?? 560);
    const has = e.cutout && e.frames && frame >= e.frames[0] && frame <= e.frames[1];
    return (
      <AbsoluteFill key={i}>
        <div style={{ position: "absolute", left: cx - 1000, width: 2000, top: cy - size * 0.62, textAlign: "center",
          fontFamily: t.headline, fontWeight: 800, fontSize: size, lineHeight: 1.0, letterSpacing: "-0.01em", whiteSpace: "nowrap",
          color: e.color || t.accent, WebkitTextStroke: `${Math.max(2, Math.round(size / 110))}px rgba(12,10,8,0.55)`, paintOrder: "stroke fill",
          textShadow: "0 6px 30px rgba(0,0,0,0.25)", opacity: pin * out, transform: `translateY(${(1 - pin) * 40}px) scale(${0.96 + 0.04 * pin})` }}>{txt}</div>
        {has && <Img src={staticFile(`${e.cutout}/${pad5(frame)}.webp`)} style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%",
          ...(grade ? { filter: grade } : {}) }} />}
      </AbsoluteFill>
    );
  });
};

// Optional light-leak flourish (WebGL; render with --gl=swangle on servers without a GPU).
const LightLeaks = ({ plan }) => {
  const frame = useCurrentFrame(); const { fps, width, height } = useVideoConfig();
  const leaks = (plan.elements || []).filter((e) => e.type === "lightleak");
  return leaks.map((l, i) => {
    const a = sec(l.at, fps), d = sec(l.duration || 1.2, fps);
    if (frame < a || frame > a + d) return null;
    return (
      <AbsoluteFill key={i} style={{ mixBlendMode: "screen", pointerEvents: "none", opacity: l.opacity ?? 0.35 }}>
        <Solid color="#000000" width={width} height={height}
          effects={[lightLeak({ seed: l.seed ?? i, hueShift: l.hueShift ?? 0, progress: interpolate(frame, [a, a + d], [0, 1], clamp) })]} />
      </AbsoluteFill>
    );
  });
};

// A 1080x1920 "stage": the vertical layout, placed somewhere inside a 16:9 frame. Elements keep their
// 9:16 coordinates inside it, so every element works in both formats.
const Stage = ({ x, y, scale = 1, children }) => (
  <div style={{ position: "absolute", left: x, top: y, width: 1080, height: 1920, transform: `scale(${scale})`, transformOrigin: "0 0" }}>{children}</div>
);
// Elements: the 9:16 content band (y 280..1420) is scaled to 0.75 and lands in the wide safe band (y 120..975),
// clear of the header (y 56..92) and the soundtrack bar (y ~996).
const EL = { scale: 0.75, y: 120 - 280 * 0.75 };
// Canvas (voice/text): scenes live in the upper band of the 9:16 frame (y 280..1000; captions sit below), so they
// are scaled up and vertically centred; captions + waveform sit centred on the right.
const CV = { scale: 0.9, y: 190 - 280 * 0.9 };

// Wide header + progress bar (16:9 safe area: 5% margins, YouTube/LinkedIn players draw controls at the bottom)
const WideBrand = ({ t, plan }) => {
  const frame = useCurrentFrame(); const { durationInFrames } = useVideoConfig();
  const p = frame / Math.max(1, durationInFrames - 1);
  return (
    <>
      {plan.brand?.wordmark && (
        <div style={{ position: "absolute", top: 50, left: 96, display: "flex", alignItems: "center", gap: 14 }}>
          <Badge t={t} text={plan.brand.wordmark} size={28} />
          {plan.brand.series && <span style={{ fontFamily: t.ui, fontWeight: 500, fontSize: 28, color: t.accent }}><SeriesLabel text={plan.brand.series} /></span>}
        </div>
      )}
      {/* the "soundtrack bar": play triangle, thin line, progress fill and dot */}
      <div style={{ position: "absolute", left: 96, right: 96, top: 1080 - 84, display: "flex", alignItems: "center", gap: 22 }}>
        <svg width="24" height="28" viewBox="0 0 30 34"><path d="M2 2 L28 17 L2 32 Z" fill={t.accent} /></svg>
        <div style={{ position: "relative", flex: 1, height: 4, background: "rgba(127,127,127,0.3)", borderRadius: 2 }}>
          <div style={{ position: "absolute", left: 0, top: 0, height: 4, width: `${p * 100}%`, background: t.accent, borderRadius: 2 }} />
          <div style={{ position: "absolute", left: `calc(${p * 100}% - 9px)`, top: -7, width: 18, height: 18, borderRadius: 9, background: t.accent }} />
        </div>
      </div>
    </>
  );
};

const SIG = { left: 60, top: 1322 };

// ---------- cutaways ----------
// {"type": "cutaway", "start", "end"}: for that window the picture cuts from the speaker to a full-screen animation (the
// canvas layout of voice mode: paper background, big scenes, kinetic captions) while his voice keeps playing - the
// footage stays mounted underneath, so its audio never stops. Elements whose start falls inside a cutaway are drawn on
// the canvas (big layouts); all others stay on the footage. In/out: a soft circular reveal (12 frames in, 10 out).
// over a full-screen picture the text must be light whatever the mood (light / cinematic ink is dark)
// (not over a `diagram: true` image: a diagram is drawn on the series paper, so the theme colours stay - otherwise the
// translation line takes the marker colour, nearly invisible on a dark paper)
const inkFor = (t, elements, time) => (elements || []).some((e) => e.type === "image" && e.full && !e.diagram && time >= e.start - 0.1 && time < e.end)
  ? { ...t, ink: "#FFF6EC", accent2: t.marker || "#FFFFFF" } : t;

const cutawayAt = (plan, time) => (plan.elements || []).find((e) => e.type === "cutaway" && time >= e.start - 0.5 && time < e.end + 0.5);
const inCutaway = (plan, el) => (plan.elements || []).some((c) => c.type === "cutaway" && el.type !== "cutaway"
  && (el.start ?? el.at ?? -1) >= c.start - 0.05 && (el.start ?? el.at ?? -1) < c.end);
const CutawayLayer = ({ plan, t }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const c = cutawayAt(plan, frame / fps);
  if (!c) return null;
  const a = sec(c.start, fps), b = sec(c.end, fps);
  // series transition (lib/theme.js SERIES_LOOK.cut): B circle reveal, A slow cross-dissolve with a push, C fast vertical wipe
  const cut = t.look?.cut || "circle";
  const inF = cut === "dissolve" ? 18 : cut === "wipe" ? 7 : 12, outF = cut === "dissolve" ? 16 : cut === "wipe" ? 7 : 10;
  const p = Math.min(interpolate(frame, [a, a + inF], [0, 1], { ...clamp, easing: Easing.bezier(0.2, 0, 0, 1) }),
    interpolate(frame, [b - outF, b], [1, 0], { ...clamp, easing: Easing.bezier(0.3, 0, 0.8, 0.15) }));
  if (p <= 0) return null;
  const wrap = cut === "dissolve" ? { opacity: p, transform: `scale(${1.04 - 0.04 * p})` }
    : cut === "wipe" ? { clipPath: `inset(${(1 - p) * 100}% 0 0 0)` } : { clipPath: `circle(${p * 120}% at 50% 45%)` };
  const canvasPlan = { ...plan, elements: (plan.elements || []).filter((e) => inCutaway(plan, e)) };
  const tc = inkFor(t, canvasPlan.elements, frame / fps);
  return (
    <AbsoluteFill style={wrap}>
      <PaperBackground t={t} />
      <RenderElements plan={canvasPlan} t={tc} surface="canvas" />
      <Texture t={t} />
      <Header t={tc} brand={plan.brand} surface="canvas" />
      <Signature t={tc} brand={plan.brand} size={52} style={{ position: "absolute", left: SIG.left, top: SIG.top }} />
      {plan.showCaptions !== false && <KineticCaptions t={tc} plan={plan} />}
      <ProgressBar t={tc} surface="canvas" />
    </AbsoluteFill>
  );
};

const TalkingHead = ({ plan, t }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const cut = cutawayAt(plan, frame / fps);
  const fullCut = !!cut && frame / fps >= cut.start + 0.3 && frame / fps < cut.end - 0.25;  // overlay captions hand over to the canvas ones
  const z = usePunch(plan);
  const cam = useCamera(plan);
  if (isWide(plan)) {
    // 16:9: the speaker in a tall frame on the right, the motion design on a branded stage to the left
    const ph = 900, pw = Math.round(ph * 9 / 16);
    return (
      <AbsoluteFill>
        <PaperBackground t={t} />
        <div style={{ position: "absolute", left: 1920 - 96 - pw, top: 60, width: pw, height: ph, borderRadius: 28, overflow: "hidden",
          boxShadow: "0 24px 60px rgba(0,0,0,0.35)" }}>
          <div style={{ width: "100%", height: "100%", transform: `scale(${cam.zoomed ? 1 : z})`, transformOrigin: "50% 35%" }}>
            <div style={{ width: "100%", height: "100%", transform: cam.transform, transformOrigin: "0 0" }}>
              <OffthreadVideo src={staticFile(plan.source)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              <div style={{ position: "absolute", left: 0, top: 0, width: 1080, height: 1920, transform: `scale(${pw / 1080})`, transformOrigin: "0 0" }}><BehindLayer plan={plan} t={t} /></div>
            </div>
          </div>
        </div>
        <LightLeaks plan={plan} />
        <Stage x={96} y={EL.y} scale={EL.scale}><RenderElements plan={plan} t={t} surface="canvas" /></Stage>
        {/* captions at full size, lower left (y ~720..960), the translation line above the soundtrack bar */}
        <Stage x={60} y={-330}>{plan.showCaptions !== false && <KineticCaptions t={t} plan={plan} />}</Stage>
        <WideBrand t={t} plan={plan} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${cam.zoomed ? 1 : z})`, transformOrigin: "50% 35%" }}>
        {/* punch-ins only on the wide camera; a zoomed camera is already the emphasis */}
        <AbsoluteFill style={{ transform: cam.transform, transformOrigin: "0 0" }}>
          <OffthreadVideo src={staticFile(plan.source)} style={t.look?.grade ? { filter: t.look.grade } : undefined} />
          <BehindLayer plan={plan} t={t} grade={t.look?.grade} />
        </AbsoluteFill>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.25) 0%, rgba(0,0,0,0) 18%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.45) 100%)" }} />
      <Texture t={t} />
      {plan.showCaptions !== false && !fullCut && <CaptionScrim t={t} />}
      <LightLeaks plan={plan} />
      <Header t={t} brand={plan.brand} surface="overlay" />
      <RenderElements plan={{ ...plan, elements: (plan.elements || []).filter((e) => !inCutaway(plan, e)) }} t={t} surface="overlay" />
      {plan.showCaptions !== false && !fullCut && <OverlayCaptions t={t} plan={plan} />}
      <ProgressBar t={t} surface="overlay" />
      <CutawayLayer plan={plan} t={t} />
      <Guides plan={plan} />
    </AbsoluteFill>
  );
};

// Voice mode (a recording, no footage) and text mode (plain text, no voice) share the canvas layout.
const CanvasVideo = ({ plan, t: t0 }) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const t = inkFor(t0, plan.elements, frame / fps);
  const hasAudio = plan.mode === "voice" && plan.source;
  const wave = hasAudio && plan.waveform !== false;
  if (isWide(plan)) {
    return (
      <AbsoluteFill>
        <PaperBackground t={t} />
        {hasAudio && <Audio src={staticFile(plan.source)} />}
        <LightLeaks plan={plan} />
        <Stage x={96} y={CV.y} scale={CV.scale}><RenderElements plan={plan} t={t} surface="canvas" /></Stage>
        <Stage x={960} y={-640}>
          {plan.showCaptions !== false && <KineticCaptions t={t} plan={plan} />}
          {wave && <Waveform t={t} src={plan.source} />}
        </Stage>
        <WideBrand t={t} plan={plan} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <PaperBackground t={t} />
      {hasAudio && <Audio src={staticFile(plan.source)} />}
      <LightLeaks plan={plan} />
      <Texture t={t} />
      <Header t={t} brand={plan.brand} surface="canvas" />
      <RenderElements plan={plan} t={t} surface="canvas" />
      {plan.showCaptions !== false && <KineticCaptions t={t} plan={plan} />}
      {wave && <Waveform t={t} src={plan.source} />}
      <ProgressBar t={t} surface="canvas" />
      <Guides plan={plan} />
    </AbsoluteFill>
  );
};

export const Main = ({ plan }) => {
  MOTION.calm = plan.motion === "calm";
  const t = getTheme(plan);
  return plan.mode === "talking-head" ? <TalkingHead plan={plan} t={t} /> : <CanvasVideo plan={plan} t={t} />;
};
