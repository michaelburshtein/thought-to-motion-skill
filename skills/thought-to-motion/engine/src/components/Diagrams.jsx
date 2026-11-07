import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE, bidiText, clamp, isRtl, sec, useWindow } from "../lib/util";
import { Icon } from "./Icons";

// ---------- diagrams ----------
// the creator's standing recommendation: when he talks about a list, steps, a process, a comparison or a change over time,
// show it as an animated diagram, not as text cards. One element, many patterns:
//   {"type": "diagram", "kind": "<pattern>", "start", "end", "kicker"?, ...pattern fields}
// Every timed part takes `at` (seconds) or `word` (a word he says; the first time it is said after the element's start,
// from the caption word times of scripts/word_times.py). Drawn on the canvas only (inside a cutaway in talking-head
// videos, or in voice/text videos), in the content band y 300-1000: the header sits above (~y 232) and the canvas
// captions below (y 1050, the translation line ~y 1255). Colours and fonts come from the series theme; the card shape
// follows SERIES_LOOK.sticker (A rule, B rounded, C brackets) and the entrance timing SERIES_LOOK.enterFrames.
//
// Patterns (fields):
//   balance     left {text, icon?, at?}, right {...}, tipAt|tipWord, tip "left"|"right" (the side that goes down)
//   link        from {text, icon?, at?}, to {...}, fillAt|fillWord, doneAt|doneWord, timer {from, to, suffix} | {text}, result {text, at|word}
//   steps       items [{text, at|word}], fan {items [text], at|word}? (the last step fans out into stacked cards)
//   table       columns [then, now], rows [{then, now, at|word}], nowAt|nowWord (the "now" column slides in)
//   device      at|word (the phone rises), items [{text, icon?, at|word}] (each drops into the screen)
//   beforeafter before {title?, text, at|word}, after {title?, text, at|word}
//   cycle       items [{text, at|word}] (3-5), closeAt|closeWord? (the loop closes)
//   funnel      items [{text, at|word}] (3-5 stages, widest first)
//   timeline    items [{when, text, at|word}]

export const BAND = { top: 300, bottom: 1000, left: 72, width: 828 };

const hasRtlChars = (s) => /[֐-׿؀-ۿ]/.test(s || "");
const Txt = ({ plan, children, style }) => {
  const rtl = isRtl(plan.lang) && hasRtlChars(children);
  return <span dir={rtl ? "rtl" : "ltr"} style={style}>{rtl ? bidiText(children) : children}</span>;
};
const head = (t, s) => (hasRtlChars(s) ? t.rtl : t.headline);
const lum = (hex) => {
  const h = (hex || "#000").replace("#", ""); const v = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
};

// time of a timed part: `at` seconds, or the first time `word` is said at/after `from` (caption word times)
export const wordTime = (plan, word, from = 0) => {
  if (!word) return null;
  const norm = (x) => (x || "").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
  const w = norm(word);
  for (const c of plan.captions || []) {
    for (const x of c.words || []) if (x.s >= from - 0.25 && norm(x.w).startsWith(w)) return x.s;
  }
  return null;
};
const timeOf = (plan, el, part, fallback) => {
  if (part == null) return fallback;
  if (typeof part === "number") return part;
  if (typeof part.at === "number") return part.at;
  return wordTime(plan, part.word, el.start) ?? fallback;
};
const T0 = (plan, el, k, fallback) => {
  const v = el[`${k}At`];
  if (typeof v === "number") return v;
  return wordTime(plan, el[`${k}Word`], el.start) ?? fallback;
};

// 0..1 entrance at time `a` (seconds), series length, decelerating (calm: no bounce)
const useIn = (t) => {
  const frame = useCurrentFrame(); const { fps } = useVideoConfig();
  const n = Math.max(8, t.look?.enterFrames || 12);
  return (a, frames = n) => interpolate(frame, [sec(a, fps), sec(a, fps) + frames], [0, 1], { ...clamp, easing: EASE.calmEnter });
};

