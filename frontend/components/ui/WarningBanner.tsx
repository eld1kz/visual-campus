"use client";

/** Pill-shaped warning bar, e.g. «Flickr недоступен — результаты могут быть неполными.» */
export function WarningBanner({
  children,
  onDismiss,
  tone = "warn",
  className = "",
}: {
  children: React.ReactNode;
  onDismiss?: () => void;
  tone?: "warn" | "neutral";
  className?: string;
}) {
  const look = tone === "warn" ? "bg-warn-soft text-ink text-[13px] py-3 px-4" : "bg-surface-2 text-ink-2 text-[12.5px] py-2.5 px-[15px]";
  return (
    <div className={`flex items-center gap-2.5 rounded-full ${look} ${className}`}>
      <span className="text-warn">⚠</span>
      <span>{children}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="×"
          className="ml-auto border-none bg-transparent text-base leading-none text-ink-3"
        >
          ×
        </button>
      )}
    </div>
  );
}
