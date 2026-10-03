"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  CircleHelp,
  FileText,
  GitPullRequestArrow,
  ShieldCheck,
  X,
} from "lucide-react";

export function HelpDialog() {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-muted hover:bg-surface-muted hover:text-ink"
        >
          <CircleHelp size={18} aria-hidden="true" /> How ContextBoard works
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-32px)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-xl border border-line bg-white p-7 shadow-xl">
          <Dialog.Title className="pr-6 text-xl font-semibold text-ink">
            From conversation to confirmed state
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm leading-6 text-muted">
            Meetings are evidence. The project state is the truth.
          </Dialog.Description>
          <ol className="my-7 space-y-6">
            {[
              {
                icon: FileText,
                title: "Start with evidence",
                text: "Keep the speaker's words and the current project baseline traceable.",
              },
              {
                icon: GitPullRequestArrow,
                title: "Review what changes",
                text: "Proposals, risks and conflicting decisions stay open for human review.",
              },
              {
                icon: ShieldCheck,
                title: "Confirm the project truth",
                text: "An explicit confirmation establishes the state used in future conversations.",
              },
            ].map(({ icon: Icon, title, text }) => (
              <li className="flex gap-4" key={title}>
                <Icon
                  className="mt-1 shrink-0 text-accent"
                  size={20}
                  aria-hidden="true"
                />
                <div>
                  <h2 className="text-sm font-semibold text-ink">{title}</h2>
                  <p className="mt-1 text-sm leading-6 text-muted">{text}</p>
                </div>
              </li>
            ))}
          </ol>
          <Dialog.Close asChild>
            <button type="button" className="button-primary">
              Got it
            </button>
          </Dialog.Close>
          <Dialog.Close asChild>
            <button
              type="button"
              aria-label="Close help"
              className="icon-button absolute right-4 top-4"
            >
              <X size={18} />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
