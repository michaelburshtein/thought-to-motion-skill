import React from "react";
import { AbsoluteFill, Easing, interpolate, OffthreadVideo, random, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { KineticLine } from "./Captions";
import { getTheme } from "../lib/theme";
import { clamp, EASE, isRtl } from "../lib/util";
import { Header, PaperBackground, SAFE, SeriesLabel, Signature, Texture } from "./Brand";

// Brand intro (2 s) and outro (3 s): one skeleton, skinned by the mood (plan.theme).
// Built on the soundtrack bar: the line draws, the play triangle presses in, the wordmark lands
// with the series label and the brand catchphrase, then everything fades and the video's one-colour header takes over.
// The outro: the wordmark, "Follow @handle", the bar runs to the end and the play triangle turns
// into a pause, the catchphrase again, the website pill (plan.site or brand.site; none = no pill).
// Rendered as its own composition ("Bumper") and joined around the video by scripts/bumpers.py.

const LINE_Y = 980;
const fade = (f, a, b, from = 0, to = 1, ease = EASE.calmEnter) => interpolate(f, [a, b], [from, to], { ...clamp, easing: ease });

const PlayPause = ({ x, y, size, color, pause = 0, scale = 1, opacity = 1 }) => {
  // pause: 0 = play triangle, 1 = pause bars (the two halves of the triangle square off)
  const w = size * 0.9, h = size;
  const l = `M0 0 L${w * (0.5 - 0.12 * pause)} ${h * 0.25 * (1 - pause)} L${w * (0.5 - 0.12 * pause)} ${h - h * 0.25 * (1 - pause)} L0 ${h} Z`;
  const r = `M${w * (0.5 + 0.12 * pause)} ${h * 0.25 * (1 - pause)} L${w} ${h * 0.5 * (1 - pause)} L${w} ${h - h * 0.5 * (1 - pause)} L${w * (0.5 + 0.12 * pause)} ${h - h * 0.25 * (1 - pause)} Z`;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ position: "absolute", left: x, top: y - h / 2, opacity,
      transform: `scale(${scale})`, transformOrigin: "50% 50%" }}>
      <path d={l} fill={color} /><path d={r} fill={color} />
    </svg>
  );
};

const Bar = ({ t, from, progress, draw = 1, triColor, pause = 0, triScale = 1, triOpacity = 1, opacity = 1 }) => {
  const x0 = SAFE.left + 70, W = SAFE.right - x0;
  return (
    <div style={{ opacity }}>
      <PlayPause x={SAFE.left} y={LINE_Y} size={44} color={triColor} pause={pause} scale={triScale} opacity={triOpacity} />
      <div style={{ position: "absolute", left: x0, top: LINE_Y - 3, width: W * draw, height: 6, borderRadius: 3, background: `${t.ink}33` }} />
      <div style={{ position: "absolute", left: x0, top: LINE_Y - 3, width: W * Math.min(draw, progress), height: 6, borderRadius: 3, background: t.accent }} />
      {draw >= progress && <div style={{ position: "absolute", left: x0 + W * progress - 11, top: LINE_Y - 11, width: 22, height: 22, borderRadius: 11, background: t.accent }} />}
    </div>
  );
};

const Catchphrase = ({ t, brand, rtl, o, y, size = 68, mood }) => {
  const main = brand.catchphrase || "Your brand line";
  const second = brand.catchphrase2;
  // the font follows the text, not the video's language: the English catchphrase keeps the mood's headline font on Hebrew videos
  const hebrew = /[\u0590-\u05FF]/.test(main);
  const marker = (t.look?.emph || (mood === "light" ? "marker" : "solid")) === "marker";
  return (
    <div style={{ position: "absolute", left: SAFE.left, width: SAFE.right - SAFE.left, top: y, opacity: o, textAlign: "center",
      transform: `translateY(${(1 - o) * 24}px)` }}>
      <div dir={hebrew ? "rtl" : "ltr"} style={{ fontFamily: hebrew ? t.rtl : t.headline, fontWeight: hebrew ? 700 : t.headlineWeight, fontSize: size,
        lineHeight: 1.18, color: t.ink }}>
        <span style={marker ? { backgroundImage: `linear-gradient(transparent 52%, ${t.marker} 52%, ${t.marker} 94%, transparent 94%)` } : {}}>{main}</span>
      </div>
      {second && <div style={{ fontFamily: t.ui, fontWeight: 500, fontSize: Math.round(size * 0.5), marginTop: 18, color: t.ink, opacity: 0.75 }}>{second}</div>}
    </div>
  );
};

