import { Slot } from "@radix-ui/react-slot";
import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";

const variants = {
  default:
    "font-semibold border-transparent bg-accent text-white hover:bg-accent-deep",
  outline:
    "border-line bg-surface text-ink hover:border-muted/40 hover:bg-surface-muted",
  secondary:
    "border-transparent bg-accent-soft text-accent-deep hover:bg-accent-soft/70",
  ghost: "border-transparent text-muted hover:bg-surface-muted hover:text-ink",
  destructive: "border-transparent bg-danger text-white hover:bg-danger-hover",
  "destructive-outline":
    "border-danger/25 bg-surface text-danger hover:bg-danger-soft",
  link: "border-transparent text-accent-deep underline-offset-4 hover:underline",
} as const;

export function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  type,
  ...props
}: ComponentProps<"button"> & {
  variant?: keyof typeof variants;
  size?: "default" | "sm" | "icon";
  asChild?: boolean;
}) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      data-slot="button"
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
        variants[variant],
        size === "icon" ? "size-11" : "min-h-11 px-4 py-2.5",
        size === "sm" && "px-3",
        className,
      )}
      {...(!asChild ? { type: type ?? "button" } : {})}
      {...props}
    />
  );
}
