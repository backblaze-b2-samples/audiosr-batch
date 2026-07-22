import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@audiosr-batch/shared";

const CONFIG: Record<
  JobStatus,
  { label: string; className: string; icon: typeof Clock; spin?: boolean }
> = {
  queued: {
    label: "Queued",
    className: "bg-muted text-muted-foreground",
    icon: Clock,
  },
  processing: {
    label: "Processing",
    className: "bg-[var(--brand-b2)]/15 text-[var(--brand-b2)]",
    icon: Loader2,
    spin: true,
  },
  completed: {
    label: "Completed",
    className: "bg-[var(--success)]/15 text-[var(--success)]",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "bg-destructive/15 text-destructive",
    icon: XCircle,
  },
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const cfg = CONFIG[status];
  const Icon = cfg.icon;
  return (
    <Badge variant="ghost" className={cfg.className}>
      <Icon className={cfg.spin ? "animate-spin" : ""} aria-hidden="true" />
      {cfg.label}
    </Badge>
  );
}