const Intro = ({ plan, t }) => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const brand = plan.brand || {}; const rtl = isRtl(plan.lang); const mood = t.name;
  const tri = mood === "bold" ? t.accent2 : t.accent;
  const slow = mood === "dark" ? 1.25 : mood === "bold" ? 0.8 : 1;   // A eases in slower, C snaps in faster
  const draw = fade(f, 0, 9 * slow, 0, 1, EASE.move);
  const triIn = fade(f, 8, 15);
  const triScale = interpolate(f, [8, 12, 16], [1.5, 0.86, 1], { ...clamp, easing: EASE.move });
  const progress = interpolate(f, [9, N], [0, 1], clamp);
  const word = fade(f, 10, 10 + 12 * slow);
  const label = fade(f, 16, 16 + 10 * slow);
  const phrase = fade(f, 20, 20 + 12 * slow);
  // exit: the last 12 frames - everything fades out and the wordmark settles back a little; the video's own
  // header (one colour, small) takes over from here
  const exit = fade(f, N - 12, N, 0, 1, EASE.move);
  return (
    <AbsoluteFill>
      <PaperBackground t={t} />
      <Texture t={t} />
      <Bar t={t} progress={progress} draw={draw} triColor={tri} triScale={triScale} triOpacity={triIn} opacity={1 - exit} />
      <div style={{ position: "absolute", inset: 0, transform: `scale(${1 - 0.06 * exit})`, transformOrigin: "540px 670px" }}>
        <WordmarkStrip t={t} text={(plan.brand || {}).wordmark || ""} top={560} o={word * (1 - exit)} />
      </div>
      {brand.series && <div style={{ position: "absolute", left: 0, width: 1080, top: 812, textAlign: "center", opacity: label * (1 - exit),
        fontFamily: t.headline, fontWeight: t.name === "bold" ? 700 : 500, fontSize: 52, color: t.accent }}><SeriesLabel text={brand.series} weight={t.name === "bold" ? 700 : 500} /></div>}
      <Catchphrase t={t} brand={brand} rtl={rtl} o={phrase * (1 - exit)} y={LINE_Y + 70} mood={mood} />
    </AbsoluteFill>
  );
};

// The wordmark on the intro and the end card: brand.wordmark, large, in the theme's ink on a band of the accent.
// Replace with your own identity treatment.
export const WordmarkStrip = ({ t, text, top, size = 112, padY = 52, o = 1 }) => (
  <div style={{ position: "absolute", left: 0, width: 1080, top, opacity: o, textAlign: "center", transform: `translateY(${(1 - o) * 24}px)` }}>
    <div style={{ display: "inline-block", fontFamily: t.ui, fontWeight: 800, fontSize: size, lineHeight: 1, letterSpacing: "0.12em",
      color: t.ink, padding: `${padY}px 0`, borderBottom: `6px solid ${t.accent}`, textTransform: "uppercase" }}>{text}</div>
  </div>
);