// a card in the series shape
const Card = ({ t, accent, dim = 0, style, children }) => {
  const kind = t.look?.sticker || "tilt";
  const dark = lum(t.paper) < 0.4;
  const bg = accent ? t.accent : dark ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.75)";
  const shape = kind === "rule" ? { borderRadius: 3, borderLeft: `6px solid ${accent ? t.ink : t.accent}` }
    : kind === "bracket" ? { borderRadius: 0, border: `2px solid ${accent ? t.accent : t.accent + "55"}` }
    : { borderRadius: 20, border: accent ? "none" : `3px solid ${t.ink}` };
  return (
    <div style={{ position: "relative", boxSizing: "border-box", background: bg, ...shape, opacity: 1 - 0.5 * dim,
      boxShadow: dark ? "0 14px 34px rgba(0,0,0,0.45)" : "0 12px 30px rgba(0,0,0,0.14)", ...style }}>
      {kind === "bracket" && !accent && ["tl", "tr", "bl", "br"].map((c) => (
        <div key={c} style={{ position: "absolute", width: 16, height: 16, [c[0] === "t" ? "top" : "bottom"]: -5, [c[1] === "l" ? "left" : "right"]: -5,
          [c[0] === "t" ? "borderTop" : "borderBottom"]: `3px solid ${t.accent}`, [c[1] === "l" ? "borderLeft" : "borderRight"]: `3px solid ${t.accent}` }} />
      ))}
      {children}
    </div>
  );
};
const Label = ({ t, plan, text, size = 50, color, style }) => (
  <div style={{ fontFamily: head(t, text), fontWeight: t.headlineWeight, fontSize: size, lineHeight: 1.06, color: color || t.ink, ...style }}>
    <Txt plan={plan}>{text}</Txt></div>
);
const Kick = ({ t, children, o = 1 }) => children ? (
  <div style={{ fontFamily: t.ui, fontWeight: 800, fontSize: 30, letterSpacing: "0.16em", color: t.accent, textTransform: "uppercase", opacity: o }}>{children}</div>
) : null;

// ---------- A. balance: two pans that tip on the key word ----------
const Balance = ({ el, t, plan, frame, fps, inn }) => {
  const L = el.left || {}, R = el.right || {};
  const aL = timeOf(plan, el, L, el.start + 0.2), aR = timeOf(plan, el, R, aL + 0.6);
  const tipT = T0(plan, el, "tip", null);
  const dir = el.tip === "left" ? -1 : 1;                 // the side that goes down
  const tip = tipT == null ? 0 : interpolate(frame, [sec(tipT, fps), sec(tipT, fps) + 22], [0, 1], { ...clamp, easing: EASE.move });
  const idle = Math.sin(frame / 14) * 1.2 * (1 - tip);
  const ang = (dir * 13 * tip + idle) * Math.PI / 180;     // positive = right side down
  const cx = 414, cy = 150, half = 290, drop = 150;
  const end = (s) => [cx + s * half * Math.cos(ang), cy + s * half * Math.sin(ang)];
  const pan = (s, node, a) => {
    const [x, y] = end(s); const p = inn(a); const heavy = tip > 0.5 && ((s === 1) === (dir === 1));
    return (
      <g key={s} opacity={Math.min(1, p * 1.4)}>
        <line x1={x} y1={y} x2={x - 120} y2={y + drop} stroke={t.ink} strokeWidth="3" opacity="0.6" />
        <line x1={x} y1={y} x2={x + 120} y2={y + drop} stroke={t.ink} strokeWidth="3" opacity="0.6" />
        <path d={`M${x - 150} ${y + drop} Q${x} ${y + drop + 70} ${x + 150} ${y + drop}`} fill="none" stroke={heavy ? t.accent : t.ink} strokeWidth="7" strokeLinecap="round" />
        <foreignObject x={x - 170} y={y + drop + 36 - (1 - p) * 30} width="340" height="190">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, textAlign: "center" }}>
            {node.icon && <Icon name={node.icon} t={heavy ? t : { ...t, accent: t.ink }} size={76} p={p} />}
            <Label t={t} plan={plan} text={node.text} size={el.size || 50} color={heavy ? t.accent : t.ink} />
          </div>
        </foreignObject>
      </g>
    );
  };
  const s0 = inn(el.start);
  return (
    <svg width={BAND.width} height="640" viewBox={`0 0 ${BAND.width} 640`} style={{ overflow: "visible" }}>
      <g opacity={s0}>
        <path d={`M${cx} ${cy} L${cx - 70} 520 L${cx + 70} 520 Z`} fill={t.accent} opacity="0.18" />
        <line x1={cx} y1={cy} x2={cx} y2={520} stroke={t.ink} strokeWidth="8" strokeLinecap="round" />
        <line x1={cx - 120} y1={524} x2={cx + 120} y2={524} stroke={t.ink} strokeWidth="8" strokeLinecap="round" />
        <line x1={end(-1)[0]} y1={end(-1)[1]} x2={end(1)[0]} y2={end(1)[1]} stroke={t.ink} strokeWidth="10" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="16" fill={t.accent} />
      </g>
      {pan(-1, L, aL)}
      {pan(1, R, aR)}
    </svg>
  );
};

