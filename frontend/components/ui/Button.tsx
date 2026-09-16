import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "surface";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-bg font-medium",
  secondary: "bg-surface-2 text-ink-2 hover:text-accent",
  surface: "bg-surface text-ink-2 shadow-soft",
};

/** Borderless pill button. Size (padding, font-size) comes from className. */
export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={`whitespace-nowrap rounded-full border-none disabled:cursor-default disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
    />
  );
}

/** Round icon button used by the photo panel, map and chat. */
export function RoundButton({
  variant = "secondary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "secondary" | "surface" }) {
  const look = variant === "surface" ? "bg-surface shadow-soft" : "bg-surface-2";
  return (
    <button
      {...props}
      className={`flex size-8 items-center justify-center rounded-full border-none text-ink-2 ${look} ${className}`}
    />
  );
}
