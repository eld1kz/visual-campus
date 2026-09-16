"use client";

import { useState } from "react";

type Props = {
  src: string | null;
  alt: string;
  /** "natural" keeps the image's own height (masonry); "fill" covers the parent box. */
  fit?: "natural" | "fill";
};

/** Remote photo (Wikimedia Commons thumbnail). Renders nothing if missing or broken, so the striped placeholder shows. */
export function PhotoImage({ src, alt, fit = "natural" }: Props) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return null;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- remote thumbnails of unknown size; next/image needs fixed dimensions
    <img
      src={src}
      alt={alt}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className={fit === "fill" ? "absolute inset-0 size-full object-contain" : "block h-auto w-full"}
    />
  );
}
