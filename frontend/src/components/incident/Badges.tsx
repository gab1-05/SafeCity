import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { SEVERITY_LABELS, STATUS_LABELS, type IncidentStatus, type Severity } from "@/types";

const STATUS_VARIANTS: Record<IncidentStatus, "default" | "secondary" | "success" | "warning" | "danger" | "outline" | "ghost" | "brand"> = {
  draft: "ghost",
  submitted: "warning",
  under_review: "warning",
  verified: "default",
  rejected: "ghost",
  duplicate: "ghost",
  assigned: "default",
  in_progress: "default",
  awaiting_info: "warning",
  escalated: "danger",
  resolved: "success",
  closed: "success",
  reopened: "danger",
};

const SEVERITY_VARIANTS: Record<Severity, "ghost" | "warning" | "danger"> = {
  low: "ghost",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

export function StatusBadge({ status }: { status: IncidentStatus }) {
  return <Badge variant={STATUS_VARIANTS[status]}>{STATUS_LABELS[status]}</Badge>;
}

export function SeverityBadge({ severity, critical }: { severity: Severity; critical?: boolean }) {
  return (
    <Badge
      variant={SEVERITY_VARIANTS[severity]}
      className={cn(critical && "animate-pulse")}
    >
      {critical ? "EMERGENCY · " : ""}
      {SEVERITY_LABELS[severity]}
    </Badge>
  );
}