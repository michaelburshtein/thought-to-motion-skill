import React from "react";
import { Composition, registerRoot } from "remotion";
import { Main } from "./Main";
import { Bumper } from "./components/Bumper";

// One composition. The plan (see references/plan-schema.md) arrives as input props:
//   npx remotion render src/index.jsx Main out.mp4 --props=plan.json --public-dir=<job>/public
const EXAMPLE = {
  mode: "voice", lang: "en", theme: "light", fps: 30, duration: 4, source: "voice.wav",
  brand: { wordmark: "YOUR NAME", series: "notes" }, captions: [], keywords: [], elements: [],
};

const Root = () => (
  <>
  <Composition
    id="Main"
    component={Main}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={120}
    defaultProps={{ plan: EXAMPLE }}
    calculateMetadata={({ props }) => {
      const fps = props.plan.fps || 30;
      const wide = props.plan.aspect === "16:9";
      return { fps, durationInFrames: Math.max(1, Math.floor(props.plan.duration * fps)),
               width: wide ? 1920 : 1080, height: wide ? 1080 : 1920 };
    }}
  />
  <Composition
    id="Bumper"
    component={Bumper}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={60}
    defaultProps={{ plan: { kind: "intro", theme: "bold", fps: 30, duration: 2, brand: { wordmark: "YOUR NAME", series: "notes" } } }}
    calculateMetadata={({ props }) => ({ fps: props.plan.fps || 30,
      durationInFrames: Math.max(1, Math.round((props.plan.duration || (props.plan.kind === "outro" ? 3 : 2)) * (props.plan.fps || 30))) })}
  />
  </>
);

registerRoot(Root);
