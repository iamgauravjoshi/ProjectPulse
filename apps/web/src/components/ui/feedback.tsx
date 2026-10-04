import type { ComponentProps } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "../../lib/utils";

export function Alert({
  className,
  variant = "info",
  ...props
}: ComponentProps<"div"> & { variant?: "info" | "success" | "destructive" }) {
  return (
    <div
      data-slot="alert"
      role={variant === "destructive" ? "alert" : "status"}
      className={cn(
        "rounded-lg border px-4 py-3 text-sm leading-6",
        variant === "destructive"
          ? "border-danger/20 bg-danger-soft text-danger"
          : variant === "success"
            ? "border-success/20 bg-success-soft text-success"
            : "border-accent/20 bg-accent-soft text-accent-deep",
        className,
      )}
      {...props}
    />
  );
}
export function Empty({
  className,
  compact = false,
  ...props
}: ComponentProps<"div"> & { compact?: boolean }) {
  return (
    <div
      data-slot="empty"
      className={cn(
        "flex flex-col items-center gap-3 text-center",
        compact ? "px-5 py-8" : "mx-auto max-w-md px-6 py-12",
        className,
      )}
      {...props}
    />
  );
}
export function EmptyMedia({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "mb-1 flex size-12 items-center justify-center rounded-xl bg-surface-muted text-muted [&_svg]:size-6",
        className,
      )}
      {...props}
    />
  );
}
export function EmptyTitle({
  asChild = false,
  className,
  ...props
}: ComponentProps<"h3"> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "h3";
  return (
    <Component
      className={cn("text-lg font-semibold text-ink", className)}
      {...props}
    />
  );
}
export function EmptyDescription({ className, ...props }: ComponentProps<"p">) {
  return (
    <p className={cn("text-sm leading-6 text-muted", className)} {...props} />
  );
}
export function Skeleton({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn(
        "animate-pulse rounded-md bg-line/70 motion-reduce:animate-none",
        className,
      )}
      {...props}
    />
  );
}
export function Separator({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      className={cn("h-px w-full shrink-0 bg-line", className)}
      {...props}
    />
  );
}
