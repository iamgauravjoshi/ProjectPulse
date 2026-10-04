import { ChevronDown } from "lucide-react";
import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";

const control =
  "min-h-11 w-full min-w-0 rounded-lg border border-line bg-surface px-3 py-2.5 text-sm text-ink shadow-micro transition-colors placeholder:text-muted focus-visible:border-accent aria-invalid:border-danger disabled:cursor-not-allowed disabled:opacity-50";
export function Input({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      data-slot="input"
      className={cn(
        control,
        "file:mr-3 file:rounded-md file:border-0 file:bg-accent-soft file:px-3 file:py-1 file:text-accent-deep",
        className,
      )}
      {...props}
    />
  );
}
export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(control, "min-h-24 resize-y", className)}
      {...props}
    />
  );
}
export function NativeSelect({
  className,
  ...props
}: ComponentProps<"select">) {
  return (
    <div
      data-slot="native-select-wrapper"
      className={cn("relative min-w-0", className)}
    >
      <select
        data-slot="native-select"
        className={cn(control, "appearance-none pr-9")}
        {...props}
      />
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted"
      />
    </div>
  );
}
export function InputGroup({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="input-group"
      className={cn(
        "flex min-h-11 min-w-0 items-center gap-2 rounded-lg border border-line bg-surface px-3 shadow-micro focus-within:border-accent focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent",
        className,
      )}
      {...props}
    />
  );
}
export function InputGroupAddon({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      data-slot="input-group-addon"
      className={cn(
        "flex shrink-0 items-center text-muted [&_svg]:size-4",
        className,
      )}
      {...props}
    />
  );
}
export function InputGroupInput({
  className,
  ...props
}: ComponentProps<"input">) {
  return (
    <input
      data-slot="input-group-input"
      className={cn(
        "min-h-11 w-full min-w-0 bg-transparent py-2.5 text-sm text-ink outline-none placeholder:text-muted disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
