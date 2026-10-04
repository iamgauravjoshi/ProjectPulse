import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";

export function FieldGroup({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="field-group"
      className={cn("flex flex-col gap-4", className)}
      {...props}
    />
  );
}
export function Field({
  className,
  orientation = "vertical",
  ...props
}: ComponentProps<"div"> & { orientation?: "vertical" | "horizontal" }) {
  return (
    <div
      data-slot="field"
      className={cn(
        "group/field flex min-w-0 gap-2 data-[disabled=true]:opacity-60",
        orientation === "horizontal"
          ? "flex-col sm:flex-row sm:items-end sm:gap-3"
          : "flex-col",
        className,
      )}
      {...props}
    />
  );
}
export function FieldLabel({ className, ...props }: ComponentProps<"label">) {
  return (
    <label
      data-slot="field-label"
      className={cn(
        "text-sm font-medium text-ink group-data-[invalid=true]/field:text-danger",
        className,
      )}
      {...props}
    />
  );
}
export function FieldDescription({ className, ...props }: ComponentProps<"p">) {
  return (
    <p
      data-slot="field-description"
      className={cn("text-xs leading-5 text-muted", className)}
      {...props}
    />
  );
}
