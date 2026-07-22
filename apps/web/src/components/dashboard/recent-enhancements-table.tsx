"use client";

import Link from "next/link";
import { ArrowRight, AudioLines } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { JobStatusBadge } from "@/components/jobs/status-badge";
import { useJobs } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function basename(key: string) {
  return key.split("/").pop() || key;
}

function rateLabel(inRate: number | null, outRate: number | null) {
  if (!inRate || !outRate) return "—";
  return `${Math.round(inRate / 1000)}→${Math.round(outRate / 1000)} kHz`;
}

export function RecentEnhancementsTable() {
  const { data: jobs = [], isLoading, error, refetch } = useJobs();
  const recent = jobs.slice(0, 8);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Enhancements</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={AudioLines}
            title="No enhancements yet"
            description="Create one from the Enhancements page to get started."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[38%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Input
                </TableHead>
                <TableHead className="w-[20%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Rate
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Amp
                </TableHead>
                <TableHead className="w-[28%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((job) => (
                <TableRow key={job.id} className="table-row-hover">
                  <TableCell className="font-medium">
                    <div className="truncate" title={job.input_key}>
                      {basename(job.input_key)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(job.created_at)}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {rateLabel(job.input_sample_rate, job.output_sample_rate)}
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums whitespace-nowrap">
                    {job.amplification_ratio ? `${job.amplification_ratio.toFixed(1)}×` : "—"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <JobStatusBadge status={job.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
