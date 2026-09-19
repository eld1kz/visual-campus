"use client";

import { useEffect } from "react";

type Props = {
  onClick: () => void;
  children: React.ReactNode;
  /** Esc triggers the same action (ignored while typing in a field or when a dialog handles Esc itself). */
  escape?: boolean;
  className?: string;
};

/** Quiet "← back" / "Cancel" text button used on every step of search → profile. */
export function BackButton({ onClick, children, escape = true, className = "" }: Props) {
  useEffect(() => {
    if (!escape) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (e.key !== "Escape" || e.defaultPrevented || target?.closest("input, textarea, select")) return;
      if (document.querySelector("[role=dialog]")) return; // Esc closes the open photo first
      onClick();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [escape, onClick]);

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border-none bg-transparent px-0 py-1 text-[13px] text-ink-3 hover:text-ink ${className}`}
    >
      {children}
    </button>
  );
}
