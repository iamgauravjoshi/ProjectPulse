import { CircleAlert, FolderOpen, type LucideIcon } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyMedia,
  EmptyTitle,
  Skeleton,
} from "../ui/feedback";

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
    <Empty>
      <EmptyMedia>
        <Icon aria-hidden="true" />
      </EmptyMedia>
      <EmptyTitle asChild>
        <Heading>{title}</Heading>
      </EmptyTitle>
      <EmptyDescription>{description}</EmptyDescription>
      {action && <div className="mt-2">{action}</div>}
    </Empty>
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
      action={<Button onClick={retry}>Try again</Button>}
    />
  );
}
export function WorkspaceSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading workspace"
      className="flex flex-col gap-7 p-6 lg:p-8"
    >
      <span className="sr-only">Loading workspace</span>
      <Skeleton className="h-7 w-64 max-w-full" />
      <Skeleton className="h-4 w-96 max-w-full" />
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
        {[1, 2, 3, 4].map((key) => (
          <Skeleton className="h-24" key={key} />
        ))}
      </div>
      <Card>
        <CardContent>
          <Skeleton className="mb-7 h-5 w-40" />
          {[1, 2, 3, 4].map((key) => (
            <Skeleton className="my-5 h-10" key={key} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
