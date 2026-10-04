import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";

export function Card({ className, ...props }: ComponentProps<"section">) {
  return (
    <section
      data-slot="card"
      className={cn(
        "min-w-0 rounded-xl border border-line bg-surface",
        className,
      )}
      {...props}
    />
  );
}
export function CardHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4",
        className,
      )}
      {...props}
    />
  );
}
export function CardTitle({ className, ...props }: ComponentProps<"h2">) {
  return (
    <h2
      data-slot="card-title"
      className={cn(
        "flex items-center gap-2 text-base font-semibold leading-6 text-ink",
        className,
      )}
      {...props}
    />
  );
}
export function CardDescription({ className, ...props }: ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn("mt-1 text-sm leading-6 text-muted", className)}
      {...props}
    />
  );
}
export function CardContent({
  className,
  flush = false,
  ...props
}: ComponentProps<"div"> & { flush?: boolean }) {
  return (
    <div
      data-slot="card-content"
      className={cn(!flush && "p-5", className)}
      {...props}
    />
  );
}
export function CardFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        "flex flex-wrap items-center gap-3 border-t border-line px-5 py-4",
        className,
      )}
      {...props}
    />
  );
}
