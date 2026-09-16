/** 96×96 grid placeholder with the university point — real map tiles come later. */
export function MiniMapThumb({ size = 96 }: { size?: number }) {
  return (
    <div
      className="ph-grid flex shrink-0 items-center justify-center rounded-[14px] [--g:12px]"
      style={{ width: size, height: size }}
    >
      <div className="size-3 rounded-full bg-accent shadow-[0_0_0_5px_var(--accent-soft)]" />
    </div>
  );
}
