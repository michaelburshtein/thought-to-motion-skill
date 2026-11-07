import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { clamp } from "../lib/util";

// Small set of generic, original icons drawn in code (no third-party artwork).
// Each returns SVG content in a 0..400 box. `p` = entrance progress 0..1, `f` = local frame.
const ICONS = {
  tv: (t, p, f) => (
    <g>
      <line x1="170" y1="70" x2="120" y2="20" stroke={t.ink} strokeWidth="8" strokeLinecap="round" />
      <line x1="230" y1="70" x2="285" y2="25" stroke={t.ink} strokeWidth="8" strokeLinecap="round" />
      <rect x="20" y="70" width="360" height="270" rx="36" fill={t.accent} />
      <rect x="48" y="98" width="250" height="214" rx="24" fill={t.ink} opacity={0.92} />
      <rect x="48" y="98" width="250" height="214" rx="24" fill={t.paper} opacity={0.12 * p * (0.8 + 0.2 * Math.sin(f * 1.7))} />
      <circle cx="338" cy="140" r="16" fill={t.paper} /><circle cx="338" cy="190" r="16" fill={t.paper} />
      <rect x="80" y="340" width="20" height="30" fill={t.ink} /><rect x="300" y="340" width="20" height="30" fill={t.ink} />
    </g>
  ),
  paws: (t, p, f) => (
    <g fill={t.accent}>
      {Array.from({ length: 6 }).map((_, i) => {
        const o = interpolate(f, [6 + i * 7, 12 + i * 7], [0, 0.9], clamp);
        const x = 40 + i * 64, y = 330 - i * 52 + (i % 2 ? -26 : 26);
        return (
          <g key={i} transform={`translate(${x},${y}) rotate(${-30 + (i % 2 ? 12 : -12)}) scale(0.8)`} opacity={o}>
            <ellipse cx="0" cy="18" rx="22" ry="18" />
            <ellipse cx="-24" cy="-8" rx="9" ry="12" /><ellipse cx="-8" cy="-22" rx="9" ry="12" />
            <ellipse cx="10" cy="-22" rx="9" ry="12" /><ellipse cx="26" cy="-8" rx="9" ry="12" />
          </g>
        );
      })}
    </g>
  ),
  burst: (t, p) => (
    <g transform={`translate(200,200) scale(${0.6 + 0.4 * p})`}>
      {Array.from({ length: 14 }).map((_, i) => (
        <line key={i} x1="0" y1="-70" x2="0" y2={-150 - (i % 2) * 30} stroke={i % 2 ? t.accent : t.accent2} strokeWidth="16"
          strokeLinecap="round" transform={`rotate(${i * (360 / 14)})`} />
      ))}
      <circle r="48" fill={t.accent} />
    </g>
  ),
  question: (t, p) => (
    <text x="200" y="320" textAnchor="middle" fontFamily={t.headline} fontWeight="700" fontSize="380" fill={t.accent}
      transform={`translate(200,200) scale(${p}) translate(-200,-200)`}>?</text>
  ),
  quote: (t, p) => (
    <text x="40" y="330" fontFamily={t.headline} fontWeight="700" fontSize="420" fill={t.accent} opacity={p}>{"“"}</text>
  ),
  lightbulb: (t, p, f) => (
    <g>
      {Array.from({ length: 7 }).map((_, i) => (
        <line key={i} x1="200" y1="40" x2="200" y2="10" stroke={t.accent} strokeWidth="12" strokeLinecap="round"
          transform={`rotate(${-90 + i * 30} 200 170)`} opacity={p * (0.6 + 0.4 * Math.sin(f / 5 + i))} />
      ))}
      <circle cx="200" cy="170" r="95" fill={t.accent} />
      <rect x="150" y="255" width="100" height="70" rx="14" fill={t.ink} />
      <rect x="165" y="335" width="70" height="22" rx="10" fill={t.ink} />
    </g>
  ),
  chat: (t, p) => (
    <g transform={`translate(0,${(1 - p) * 40})`}>
      <path d="M40 60 h250 a30 30 0 0 1 30 30 v120 a30 30 0 0 1 -30 30 h-150 l-60 50 v-50 h-40 a30 30 0 0 1 -30 -30 v-120 a30 30 0 0 1 30 -30z" fill={t.accent} />
      <path d="M140 170 h190 a30 30 0 0 1 30 30 v90 a30 30 0 0 1 -30 30 h-20 v40 l-50 -40 h-120 a30 30 0 0 1 -30 -30 v-90 a30 30 0 0 1 30 -30z" fill={t.ink} opacity={p} />
    </g>
  ),
  check: (t, p) => (
    <g><circle cx="200" cy="200" r="170" fill={t.accent2} />
      <path d="M115 205 l60 60 l115 -130" fill="none" stroke={t.paper} strokeWidth="34" strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray="320" strokeDashoffset={320 * (1 - p)} /></g>
  ),
  clock: (t, p, f) => (
    <g><circle cx="200" cy="200" r="165" fill="none" stroke={t.ink} strokeWidth="22" />
      <line x1="200" y1="200" x2="200" y2="90" stroke={t.accent} strokeWidth="18" strokeLinecap="round" transform={`rotate(${f * 6} 200 200)`} />
      <line x1="200" y1="200" x2="270" y2="200" stroke={t.ink} strokeWidth="18" strokeLinecap="round" transform={`rotate(${f * 0.5} 200 200)`} />
      <circle cx="200" cy="200" r="16" fill={t.ink} /></g>
  ),
  heart: (t, p, f) => (
    <path d="M200 340 C 60 250 30 170 70 115 C 110 60 180 75 200 125 C 220 75 290 60 330 115 C 370 170 340 250 200 340Z"
      fill={t.accent} transform={`translate(200,200) scale(${(0.7 + 0.3 * p) * (1 + 0.04 * Math.sin(f / 4))}) translate(-200,-200)`} />
  ),
  growth: (t, p) => (
    <g>{[90, 150, 230, 320].map((h, i) => (
      <rect key={i} x={40 + i * 90} y={360 - h * p} width="64" height={h * p} rx="10" fill={i === 3 ? t.accent : t.ink} />
    ))}</g>
  ),
  coffee: (t, p, f) => (
    <g>
      {[0, 1, 2].map((i) => (
        <path key={i} d={`M${140 + i * 45} 120 q -20 -30 0 -60 q 20 -30 0 -60`} fill="none" stroke={t.accent} strokeWidth="10"
          strokeLinecap="round" opacity={p * (0.5 + 0.5 * Math.sin(f / 6 + i))} />
      ))}
      <rect x="80" y="150" width="220" height="190" rx="30" fill={t.accent} />
      <path d="M300 190 a50 50 0 0 1 0 100" fill="none" stroke={t.accent} strokeWidth="24" />
      <rect x="60" y="340" width="280" height="24" rx="12" fill={t.ink} />
    </g>
  ),
  book: (t, p) => (
    <g><path d="M200 90 C150 60 80 60 30 80 V330 C80 310 150 310 200 340Z" fill={t.accent} />
      <path d="M200 90 C250 60 320 60 370 80 V330 C320 310 250 310 200 340Z" fill={t.ink} opacity={0.4 + 0.6 * p} /></g>
  ),
  laptop: (t, p) => (
    <g><rect x="70" y="70" width="260" height="190" rx="18" fill={t.ink} />
      <rect x="90" y="90" width="220" height="150" rx="8" fill={t.accent} opacity={p} />
      <path d="M30 280 h340 l-30 40 h-280z" fill={t.ink} /></g>
  ),
  // ---- added 2026-10-22 (branch kinetic-type): one icon per common idea in the creator's scripts ----
  wand: (t, p, f) => (
    <g><rect x="60" y="300" width="250" height="34" rx="17" fill={t.ink} transform="rotate(-40 185 317)" />
      <rect x="262" y="148" width="62" height="34" rx="10" fill={t.accent} transform="rotate(-40 293 165)" />
      {[[310, 80], [360, 150], [250, 60]].map(([x, y], i) => (
        <path key={i} d={`M${x} ${y - 26} L${x + 8} ${y - 8} L${x + 26} ${y} L${x + 8} ${y + 8} L${x} ${y + 26} L${x - 8} ${y + 8} L${x - 26} ${y} L${x - 8} ${y - 8}Z`}
          fill={i % 2 ? t.accent2 : t.accent} opacity={interpolate(f, [4 + i * 5, 10 + i * 5], [0, 1], clamp)}
          transform={`rotate(${f * 2} ${x} ${y})`} />))}</g>
  ),
  // two beamed eighth notes; they bob gently
  music: (t, p, f) => (
    <g transform={`translate(0 ${Math.sin(f / 8) * 6 * p})`}>
      <path d="M150 90 L330 50 L330 110 L150 150 Z" fill={t.accent} />
      <rect x="138" y="90" width="20" height="210" rx="6" fill={t.ink} /><rect x="318" y="50" width="20" height="210" rx="6" fill={t.ink} />
      <ellipse cx="110" cy="300" rx="52" ry="40" transform="rotate(-18 110 300)" fill={t.ink} />
      <ellipse cx="290" cy="260" rx="52" ry="40" transform="rotate(-18 290 260)" fill={t.ink} />
    </g>
  ),
  // a phone with a lit screen
  phone: (t, p) => (
    <g><rect x="110" y="20" width="180" height="360" rx="34" fill={t.ink} />
      <rect x="126" y="56" width="148" height="280" rx="12" fill={t.accent} opacity={0.35 + 0.65 * p} />
      <rect x="170" y="34" width="60" height="10" rx="5" fill={t.paper} opacity={0.7} /></g>
  ),
  film: (t, p) => (
    <g><rect x="40" y="90" width="320" height="220" rx="22" fill={t.ink} />
      {[0, 1, 2, 3, 4, 5].map((i) => <rect key={i} x={62 + i * 50} y="106" width="26" height="22" rx="5" fill={t.paper} opacity={0.8} />)}
      {[0, 1, 2, 3, 4, 5].map((i) => <rect key={"b" + i} x={62 + i * 50} y="272" width="26" height="22" rx="5" fill={t.paper} opacity={0.8} />)}
      <path d={`M170 160 L${170 + 80 * p} 200 L170 240Z`} fill={t.accent} /></g>
  ),
  code: (t, p) => (
    <g strokeLinecap="round" strokeLinejoin="round" fill="none" strokeWidth="30">
      <path d="M140 110 L60 200 L140 290" stroke={t.accent} /><path d="M260 110 L340 200 L260 290" stroke={t.accent} />
      <path d={`M225 90 L${225 - 50 * p} 310`} stroke={t.ink} /></g>
  ),
  palette: (t, p) => (
    <g><path d="M200 50 C90 50 30 140 50 230 C70 320 170 350 210 320 C240 298 210 262 245 250 C300 232 360 260 365 190 C370 110 300 50 200 50Z" fill={t.ink} />
      {[[130, 140, t.accent], [200, 110, t.accent2], [275, 140, t.paper], [120, 230, t.marker]].map(([x, y, c], i) => (
        <circle key={i} cx={x} cy={y} r={30 * Math.min(1, p * 1.2)} fill={c} />))}</g>
  ),
  scissors: (t, p) => (
    <g transform={`rotate(${-8 + 8 * p} 200 200)`}><circle cx="110" cy="290" r="48" fill="none" stroke={t.ink} strokeWidth="24" />
      <circle cx="290" cy="290" r="48" fill="none" stroke={t.ink} strokeWidth="24" />
      <path d={`M140 255 L${250 + 20 * p} 60`} stroke={t.accent} strokeWidth="28" strokeLinecap="round" />
      <path d={`M260 255 L${150 - 20 * p} 60`} stroke={t.accent} strokeWidth="28" strokeLinecap="round" /></g>
  ),
  zoom: (t, p) => (
    <g><circle cx="170" cy="170" r="110" fill="none" stroke={t.ink} strokeWidth="30" />
      <circle cx="170" cy="170" r={70 * p} fill={t.accent} opacity={0.85} />
      <path d="M252 252 L350 350" stroke={t.ink} strokeWidth="44" strokeLinecap="round" /></g>
  ),
  rocket: (t, p, f) => (
    <g transform={`translate(0 ${(1 - p) * 60})`}>
      <path d="M200 40 C270 100 280 200 250 280 H150 C120 200 130 100 200 40Z" fill={t.ink} />
      <circle cx="200" cy="150" r="32" fill={t.accent} />
      <path d="M150 230 L95 300 L150 280Z M250 230 L305 300 L250 280Z" fill={t.accent} />
      <path d={`M170 290 Q200 ${360 + 12 * Math.sin(f * 0.9)} 230 290Z`} fill={t.accent2} /></g>
  ),
  people: (t, p) => (
    <g>{[[110, t.accent2, 0.85], [290, t.accent2, 0.85], [200, t.accent, 1]].map(([x, c, k], i) => (
      <g key={i} opacity={Math.min(1, p * 1.5)} transform={`translate(${x} 0) scale(${k}) translate(${-x} ${i === 2 ? -10 : 20})`}>
        <circle cx={x} cy="140" r="52" fill={c} /><path d={`M${x - 85} 330 C${x - 85} 230 ${x + 85} 230 ${x + 85} 330Z`} fill={c} /></g>))}</g>
  ),
  tag: (t, p) => (
    <g><path d="M60 80 H220 L350 210 L210 350 L60 200Z" fill={t.accent} transform={`rotate(${-10 + 10 * p} 200 200)`} />
      <circle cx="130" cy="150" r="24" fill={t.paper} /></g>
  ),
  mute: (t, p) => (
    <g><path d="M60 150 H130 L220 80 V320 L130 250 H60Z" fill={t.ink} />
      <path d={`M260 150 L${260 + 90 * p} ${150 + 100 * p} M${350} 150 L${350 - 90 * p} ${150 + 100 * p}`} stroke={t.accent} strokeWidth="28" strokeLinecap="round" /></g>
  ),
  gear: (t, p, f) => (
    <g transform={`rotate(${f * 3} 200 200)`}>
      {Array.from({ length: 8 }).map((_, i) => <rect key={i} x="176" y="40" width="48" height="70" rx="10" fill={t.ink} transform={`rotate(${i * 45} 200 200)`} />)}
      <circle cx="200" cy="200" r="120" fill={t.ink} /><circle cx="200" cy="200" r="52" fill={t.accent} /></g>
  ),
  loop: (t, p, f) => (
    <g transform={`rotate(${f * 4} 200 200)`} fill="none" strokeWidth="32" strokeLinecap="round">
      <path d="M90 200 A110 110 0 0 1 290 130" stroke={t.accent} /><path d="M310 200 A110 110 0 0 1 110 270" stroke={t.ink} />
      <path d="M262 92 L300 130 L250 150" stroke={t.accent} /><path d="M138 308 L100 270 L150 250" stroke={t.ink} /></g>
  ),
  gap: (t, p) => (
    <g><path d="M40 140 H170 V260 H40Z" fill={t.ink} /><path d="M230 140 H360 V260 H230Z" fill={t.ink} />
      <path d={`M170 200 H${170 + 30 * (1 - p)}`} stroke={t.accent} strokeWidth="20" strokeLinecap="round" />
      <path d={`M230 200 H${230 - 30 * (1 - p)}`} stroke={t.accent} strokeWidth="20" strokeLinecap="round" />
      <circle cx="200" cy="200" r={22 * p} fill={t.accent} /></g>
  ),
  sparkle: (t, p, f) => (
    <g>{[[200, 200, 1], [310, 110, 0.45], [100, 300, 0.4]].map(([x, y, k], i) => (
      <path key={i} d={`M${x} ${y - 140 * k} C${x + 14 * k} ${y - 20 * k} ${x + 20 * k} ${y - 14 * k} ${x + 140 * k} ${y} C${x + 20 * k} ${y + 14 * k} ${x + 14 * k} ${y + 20 * k} ${x} ${y + 140 * k} C${x - 14 * k} ${y + 20 * k} ${x - 20 * k} ${y + 14 * k} ${x - 140 * k} ${y} C${x - 20 * k} ${y - 14 * k} ${x - 14 * k} ${y - 20 * k} ${x} ${y - 140 * k}Z`}
        fill={i ? t.accent2 : t.accent} transform={`rotate(${f * (i ? -2 : 1)} ${x} ${y}) scale(${Math.min(1, p * (1.2 - i * 0.1))})`} style={{ transformOrigin: `${x}px ${y}px` }} />))}</g>
  ),
  // ---- everyday objects: drawn here, original, no third-party artwork ----
  doc: (t, p) => (
    <g transform={`translate(0 ${(1 - p) * 30})`}>
      <path d="M90 40 H250 L320 110 V360 H90Z" fill={t.paper} stroke={t.ink} strokeWidth="16" strokeLinejoin="round" />
      <path d="M250 40 V110 H320" fill="none" stroke={t.ink} strokeWidth="16" strokeLinejoin="round" />
      {[170, 220, 270, 320].map((y, i) => <line key={i} x1="130" y1={y - 20} x2={i === 3 ? 220 : 280} y2={y - 20} stroke={i ? t.ink : t.accent} strokeWidth="14" strokeLinecap="round" opacity={i ? 0.55 : 1} />)}
    </g>
  ),
  envelope: (t, p) => (
    <g><rect x="40" y="100" width="320" height="220" rx="22" fill={t.paper} stroke={t.ink} strokeWidth="16" />
      <path d={`M48 112 L200 ${230 - 40 * (1 - p)} L352 112`} fill="none" stroke={t.accent} strokeWidth="18" strokeLinejoin="round" /></g>
  ),
  card: (t, p, f) => (
    <g><path d="M200 70 L330 110 V340 L200 300Z" fill={t.paper} stroke={t.ink} strokeWidth="14" strokeLinejoin="round" />
      <path d="M200 70 L70 110 V340 L200 300Z" fill={t.accent} stroke={t.ink} strokeWidth="14" strokeLinejoin="round" />
      <path d="M135 190 C110 165 85 195 135 235 C185 195 160 165 135 190Z" fill={t.paper} transform={`scale(${0.9 + 0.1 * Math.sin(f * 0.25)})`} style={{ transformOrigin: "135px 205px" }} /></g>
  ),
  lace: (t, p) => (
    <g fill="none" strokeLinecap="round">
      <path d="M60 300 C120 160 200 340 260 200 S330 90 350 120" stroke={t.accent} strokeWidth="18" strokeDasharray="600" strokeDashoffset={600 * (1 - p)} />
      <rect x="40" y="290" width="40" height="22" rx="8" fill={t.ink} transform="rotate(-50 60 300)" />
      <rect x="335" y="105" width="40" height="22" rx="8" fill={t.ink} transform="rotate(30 350 120)" /></g>
  ),
  balloon: (t, p, f) => (
    <g>{[[150, 160, t.accent, 0], [255, 130, t.accent2 || t.ink, 1.3]].map(([x, y, c, ph], i) => {
      const dy = Math.sin(f * 0.12 + ph) * 10 - (1 - p) * 60;
      return (<g key={i} transform={`translate(0 ${dy})`}>
        <ellipse cx={x} cy={y} rx="70" ry="86" fill={c} /><path d={`M${x - 12} ${y + 86} h24 l-12 16Z`} fill={c} />
        <path d={`M${x} ${y + 100} C${x - 30} ${y + 160} ${x + 30} ${y + 200} ${x} ${y + 250}`} stroke={t.ink} strokeWidth="6" fill="none" />
        <ellipse cx={x - 24} cy={y - 30} rx="14" ry="22" fill="#fff" opacity="0.35" /></g>);
    })}</g>
  ),
  pen: (t, p) => (
    <g transform={`rotate(${-40 + 10 * (1 - p)} 200 200)`}>
      <rect x="80" y="170" width="220" height="60" rx="14" fill={t.accent} /><rect x="250" y="170" width="50" height="60" rx="10" fill={t.ink} />
      <path d="M80 170 L20 200 L80 230Z" fill={t.paper} stroke={t.ink} strokeWidth="10" strokeLinejoin="round" />
      <rect x="120" y="150" width="120" height="16" rx="8" fill={t.ink} /></g>
  ),
  gift: (t, p) => (
    <g><rect x="70" y="170" width="260" height="190" rx="16" fill={t.accent} />
      <rect x="55" y={130 - 30 * (1 - p)} width="290" height="60" rx="14" fill={t.ink} />
      <rect x="182" y="130" width="36" height="230" fill={t.paper} />
      <path d="M200 130 C150 60 100 110 200 130 C300 110 250 60 200 130Z" fill="none" stroke={t.paper} strokeWidth="14" /></g>
  ),
  calendar: (t, p, f) => (
    <g><rect x="60" y="80" width="280" height="280" rx="28" fill={t.paper} stroke={t.ink} strokeWidth="16" />
      <path d="M60 108 A28 28 0 0 1 88 80 H312 A28 28 0 0 1 340 108 V150 H60Z" fill={t.accent} />
      <line x1="130" y1="50" x2="130" y2="110" stroke={t.ink} strokeWidth="16" strokeLinecap="round" />
      <line x1="270" y1="50" x2="270" y2="110" stroke={t.ink} strokeWidth="16" strokeLinecap="round" />
      {Array.from({ length: 9 }).map((_, i) => <rect key={i} x={100 + (i % 3) * 75} y={180 + Math.floor(i / 3) * 55} width="45" height="32" rx="6"
        fill={i === Math.floor(f / 4) % 9 ? t.accent : t.ink} opacity={i === Math.floor(f / 4) % 9 ? 1 : 0.3} />)}</g>
  ),
  shield: (t, p) => (
    <g><path d="M200 40 L330 90 V200 C330 290 270 340 200 370 C130 340 70 290 70 200 V90Z" fill={t.ink} />
      <path d={`M140 205 L185 250 L270 ${165 + 20 * (1 - p)}`} fill="none" stroke={t.accent} strokeWidth="26" strokeLinecap="round" strokeLinejoin="round" /></g>
  ),
  globe: (t, p, f) => (
    <g fill="none" strokeWidth="14"><circle cx="200" cy="200" r="150" stroke={t.ink} />
      <ellipse cx="200" cy="200" rx={60 + 30 * Math.sin(f * 0.08)} ry="150" stroke={t.accent} />
      <line x1="50" y1="200" x2="350" y2="200" stroke={t.ink} /><path d="M80 120 H320 M80 280 H320" stroke={t.ink} opacity="0.5" /></g>
  ),
  coins: (t, p, f) => (
    <g>{[0, 1, 2, 3].map((i) => {
      const o = interpolate(f, [i * 5, i * 5 + 6], [0, 1], clamp);
      return (<g key={i} opacity={o} transform={`translate(0 ${(1 - o) * -40})`}>
        <ellipse cx="200" cy={320 - i * 52} rx="120" ry="34" fill={i % 2 ? t.ink : t.accent} />
        <rect x="80" y={300 - i * 52} width="240" height="20" fill={i % 2 ? t.ink : t.accent} />
        <ellipse cx="200" cy={300 - i * 52} rx="120" ry="34" fill={i % 2 ? t.ink : t.accent} stroke={t.paper} strokeWidth="6" /></g>);
    })}</g>
  ),
};

export const ICON_NAMES = Object.keys(ICONS);

export const Icon = ({ name, t, size = 400, p = 1, start = 0, fps = 30 }) => {
  const frame = useCurrentFrame();
  const draw = ICONS[name] || ICONS.lightbulb;
  return (
    <svg width={size} height={size} viewBox="0 0 400 400" style={{ overflow: "visible" }}>
      {draw(t, p, frame - Math.round(start * fps))}
    </svg>
  );
};