const Outro = ({ plan, t }) => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const brand = plan.brand || {}; const rtl = isRtl(plan.lang); const mood = t.name;
  const tri = mood === "bold" ? t.accent2 : t.accent;
  const progress = interpolate(f, [0, 54], [0.72, 1], { ...clamp, easing: EASE.move });
  const pause = fade(f, 54, 62, 0, 1, EASE.move);
  const l0 = fade(f, 0, 12), l1 = fade(f, 8, 20), l2 = fade(f, 16, 28), l3 = fade(f, 24, 36);
  const follow = plan.follow || (rtl ? "עקבו אחריי" : "Follow");
  const handle = brand.handle || "";
  const site = plan.site === undefined ? (brand.site || "") : plan.site;
  const platforms = plan.platforms || "LinkedIn · Instagram · TikTok · Threads · YouTube";
  return (
    <AbsoluteFill>
      <PaperBackground t={t} />
      <Texture t={t} />
      <WordmarkStrip t={t} text={(plan.brand || {}).wordmark || ""} top={brand.avatar ? 330 : 400} o={l0} />
      {brand.avatar && <div style={{ position: "absolute", left: 0, width: 1080, top: 570, display: "flex", justifyContent: "center", opacity: l1 }}>
        <Signature t={t} brand={{ ...brand, handle: " " }} size={92} />
      </div>}
      <div style={{ position: "absolute", left: 0, width: 1080, top: 700, textAlign: "center", opacity: l1,
        transform: `translateY(${(1 - l1) * 24}px)` }}>
        <div dir={rtl ? "rtl" : "ltr"} style={{ fontFamily: rtl ? t.rtl : t.ui, fontWeight: 700, fontSize: 50, color: t.ink }}>{follow}</div>
        <div style={{ fontFamily: t.ui, fontWeight: 800, fontSize: 66, color: t.accent, marginTop: 6, letterSpacing: "0.01em" }}>{handle}</div>
      </div>
      <Bar t={t} progress={progress} draw={1} triColor={tri} pause={pause} />
      <Catchphrase t={t} brand={brand} rtl={rtl} o={l2} y={LINE_Y + 70} size={60} mood={mood} />
      {site && <div style={{ position: "absolute", left: 0, width: 1080, top: 1215, textAlign: "center", opacity: l3,
        transform: `translateY(${(1 - l3) * 24}px)` }}>
        <span style={{ display: "inline-block", padding: "16px 40px 18px", borderRadius: 60, border: `3px solid ${t.accent}`,
          fontFamily: t.ui, fontWeight: 700, fontSize: 44, color: t.ink, letterSpacing: "0.01em" }}>{site}</span>
      </div>}
      <div style={{ position: "absolute", left: 0, width: 1080, top: 1350, textAlign: "center", opacity: l3 * 0.7,
        fontFamily: t.ui, fontWeight: 500, fontSize: 28, color: t.ink }}>{platforms}</div>
    </AbsoluteFill>
  );
};

// Opener: the video's catchphrase, the same template in every video. His own footage and line (cut from the video),
// a slow push-in, the line once in big kinetic type with the key word lit, nothing else on screen.
const Opener = ({ plan, t }) => {
  const f = useCurrentFrame(); const { fps, durationInFrames: N } = useVideoConfig();
  const o = plan.opener; const rtl = isRtl(plan.lang);
  const z = interpolate(f, [0, N], [1.0, 1.07], { ...clamp, easing: Easing.inOut(Easing.sin) });
  const cue = { text: o.text, emph: o.emph, words: o.words, start: 0, end: N / fps };
  const second = fade(f, 6, 16);
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ transform: `scale(${z})`, transformOrigin: `50% ${o.focusY || 38}%` }}>
        <OffthreadVideo src={staticFile(o.src)} startFrom={Math.round(o.from * fps)} muted
          style={{ width: "100%", height: "100%", objectFit: "cover", ...(t.look?.grade ? { filter: t.look.grade } : {}) }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 48%, rgba(0,0,0,0.62) 72%, rgba(0,0,0,0.7) 100%)" }} />
      <Texture t={t} />
      <div style={{ position: "absolute", left: SAFE.left, width: SAFE.right - SAFE.left, top: 1040 }}>
        <KineticLine t={t} plan={{ keywords: [] }} cue={cue} rtl={rtl} size={o.size || 86} />
        {o.text2 && <div style={{ marginTop: 22, textAlign: "center", fontFamily: t.ui, fontWeight: 600, fontSize: 40, color: "#fff",
          opacity: 0.85 * second }}>{o.text2}</div>}
      </div>
    </AbsoluteFill>
  );
};