// ---------- B. link: two nodes, a line that fills while a timer counts, then a result tag ----------
const Link = ({ el, t, plan, frame, fps, inn }) => {
  const A = el.from || {}, B = el.to || {};
  const aA = timeOf(plan, el, A, el.start + 0.1), aB = timeOf(plan, el, B, aA + 0.5);
  const f0 = T0(plan, el, "fill", aB + 0.2), f1 = Math.max(f0 + 0.6, T0(plan, el, "done", f0 + 1.6));
  const fill = interpolate(frame, [sec(f0, fps), sec(f1, fps)], [0, 1], clamp);
  const res = el.result ? timeOf(plan, el, el.result, f1 + 0.1) : null;
  const tm = el.timer || {};
  const count = tm.text ? tm.text : `${Math.round((tm.from ?? 0) + ((tm.to ?? 60) - (tm.from ?? 0)) * fill)}${tm.suffix ?? " s"}`;
  const node = (n, a, y, lit) => {
    const p = inn(a);
    return (
      <div style={{ position: "absolute", left: 0, top: y, display: "flex", alignItems: "center", gap: 34, opacity: Math.min(1, p * 1.4),
        transform: `translateY(${(1 - p) * 30}px)` }}>
        <div style={{ width: 170, height: 170, borderRadius: 85, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
          background: lit ? t.accent : "transparent", border: `6px solid ${lit ? t.accent : t.ink}` }}>
          {n.icon && <Icon name={n.icon} t={lit ? { ...t, ink: t.paper, accent: t.paper } : t} size={96} p={p} />}
        </div>
        <Label t={t} plan={plan} text={n.text} size={el.size || 58} style={{ maxWidth: 560 }} />
      </div>
    );
  };
  const y0 = 40, y1 = 430, lx = 85;
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      <div style={{ position: "absolute", left: lx - 5, top: y0 + 170, width: 10, height: y1 - y0 - 170, background: `${t.ink}30`, borderRadius: 5 }} />
      <div style={{ position: "absolute", left: lx - 5, top: y0 + 170, width: 10, height: (y1 - y0 - 170) * fill, background: t.accent, borderRadius: 5 }} />
      {fill > 0 && <div style={{ position: "absolute", left: 230, top: y0 + 190, fontFamily: t.ui, fontWeight: 800, fontSize: 84,
        color: t.accent, fontVariantNumeric: "tabular-nums", opacity: Math.min(1, fill * 6) }}>{count}</div>}
      {node(A, aA, y0, false)}
      {node(B, aB, y1, fill >= 1)}
      {res != null && frame >= sec(res, fps) - 1 && (() => {
        const p = inn(res);
        return (
          <div style={{ position: "absolute", left: 204, top: y1 + 128, opacity: p, transform: `translateX(${(1 - p) * -24}px)` }}>
            <Card t={t} accent style={{ padding: "10px 24px" }}>
              <div style={{ fontFamily: t.ui, fontWeight: 800, fontSize: 34, letterSpacing: "0.08em", textTransform: "uppercase", color: t.paper }}>
                <Txt plan={plan}>{el.result.text}</Txt></div>
            </Card>
          </div>
        );
      })()}
    </div>
  );
};

