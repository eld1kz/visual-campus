/** Rounded map box shared by every map mode and the skeleton. */
export function MapFrame({
  children,
  tall = false,
  className = "",
  style,
}: {
  children: React.ReactNode;
  tall?: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-[20px] bg-surface-2 ${
        tall ? "h-[clamp(360px,60vh,600px)]" : "h-[clamp(360px,56vh,560px)]"
      } ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}

export function CampusPolygon({ points, fillOpacity, strokeWidth = 1.5 }: { points: string; fillOpacity: number; strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 size-full">
      <polygon
        points={points}
        fill="var(--accent)"
        fillOpacity={fillOpacity}
        stroke="var(--accent)"
        strokeWidth={strokeWidth}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function MapButton({ className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`flex size-8 items-center justify-center rounded-full border-none bg-surface text-ink-2 shadow-soft ${className}`}
    />
  );
}
