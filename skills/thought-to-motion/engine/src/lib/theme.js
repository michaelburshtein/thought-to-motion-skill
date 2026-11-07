// Themes ("moods"). Each theme is fully self-contained: colours, fonts, labels. These are neutral starting points:
// make the video yours by copying one entry with your own colours and fonts (bundle the fonts locally, see fonts.js),
// or override single values per video with plan.themeOverrides.
import "./fonts";

export const THEMES = {
  // Light and clean. Off-white paper, near-black ink, blue accent.
  light: {
    name: "light",
    paper: "#FAFAF7", ink: "#1A1A1A", accent: "#3B5BDB", accent2: "#5C677D", marker: "#DCE4FF",
    topBar: true, glow: "#EEF1FA", grid: null,
    headline: "Inter, sans-serif", headlineWeight: 700,
    ui: "Inter, sans-serif", rtl: "Heebo, Inter, sans-serif",
  },
  // Dark and calm. Charcoal paper, light ink, soft blue accent.
  dark: {
    name: "dark",
    paper: "#15171C", ink: "#F2F2F2", accent: "#7C9CFF", accent2: "#9AA3B2", marker: "#2A3350",
    topBar: false, glow: "#242A3A", grid: null,
    headline: "Inter, sans-serif", headlineWeight: 700,
    ui: "Inter, sans-serif", rtl: "Heebo, Inter, sans-serif",
  },
  // Bold and high-contrast. White paper, black ink, red accent, a faint grid.
  bold: {
    name: "bold",
    paper: "#FFFFFF", ink: "#0A0A0A", accent: "#E63946", accent2: "#1D3557", marker: "#FFE3E5",
    topBar: false, glow: "#F4F4F4", grid: "#F0F0F0",
    headline: "Inter, sans-serif", headlineWeight: 800,
    ui: "Inter, sans-serif", rtl: "Heebo, Inter, sans-serif",
  },
};
// names used by earlier versions of this skill
const ALIASES = { warm: "light", cinematic: "dark", tech: "bold" };

// Look: how a theme MOVES and is DRESSED, inside its own colours and fonts. Every option works with every theme:
//   caption  plate = rounded dark plate | scrim = no plate, a dark band rising from the bottom | panel = square panel
//   emph     marker = marker behind the word | glow = accent word + soft glow | solid = accent word only
//   sticker  tilt = rotated sticker that pops | rule = level lower-third, accent rule on the left | bracket = flat chip, corner brackets
//   enter    pop = scale + spring | wipe = slow left-to-right reveal | snap = fast, short slide
//   cut      circle = circular reveal | dissolve = cross-dissolve with a push | wipe = fast vertical wipe
//   grain / vignette / grade = texture on the footage and the canvas
//   bed      the default music bed (scripts/make_music.py: calm | warm | pulse); plan.music.style overrides it
//   sfx      sound-effect swaps and level
// Set your own with plan.look (e.g. {"caption": "scrim", "emph": "glow"}).
export const SERIES_LOOK = {
  light: { caption: "plate", emph: "solid", sticker: "rule", enter: "snap", cut: "circle", grain: 0, vignette: 0, grade: null,
    bed: "warm", sfx: { swap: {}, gain: 1 }, emphScale: 0.1, enterFrames: 10 },
  dark: { caption: "scrim", emph: "solid", sticker: "bracket", enter: "wipe", cut: "wipe", grain: 0, vignette: 0, grade: null,
    bed: "calm", sfx: { swap: {}, gain: 0.8 }, emphScale: 0.08, enterFrames: 12 },
  bold: { caption: "panel", emph: "marker", sticker: "tilt", enter: "pop", cut: "dissolve", grain: 0, vignette: 0, grade: null,
    bed: "pulse", sfx: { swap: {}, gain: 1 }, emphScale: 0.12, enterFrames: 9 },
};

export const getTheme = (plan) => {
  const key = ALIASES[plan.theme] || plan.theme;
  const base = THEMES[key] || THEMES.light;
  const look = { ...(SERIES_LOOK[base.name] || SERIES_LOOK.light), ...(plan.look || {}) };
  return { ...base, look, ...(plan.themeOverrides || {}) };
};