// ---------- C. steps: each step lights up as it is said; the last one can fan out into stacked cards ----------
const Steps = ({ el, t, plan, frame, fps, inn }) => {
  const items = (el.items || []).slice(0, 5);
  const ats = []; items.forEach((it, i) => ats.push(timeOf(plan, el, it, (ats[i - 1] ?? el.start) + (i ? 0.8 : 0.1))));
  const fanAt = el.fan ? timeOf(plan, el, el.fan, ats[ats.length - 1] + 0.8) : null;
  const now = frame / fps;
  const cur = ats.reduce((k, a, i) => (now >= a ? i : k), -1);
  const H = items.length > 4 ? 104 : 116, G = items.length > 4 ? 22 : 30;
  const fan = fanAt != null ? interpolate(frame, [sec(fanAt, fps), sec(fanAt, fps) + 16], [0, 1], { ...clamp, easing: EASE.move }) : 0;
  const lineTo = cur < 0 ? 0 : cur * (H + G) + H / 2;
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      <div style={{ position: "absolute", left: 44, top: H / 2, width: 6, height: Math.max(0, (items.length - 1) * (H + G)), background: `${t.ink}22`, borderRadius: 3 }} />
      <div style={{ position: "absolute", left: 44, top: H / 2, width: 6, height: Math.max(0, lineTo - H / 2), background: t.accent, borderRadius: 3 }} />
      {items.map((it, i) => {
        if (frame < sec(ats[i], fps) - 1) return null;
        const p = inn(ats[i]); const lit = i === cur; const last = i === items.length - 1;
        const y = i * (H + G);
        const fanned = last && el.fan ? (el.fan.items || []).slice(0, 4) : [];
        return (
          <div key={i} style={{ position: "absolute", left: 0, top: y, width: BAND.width, opacity: Math.min(1, p * 1.5), transform: `translateX(${(1 - p) * -40}px)` }}>
            <div style={{ position: "absolute", left: 10, top: H / 2 - 37, width: 74, height: 74, borderRadius: 37, display: "flex", alignItems: "center", justifyContent: "center",
              background: i <= cur ? t.accent : t.paper, border: `5px solid ${i <= cur ? t.accent : t.ink + "66"}`, zIndex: 2,
              fontFamily: t.ui, fontWeight: 800, fontSize: 34, color: i <= cur ? t.paper : t.ink }}>{i + 1}</div>
            {fan > 0 && fanned.map((f, k) => (
              <div key={k} style={{ position: "absolute", left: 120 + fan * (40 + k * 40), top: fan * ((k + 1) * (H * 0.64)), width: 600 - k * 10,
                transform: `rotate(${fan * (k - 1) * 1.6}deg)`, opacity: Math.min(1, fan * 1.6), zIndex: -1 - k }}>
                <Card t={t} accent={k === fanned.length - 1 && fan >= 1} style={{ height: H * 0.78, padding: "0 26px", display: "flex", alignItems: "center" }}>
                  <Label t={t} plan={plan} text={f} size={40} color={k === fanned.length - 1 && fan >= 1 ? t.paper : t.ink} /></Card>
              </div>
            ))}
            <div style={{ position: "absolute", left: 120, top: 0, width: 690, zIndex: 1 }}>
              <Card t={t} accent={lit && !(last && fan > 0)} style={{ height: H, padding: "0 28px", display: "flex", alignItems: "center" }}>
                <Label t={t} plan={plan} text={it.text} size={el.size || 50} color={lit && !(last && fan > 0) ? t.paper : t.ink} />
              </Card>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- D. table: then vs now; rows appear as each item is named, then the "now" column slides in ----------
const Table = ({ el, t, plan, frame, fps, inn }) => {
  const rows = (el.rows || []).slice(0, 5);
  const ats = []; rows.forEach((r, i) => ats.push(timeOf(plan, el, r, (ats[i - 1] ?? el.start) + (i ? 0.7 : 0.15))));
  const nowAt = T0(plan, el, "now", ats[ats.length - 1] + 0.8);
  const nw = interpolate(frame, [sec(nowAt, fps), sec(nowAt, fps) + 18], [0, 1], { ...clamp, easing: EASE.move });
  const [c1, c2] = el.columns || ["Then", "Now"];
  const W = 400, RH = 118, top = 96;
  const colHead = (txt, x, accent, o) => (
    <div style={{ position: "absolute", left: x, top: 0, width: W, opacity: o, fontFamily: t.ui, fontWeight: 800, fontSize: 32, letterSpacing: "0.16em",
      textTransform: "uppercase", color: accent ? t.accent : t.ink }}><Txt plan={plan}>{txt}</Txt>
      <div style={{ marginTop: 14, height: 4, width: W - 24, background: accent ? t.accent : `${t.ink}55` }} /></div>
  );
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      {colHead(c1, 0, false, inn(el.start) * (1 - 0.4 * nw))}
      <div style={{ position: "absolute", left: 428, top: 0, width: W, height: 660, overflow: "hidden" }}>
        <div style={{ position: "absolute", left: (1 - nw) * 440, top: 0, width: W }}>
          {colHead(c2, 0, true, 1)}
          {rows.map((r, i) => {
            const p = inn(nowAt + 0.12 * i, 10);
            return frame >= sec(ats[i], fps) && (
              <div key={i} style={{ position: "absolute", left: 0, top: top + i * (RH + 14), width: W - 24, opacity: p }}>
                <Card t={t} accent style={{ height: RH, padding: "0 22px", display: "flex", alignItems: "center" }}>
                  <Label t={t} plan={plan} text={r.now} size={el.size || 48} color={t.paper} /></Card>
              </div>
            );
          })}
        </div>
      </div>
      {rows.map((r, i) => {
        if (frame < sec(ats[i], fps) - 1) return null;
        const p = inn(ats[i]);
        return (
          <div key={i} style={{ position: "absolute", left: 0, top: top + i * (RH + 14), width: W - 24, opacity: Math.min(1, p * 1.5) * (1 - 0.45 * nw),
            transform: `translateY(${(1 - p) * 24}px)` }}>
            <Card t={t} style={{ height: RH, padding: "0 22px", display: "flex", alignItems: "center" }}>
              <Label t={t} plan={plan} text={r.then} size={el.size || 48} /></Card>
          </div>
        );
      })}
    </div>
  );
};

// ---------- E. device: a phone rises and the items drop into its screen ----------
const Device = ({ el, t, plan, frame, fps, inn }) => {
  const rise = inn(timeOf(plan, el, el, el.start + 0.1), 20);
  const items = (el.items || []).slice(0, 5);
  const ats = []; items.forEach((it, i) => ats.push(timeOf(plan, el, it, (ats[i - 1] ?? el.start + 0.6) + (i ? 0.6 : 0))));
  const PW = 360, PH = 640, px = (BAND.width - PW) / 2, sx = 22, sy = 70, SW = PW - 2 * sx, RH = 92;
  const dark = lum(t.paper) < 0.4;
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      <div style={{ position: "absolute", left: px, top: 10 + (1 - rise) * 420, width: PW, height: PH, opacity: Math.min(1, rise * 1.5),
        borderRadius: 54, border: `8px solid ${t.ink}`, boxSizing: "border-box", background: dark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
        boxShadow: "0 30px 70px rgba(0,0,0,0.35)" }}>
        <div style={{ position: "absolute", left: "50%", top: 18, width: 96, height: 22, marginLeft: -48, borderRadius: 11, background: t.ink }} />
        {items.map((it, i) => {
          if (frame < sec(ats[i], fps) - 1) return null;
          const p = interpolate(frame, [sec(ats[i], fps), sec(ats[i], fps) + 14], [0, 1], { ...clamp, easing: EASE.calmEnter });
          const y = sy + i * (RH + 12);
          return (
            <div key={i} style={{ position: "absolute", left: sx - 8, top: y - (1 - p) * (y + 260), width: SW, opacity: Math.min(1, p * 2) }}>
              <Card t={t} accent={i === items.length - 1 && p >= 1} style={{ height: RH, padding: "0 14px", display: "flex", alignItems: "center", gap: 14 }}>
                {it.icon && <Icon name={it.icon} t={i === items.length - 1 && p >= 1 ? { ...t, ink: t.paper, accent: t.paper } : t} size={56} p={p} />}
                <Label t={t} plan={plan} text={it.text} size={el.size || 34} color={i === items.length - 1 && p >= 1 ? t.paper : t.ink} />
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ---------- before / after ----------
const BeforeAfter = ({ el, t, plan, frame, fps, inn }) => {
  const B = el.before || {}, A = el.after || {};
  const a0 = timeOf(plan, el, B, el.start + 0.1), a1 = timeOf(plan, el, A, a0 + 1.2);
  const pB = inn(a0), pA = inn(a1, 16);
  const arrow = interpolate(frame, [sec(a1, fps) - 8, sec(a1, fps) + 6], [0, 1], { ...clamp, easing: EASE.move });
  const box = (n, p, accent, y, tag, dim) => (
    <div style={{ position: "absolute", left: 0, top: y, width: BAND.width, opacity: Math.min(1, p * 1.5) * (1 - 0.4 * dim),
      clipPath: `inset(0 ${(1 - p) * 100}% 0 0)` }}>
      <div style={{ fontFamily: t.ui, fontWeight: 800, fontSize: 28, letterSpacing: "0.18em", textTransform: "uppercase", color: accent ? t.accent : `${t.ink}AA`, marginBottom: 12 }}>
        <Txt plan={plan}>{n.title || tag}</Txt></div>
      <Card t={t} accent={accent} style={{ minHeight: 170, padding: "22px 30px", display: "flex", alignItems: "center" }}>
        <Label t={t} plan={plan} text={n.text} size={el.size || 56} color={accent ? t.paper : t.ink} /></Card>
    </div>
  );
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      {box(B, pB, false, 0, "Before", pA)}
      <svg width="120" height="110" viewBox="0 0 120 110" style={{ position: "absolute", left: 354, top: 262, overflow: "visible" }}>
        <path d="M60 4 L60 92" stroke={t.accent} strokeWidth="10" strokeLinecap="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - arrow} fill="none" />
        <path d="M30 66 L60 98 L90 66" stroke={t.accent} strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity={arrow > 0.9 ? 1 : 0} />
      </svg>
      {frame >= sec(a1, fps) - 1 && box(A, pA, true, 390, "After", 0)}
    </div>
  );
};

// ---------- cycle: nodes around a loop, each arc draws itself as the next one is said ----------
const Cycle = ({ el, t, plan, frame, fps, inn }) => {
  const items = (el.items || []).slice(0, 5); const n = items.length || 1;
  const ats = []; items.forEach((it, i) => ats.push(timeOf(plan, el, it, (ats[i - 1] ?? el.start) + (i ? 0.8 : 0.1))));
  const closeAt = T0(plan, el, "close", ats[n - 1] + 0.7);
  const cx = 414, cy = 330, R = 250;
  const pos = (i) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [cx + R * Math.cos(a), cy + R * Math.sin(a)]; };
  const arc = (i, p) => {
    const a0 = -Math.PI / 2 + (2 * Math.PI * i) / n + 0.32, a1 = -Math.PI / 2 + (2 * Math.PI * (i + 1)) / n - 0.32;
    const [x0, y0] = [cx + R * Math.cos(a0), cy + R * Math.sin(a0)], [x1, y1] = [cx + R * Math.cos(a1), cy + R * Math.sin(a1)];
    const ah = a1 + 0.0, tx = -Math.sin(ah), ty = Math.cos(ah);  // tangent at the arc end
    return (
      <g key={`a${i}`}>
        <path d={`M${x0} ${y0} A${R} ${R} 0 0 1 ${x1} ${y1}`} fill="none" stroke={t.accent} strokeWidth="8" strokeLinecap="round" pathLength={1}
          strokeDasharray="1 1" strokeDashoffset={1 - p} />
        {p > 0.95 && <path d={`M${x1 - 22 * tx + 14 * ty} ${y1 - 22 * ty - 14 * tx} L${x1} ${y1} L${x1 - 22 * tx - 14 * ty} ${y1 - 22 * ty + 14 * tx}`}
          fill="none" stroke={t.accent} strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />}
      </g>
    );
  };
  const arcP = (i) => {
    const a = i < n - 1 ? ats[i + 1] - 0.35 : closeAt;
    return interpolate(frame, [sec(a, fps), sec(a, fps) + 14], [0, 1], { ...clamp, easing: EASE.move });
  };
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      <svg width={BAND.width} height="660" style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={`${t.ink}1E`} strokeWidth="4" />
        {items.map((_, i) => arc(i, arcP(i)))}
      </svg>
      {items.map((it, i) => {
        if (frame < sec(ats[i], fps) - 1) return null;
        const p = inn(ats[i]); const [x, y] = pos(i); const W = 300;
        return (
          <div key={i} style={{ position: "absolute", left: Math.min(BAND.width - W, Math.max(0, x - W / 2)), top: y - 52, width: W,
            opacity: Math.min(1, p * 1.5), transform: `scale(${0.85 + 0.15 * p})` }}>
            <Card t={t} accent={frame / fps >= ats[i] && (i === n - 1 ? frame / fps < closeAt : frame / fps < ats[i + 1])}
              style={{ minHeight: 104, padding: "10px 18px", display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
              <Label t={t} plan={plan} text={it.text} size={el.size || 40}
                color={frame / fps >= ats[i] && (i === n - 1 ? frame / fps < closeAt : frame / fps < ats[i + 1]) ? t.paper : t.ink} /></Card>
          </div>
        );
      })}
    </div>
  );
};

// ---------- funnel: stages narrowing down, each lands as it is said ----------
const Funnel = ({ el, t, plan, frame, fps, inn }) => {
  const items = (el.items || []).slice(0, 5); const n = items.length || 1;
  const ats = []; items.forEach((it, i) => ats.push(timeOf(plan, el, it, (ats[i - 1] ?? el.start) + (i ? 0.8 : 0.1))));
  const H = n > 4 ? 104 : 120, G = 14, W0 = 820, W1 = 380;
  const now = frame / fps; const cur = ats.reduce((k, a, i) => (now >= a ? i : k), -1);
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      {items.map((it, i) => {
        if (frame < sec(ats[i], fps) - 1) return null;
        const p = inn(ats[i]); const wTop = W0 - (W0 - W1) * (i / n), wBot = W0 - (W0 - W1) * ((i + 1) / n);
        const x0 = (BAND.width - wTop) / 2, x1 = (BAND.width - wBot) / 2; const y = i * (H + G); const lit = i === cur;
        return (
          <div key={i} style={{ position: "absolute", left: 0, top: y, width: BAND.width, height: H, opacity: Math.min(1, p * 1.5), transform: `translateY(${(1 - p) * -30}px)` }}>
            <svg width={BAND.width} height={H} style={{ position: "absolute", left: 0, top: 0 }}>
              <path d={`M${x0} 0 L${x0 + wTop} 0 L${x1 + wBot} ${H} L${x1} ${H} Z`} fill={lit ? t.accent : lum(t.paper) < 0.4 ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.8)"}
                stroke={lit ? t.accent : `${t.ink}66`} strokeWidth="3" />
            </svg>
            <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Label t={t} plan={plan} text={it.text} size={el.size || 46} color={lit ? t.paper : t.ink} /></div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- timeline: a line grows down, each point lights up as it is said ----------
const Timeline = ({ el, t, plan, frame, fps, inn }) => {
  const items = (el.items || []).slice(0, 5); const n = items.length || 1;
  const ats = []; items.forEach((it, i) => ats.push(timeOf(plan, el, it, (ats[i - 1] ?? el.start) + (i ? 0.8 : 0.1))));
  const step = Math.min(190, 560 / Math.max(1, n - 1)); const now = frame / fps; const cur = ats.reduce((k, a, i) => (now >= a ? i : k), -1);
  const grow = cur <= 0 ? 0 : (cur - 1) * step + step * interpolate(frame, [sec(ats[cur], fps) - 10, sec(ats[cur], fps) + 2], [0, 1], { ...clamp, easing: EASE.move });
  return (
    <div style={{ position: "relative", width: BAND.width, height: 660 }}>
      <div style={{ position: "absolute", left: 37, top: 30, width: 6, height: (n - 1) * step, background: `${t.ink}22`, borderRadius: 3 }} />
      <div style={{ position: "absolute", left: 37, top: 30, width: 6, height: grow, background: t.accent, borderRadius: 3 }} />
      {items.map((it, i) => {
        if (frame < sec(ats[i], fps) - 1) return null;
        const p = inn(ats[i]); const lit = i === cur;
        return (
          <div key={i} style={{ position: "absolute", left: 0, top: i * step, width: BAND.width, opacity: Math.min(1, p * 1.5) }}>
            <div style={{ position: "absolute", left: 40 - 22, top: 30 - 22, width: 44, height: 44, borderRadius: 22, background: lit ? t.accent : t.paper,
              border: `6px solid ${t.accent}`, boxSizing: "border-box", transform: `scale(${0.6 + 0.4 * p})` }} />
            <div style={{ position: "absolute", left: 96, top: 0, transform: `translateX(${(1 - p) * -24}px)` }}>
              {it.when && <div style={{ fontFamily: t.ui, fontWeight: 800, fontSize: 32, letterSpacing: "0.14em", textTransform: "uppercase", color: t.accent }}>
                <Txt plan={plan}>{it.when}</Txt></div>}
              <Label t={t} plan={plan} text={it.text} size={el.size || (lit ? 62 : 54)} color={t.ink} style={{ opacity: lit ? 1 : 0.75, maxWidth: 700 }} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

const KINDS = { balance: Balance, link: Link, steps: Steps, table: Table, device: Device, beforeafter: BeforeAfter, cycle: Cycle, funnel: Funnel, timeline: Timeline };
export const DIAGRAM_KINDS = Object.keys(KINDS);

export const Diagram = ({ el, t, plan, surface }) => {
  const { o, visible, frame, fps } = useWindow(el.start, el.end);
  const inn = useIn(t);
  if (!visible || surface !== "canvas") return null;
  const K = KINDS[el.kind];
  if (!K) return null;
  return (
    <div style={{ position: "absolute", top: BAND.top, left: BAND.left, width: BAND.width, height: BAND.bottom - BAND.top, opacity: o }}>
      {el.kicker && <div style={{ height: 70 }}><Kick t={t} o={inn(el.start)}>{el.kicker}</Kick></div>}
      <div style={{ position: "relative" }}><K el={el} t={t} plan={plan} frame={frame} fps={fps} inn={inn} /></div>
    </div>
  );
};
