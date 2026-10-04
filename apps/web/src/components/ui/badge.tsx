import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";
import type { StatusTone } from "../../features/workspace/status";

const tones: Record<StatusTone, string> = {
  success: "border-success/20 bg-success-soft text-success",
  warning: "border-warning/20 bg-warning-soft text-warning",
  danger: "border-danger/20 bg-danger-soft text-danger",
  info: "border-accent/20 bg-accent-soft text-accent-deep",
  neutral: "border-neutral/20 bg-neutral-soft text-neutral",
};
export function Badge({
  className,
  tone = "neutral",
  variant = "filled",
  ...props
}: ComponentProps<"span"> & {
  tone?: StatusTone;
  variant?: "filled" | "outline";
}) {
  return (
    <span
      data-slot="badge"
      data-tone={tone}
      data-variant={variant}
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-[13px] font-medium leading-5 [&_svg]:size-3.5",
        tones[tone],
        variant === "outline" && "bg-surface",
        className,
      )}
      {...props}
    />
  );
}
