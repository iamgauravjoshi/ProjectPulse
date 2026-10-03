import { CircleAlert, FolderOpen, type LucideIcon } from "lucide-react";

export function Feedback({
  title,
  description,
  action,
  icon: Icon = FolderOpen,
  headingLevel = 1,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: LucideIcon;
  headingLevel?: 1 | 2 | 3;
}) {
  const Heading = headingLevel === 1 ? "h1" : headingLevel === 2 ? "h2" : "h3";
  return (
    <section className="mx-auto flex max-w-md flex-col items-center px-6 py-16 text-center">
      <div className="mb-5 rounded-xl bg-surface-muted p-3">
        <Icon size={24} aria-hidden="true" className="text-muted" />
      </div>
      <Heading className="text-xl font-semibold text-ink">{title}</Heading>
      <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </section>
  );
}

export function ErrorFeedback({
  title,
  retry,
  headingLevel = 1,
}: {
  title: string;
  retry: () => void;
  headingLevel?: 1 | 2 | 3;
}) {
  return (
    <Feedback
      title={title}
      headingLevel={headingLevel}
      description="Check your connection and try again."
      icon={CircleAlert}
      action={
        <button type="button" className="button-primary" onClick={retry}>
          Try again
        </button>
      }
    />
  );
}

export function WorkspaceSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading workspace"
      className="space-y-7 p-6 lg:p-8"
    >
      <span className="sr-only">Loading workspace</span>
      <div className="skeleton h-7 w-64 max-w-full" />
      <div className="skeleton h-4 w-96 max-w-full" />
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
        {[1, 2, 3, 4].map((key) => (
          <div className="skeleton h-24" key={key} />
        ))}
      </div>
      <div className="rounded-xl border border-line bg-white p-5">
        <div className="skeleton mb-7 h-5 w-40" />
        {[1, 2, 3, 4].map((key) => (
          <div className="skeleton my-5 h-10" key={key} />
        ))}
      </div>
    </div>
  );
}