// Insert: a card that pauses the talk to show one of the speaker's own clips with its own sound, joined into the video by scripts/insert.py. Dressed by the series: B = white photo frame (a print on paper),
// A = thin accent hairline, no frame (a screening), C = corner brackets (a screen capture).
// plan: { kind: "insert", src, duration, kicker, headline, quote, tag, brand, theme, lang }
const Insert = ({ plan, t }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const look = t.look || {}; const k = plan.clipBox || { x: 60, y: 600, w: 840, h: 472 };
  const a = fade(f, 0, 12), b = fade(f, 6, 20), c = fade(f, 14, 28);
  const frame = look.sticker === "rule" ? { outline: `2px solid ${t.accent}AA`, outlineOffset: 10, boxShadow: "0 30px 80px rgba(0,0,0,0.6)" }
    : look.sticker === "bracket" ? { boxShadow: "0 18px 50px rgba(0,0,0,0.5)" }
    : { border: "14px solid #FFFFFF", boxShadow: "0 18px 50px rgba(0,0,0,0.28)" };
  const quoteHe = /[\u0590-\u05FF]/.test(plan.quote || "");
  return (
    <AbsoluteFill>
      <PaperBackground t={t} />
      <Texture t={t} />
      <Header t={t} brand={plan.brand} surface="canvas" />
      {plan.kicker && <div style={{ position: "absolute", left: k.x, top: 430, opacity: a, fontFamily: t.ui, fontWeight: 700, fontSize: 34,
        letterSpacing: "0.16em", textTransform: "uppercase", color: t.accent }}>{plan.kicker}</div>}
      {plan.headline && <div style={{ position: "absolute", left: k.x, width: k.w, top: 492, opacity: a, fontFamily: t.headline,
        fontWeight: t.headlineWeight, fontSize: 52, lineHeight: 1.1, color: t.ink }}>{plan.headline}</div>}
      <div style={{ position: "absolute", left: k.x + (look.sticker === "tilt" || !look.sticker ? -14 : 0), top: k.y, width: k.w, height: k.h,
        opacity: b, transform: `translateY(${(1 - b) * 30}px)`, background: "#000", ...frame }}>
        {look.sticker === "bracket" && [["top", "left"], ["top", "right"], ["bottom", "left"], ["bottom", "right"]].map(([v, h]) => (
          <div key={v + h} style={{ position: "absolute", [v]: -12, [h]: -12, width: 30, height: 30, zIndex: 2,
            [`border${v[0].toUpperCase() + v.slice(1)}`]: `4px solid ${t.accent}`, [`border${h[0].toUpperCase() + h.slice(1)}`]: `4px solid ${t.accent}` }} />))}
        <OffthreadVideo src={staticFile(plan.src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
      {plan.quote && <div dir={quoteHe ? "rtl" : "ltr"} style={{ position: "absolute", left: k.x, width: k.w, top: k.y + k.h + 56, opacity: c,
        fontFamily: quoteHe ? t.rtl : t.headline, fontStyle: quoteHe ? "normal" : "italic", fontWeight: quoteHe ? 700 : t.headlineWeight,
        fontSize: 44, lineHeight: 1.2, color: t.ink }}>{plan.quote}</div>}
      {/* the AI disclosure must be legible on a phone: >= 14 px cap height at 540 wide */}
      {plan.tag && <div style={{ position: "absolute", left: k.x, top: 1250, opacity: c, fontFamily: t.ui, fontWeight: 800, fontSize: 40,
        letterSpacing: "0.1em", textTransform: "uppercase", color: t.ink, padding: "10px 22px", border: `3px solid ${t.ink}88`,
        borderRadius: look.sticker === "tilt" || !look.sticker ? 999 : 2 }}>{plan.tag}</div>}
    </AbsoluteFill>
  );
};

export const Bumper = ({ plan }) => {
  const t = getTheme(plan);
  if (plan.kind === "opener") return <Opener plan={plan} t={t} />;
  if (plan.kind === "insert") return <Insert plan={plan} t={t} />;
  return plan.kind === "outro" ? <Outro plan={plan} t={t} /> : <Intro plan={plan} t={t} />;
};
