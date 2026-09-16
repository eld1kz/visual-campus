import type { CSSProperties } from "react";
import type { MascotState, OutfitAccessory, OutfitHead, OutfitTop } from "@/lib/types";

// «Кампи» — layered flat-vector character, ported from design/Mascot.dc.html.
// Layers are kept separate so they can move to Rive/Lottie without redrawing.

export type MascotProps = {
  state?: MascotState;
  top?: OutfitTop;
  head?: OutfitHead;
  accessory?: OutfitAccessory;
  primary?: string;
  secondary?: string;
  label?: string;
  height?: number;
  packColor?: string;
};

const SKIN = "#e8c6a8";
const SKIN_SHADE = "#dfb896";
const HAIR = "#3a3733";
const SHOES = "#22201e";
const INK = "#26241f";

function poseStyles(state: MascotState) {
  const arm: CSSProperties = { transformBox: "view-box" };
  let body = "km-sway 3.6s ease-in-out infinite";
  const left: CSSProperties = { ...arm, transformOrigin: "47px 118px" };
  const right: CSSProperties = { ...arm, transformOrigin: "112px 118px" };
  const mouth: CSSProperties = { transformBox: "view-box", transformOrigin: "80px 89px", transform: "scale(0.95,0.55)" };

  switch (state) {
    case "hello":
      right.animation = "km-wave .6s ease-in-out infinite";
      mouth.transform = "scaleY(1.15)";
      break;
    case "thinking":
      right.transform = "rotate(-142deg)";
      left.transform = "rotate(6deg)";
      mouth.transform = "scaleY(0.5)";
      break;
    case "talking":
      mouth.animation = "km-talk .3s ease-in-out infinite";
      left.animation = "km-gesture 1.4s ease-in-out infinite";
      break;
    case "pointing":
      right.animation = "km-point 1.1s ease-in-out infinite";
      mouth.transform = "scaleY(0.9)";
      break;
    case "dont_know":
      left.transform = "rotate(38deg)";
      right.animation = "km-shrug 1.6s ease-in-out infinite";
      mouth.transform = "scale(0.7,0.6)";
      break;
    case "changing":
      body = "km-change .55s ease-in-out infinite";
      break;
  }
  return { body, left, right, mouth };
}

