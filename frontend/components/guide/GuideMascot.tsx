"use client";

import { Mascot } from "@/components/mascot/Mascot";
import type { MascotState } from "@/lib/types";
import { useGuide } from "./GuideProvider";

/** Mascot dressed in the current outfit and university colors. */
export function GuideMascot({ height, state }: { height: number; state?: MascotState }) {
  const { outfit, brand, mascot } = useGuide();
  return (
    <Mascot
      state={state ?? mascot}
      top={outfit.top}
      head={outfit.head}
      accessory={outfit.accessory}
      primary={brand.primary}
      secondary={brand.secondary}
      label={brand.label}
      height={height}
    />
  );
}
