import type { LucideIcon } from "lucide-react";
import { humanLabel } from "../../features/workspace/presenters";
import { statusTone } from "../../features/workspace/status";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Empty, EmptyDescription } from "../ui/feedback";

export function StatusBadge({
  status,
  variant = "filled",
}: {
  status: string;
  variant?: "filled" | "outline";
}) {
  return (
    <Badge tone={statusTone(status)} variant={variant} data-status={status}>
      {humanLabel(status)}
    </Badge>
  );
}

export function Panel({
  title,
  icon: Icon,
  action,
  children,
  id,
}: {
  title: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  children: React.ReactNode;
  id?: string;
}) {
  return (
    <Card id={id}>
      <CardHeader>
        <CardTitle>
          {Icon && <Icon size={18} aria-hidden="true" className="text-muted" />}
          {title}
        </CardTitle>
        {action}
      </CardHeader>
      <CardContent flush>{children}</CardContent>
    </Card>
  );
}
export function EmptyCategory({ text }: { text: string }) {
  return (
    <Empty compact>
      <EmptyDescription>{text}</EmptyDescription>
    </Empty>
  );
}