export function Mascot({
  state = "idle",
  top = "hoodie",
  head = "cap",
  accessory = "backpack",
  primary = "oklch(0.55 0.14 265)",
  secondary = "#f4f4f2",
  label = "KU",
  height = 200,
  packColor = "#3f4247",
}: MascotProps) {
  const pose = poseStyles(state);
  const sleeve = top === "varsity" ? secondary : primary;
  const labelFont: CSSProperties = {
    position: "absolute",
    left: "50%",
    transform: "translateX(-50%)",
    pointerEvents: "none",
    fontFamily: "var(--font-sans)",
    fontWeight: 600,
    lineHeight: 1,
  };

  return (
    <div
      className="relative flex select-none items-end justify-center"
      style={{ height, animation: pose.body, transformOrigin: "50% 100%" }}
    >
      <svg
        viewBox="0 0 160 248"
        role="img"
        aria-label="Кампи"
        style={{ height, width: "auto", overflow: "visible", display: "block" }}
      >
        <ellipse cx="80" cy="238" rx="34" ry="5.5" fill="#000" opacity="0.08" />
        <g>
          {state === "thinking" && (
            <g>
              {[0, 0.18, 0.36].map((delay, i) => (
                <circle
                  key={i}
                  cx={112 + i * 14}
                  cy={i === 1 ? 16 : 20}
                  r="4"
                  fill={primary}
                  style={{ animation: `km-dots 1.1s ease-in-out ${delay}s infinite` }}
                />
              ))}
            </g>
          )}
          {state === "changing" && (
            <g>
              <circle cx="34" cy="70" r="3.5" fill={primary} style={{ animation: "km-spark .7s ease-out infinite" }} />
              <circle cx="128" cy="52" r="3" fill={primary} style={{ animation: "km-spark .7s ease-out .2s infinite" }} />
              <circle cx="120" cy="140" r="3" fill={primary} style={{ animation: "km-spark .7s ease-out .4s infinite" }} />
            </g>
          )}

          {accessory === "backpack" && (
            <g>
              <rect x="36" y="116" width="88" height="62" rx="20" fill={packColor} />
              <rect x="40" y="134" width="80" height="4" rx="2" fill="#000" opacity="0.14" />
            </g>
          )}

          <rect x="61" y="172" width="14" height="50" rx="7" fill={HAIR} />
          <rect x="85" y="172" width="14" height="50" rx="7" fill={HAIR} />
          <rect x="56" y="214" width="21" height="13" rx="6.5" fill={SHOES} />
          <rect x="83" y="214" width="21" height="13" rx="6.5" fill={SHOES} />

          {top === "hoodie" && (
            <g>
              <rect x="50" y="110" width="60" height="76" rx="22" fill={primary} />
              <rect x="62" y="152" width="36" height="16" rx="8" fill="#000" opacity="0.12" />
              <path d="M60 116 q20 18 40 0" fill="none" stroke={secondary} strokeWidth="3" strokeLinecap="round" opacity="0.9" />
            </g>
          )}
          {top === "tshirt" && (
            <g>
              <rect x="52" y="110" width="56" height="66" rx="18" fill={primary} />
              <rect x="70" y="110" width="20" height="9" rx="4.5" fill={secondary} opacity="0.85" />
            </g>
          )}
          {top === "varsity" && (
            <g>
              <rect x="50" y="110" width="60" height="76" rx="20" fill={secondary} />
              <rect x="50" y="110" width="30" height="76" rx="20" fill={primary} />
              <rect x="76" y="110" width="8" height="76" fill={primary} opacity="0.9" />
              <rect x="50" y="178" width="60" height="8" rx="4" fill={primary} />
            </g>
          )}

          {accessory === "backpack" && (
            <g>
              <rect x="60" y="110" width="7" height="42" rx="3.5" fill={packColor} opacity="0.92" />
              <rect x="93" y="110" width="7" height="42" rx="3.5" fill={packColor} opacity="0.92" />
            </g>
          )}

          <g style={pose.left}>
            <rect x="41" y="114" width="13" height="56" rx="6.5" fill={sleeve} />
            <circle cx="47.5" cy="172" r="8" fill={SKIN} />
          </g>
          <g style={pose.right}>
            <rect x="106" y="114" width="13" height="56" rx="6.5" fill={sleeve} />
            <circle cx="112.5" cy="172" r="8" fill={SKIN} />
          </g>

          <rect x="72" y="96" width="16" height="18" rx="7" fill={SKIN_SHADE} />

          {accessory === "scarf" && (
            <g>
              <rect x="56" y="98" width="48" height="16" rx="8" fill={primary} />
              <rect x="92" y="106" width="13" height="34" rx="6.5" fill={primary} opacity="0.92" />
              <rect x="60" y="102" width="40" height="3" rx="1.5" fill={secondary} opacity="0.7" />
            </g>
          )}

          <g>
            <circle cx="80" cy="66" r="35" fill={HAIR} />
            <circle cx="80" cy="72" r="33" fill={SKIN} />
            <circle cx="45" cy="74" r="6.5" fill={SKIN_SHADE} />
            <circle cx="115" cy="74" r="6.5" fill={SKIN_SHADE} />
            <rect x="49" y="40" width="62" height="20" rx="10" fill={HAIR} />
            <circle cx="66" cy="84" r="6" fill={primary} opacity="0.14" />
            <circle cx="94" cy="84" r="6" fill={primary} opacity="0.14" />
            <g
              style={{
                transformBox: "view-box",
                transformOrigin: "80px 72px",
                animation: "km-blink 5s ease-in-out infinite",
              }}
            >
              <ellipse cx="69" cy="72" rx="4" ry="5" fill={INK} />
              <ellipse cx="91" cy="72" rx="4" ry="5" fill={INK} />
            </g>
            <rect x="63" y="60" width="12" height="3" rx="1.5" fill={INK} opacity="0.75" />
            <rect x="85" y="60" width="12" height="3" rx="1.5" fill={INK} opacity="0.75" />
            <ellipse cx="80" cy="89" rx="7" ry="4.5" fill={INK} style={pose.mouth} />
            {head === "cap" && (
              <g>
                <rect x="48" y="30" width="64" height="24" rx="12" fill={primary} />
                <ellipse cx="80" cy="53" rx="37" ry="7" fill={primary} />
                <ellipse cx="80" cy="52" rx="37" ry="4" fill="#000" opacity="0.12" />
              </g>
            )}
          </g>
        </g>
      </svg>
      <div
        style={{
          ...labelFont,
          top: height * 0.585,
          letterSpacing: "0.04em",
          fontSize: +(height * 0.072).toFixed(1),
          color: top === "varsity" ? primary : secondary,
        }}
      >
        {label}
      </div>
      {head === "cap" && (
        <div style={{ ...labelFont, top: height * 0.145, fontSize: +(height * 0.046).toFixed(1), color: secondary }}>
          {label}
        </div>
      )}
    </div>
  );
}
