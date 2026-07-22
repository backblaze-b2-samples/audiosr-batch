"use client";

import { useState } from "react";
import { AudioLines, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { NewEnhancementDialog } from "@/components/jobs/new-enhancement-dialog";
import { JobDetailDialog } from "@/components/jobs/job-detail-dialog";
import { useJobs } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function basename(key: string) {
  return key.split("/").pop() || key;
}

function rateLabel(inRate: number | null, outRate: number | null) {
  if (!inRate || !outRate) return "—";
  return `${Math.round(inRate / 1000)}→${Math.round(outRate / 1000)} kHz`;
}

export function JobsTable() {
  const { data: jobs = [], isLoading, isFetching, error, refetch } = useJobs();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const openDetail = (id: string) => {
    setSelectedId(id);
    setDetailOpen(true);
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4 space-y-0">
          <CardTitle className="card-title">Enhancement Jobs</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="touch-target h-8 shrink-0 text-xs"
              disabled={isFetching}
              aria-label="Refresh jobs"
            >
              <RefreshCw
                aria-hidden="true"
                className={`h-3.5 w-3.5 mr-1 ${isFetching ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
            <NewEnhancementDialog />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <ErrorState error={error} title="Couldn't load jobs" onRetry={() => refetch()} className="px-4" />
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={AudioLines}
              title="No enhancements yet"
              description="Create your first enhancement to super-resolve an ingested file to 48 kHz."
            />
          ) : (
            <Table className="table-fixed">
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="w-[30%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Input
                  </TableHead>
                  <TableHead className="w-[16%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Rate
                  </TableHead>
                  <TableHead className="w-[12%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Amp
                  </TableHead>
                  <TableHead className="w-[20%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Created
                  </TableHead>
                  <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Status
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow
                    key={job.id}
                    className="table-row-hover cursor-pointer"
                    onClick={() => openDetail(job.id)}
                  >
                    <TableCell className="font-medium">
                      <div className="truncate" title={job.input_key}>
                        {basename(job.input_key)}
                      </div>
                      <div className="text-xs text-muted-foreground">{job.collection}</div>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                      {rateLabel(job.input_sample_rate, job.output_sample_rate)}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums whitespace-nowrap">
                      {job.amplification_ratio ? `${job.amplification_ratio.toFixed(1)}×` : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {formatDate(job.created_at)}
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

      <JobDetailDialog jobId={selectedId} open={detailOpen} onOpenChange={setDetailOpen} />
    </>
  );
}
