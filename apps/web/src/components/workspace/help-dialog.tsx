"use client";

import { Button } from "../ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import {
  CircleHelp,
  FileText,
  GitPullRequestArrow,
  ShieldCheck,
  X,
} from "lucide-react";

export function HelpDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="w-full justify-start"
        >
          <CircleHelp data-icon="inline-start" aria-hidden="true" /> How
          ProjectPulse works
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle className="pr-10">
          From conversation to confirmed state
        </DialogTitle>
        <DialogDescription className="mt-2">
          Meetings are evidence. The project state is the truth.
        </DialogDescription>
        <ol className="my-7 flex flex-col gap-6">
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
        <DialogClose asChild>
          <Button type="button">Got it</Button>
        </DialogClose>
        <DialogClose asChild>
          <Button
            type="button"
            aria-label="Close help"
            variant="ghost"
            size="icon"
            className="absolute right-3 top-3"
          >
            <X data-icon="inline-start" />
          </Button>
        </DialogClose>
      </DialogContent>
    </Dialog>
  );
}
