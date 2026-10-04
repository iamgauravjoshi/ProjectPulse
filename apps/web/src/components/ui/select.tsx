"use client";
import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";

export const Select = SelectPrimitive.Root;
export const SelectValue = SelectPrimitive.Value;
export const SelectGroup = SelectPrimitive.Group;
export function SelectTrigger({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        "flex min-h-11 w-full min-w-0 items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2.5 text-left text-sm text-ink shadow-micro hover:bg-surface-muted disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="ml-auto size-4 shrink-0 text-muted" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}
export function SelectContent({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position="popper"
        sideOffset={5}
        className={cn(
          "z-[70] max-h-72 min-w-[var(--radix-select-trigger-width)] max-w-[calc(100vw-32px)] overflow-hidden rounded-lg border border-line bg-surface p-1 shadow-micro",
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}
export function SelectItem({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        "relative cursor-pointer rounded-md py-2.5 pl-3 pr-8 text-sm text-ink outline-none data-[highlighted]:bg-accent-soft data-[highlighted]:text-accent-deep",
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <SelectPrimitive.ItemIndicator className="absolute right-2 top-3">
        <Check className="size-4 text-accent" />
      </SelectPrimitive.ItemIndicator>
    </SelectPrimitive.Item>
  );
}
