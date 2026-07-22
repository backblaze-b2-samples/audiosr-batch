"use client";

import { toast } from "sonner";
import { Play, RotateCw, Trash2 } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { JobStatusBadge } from "@/components/jobs/status-badge";
import { AudioPlayer } from "@/components/jobs/audio-player";
import { ApiError } from "@/lib/api-client";
import { useDeleteJob, useJob, useRunJob } from "@/lib/queries";
import { humanizeBytes } from "@/lib/utils";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_minmax(0,1fr)] gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0 break-all">{value}</span>
    </div>
  );
}

interface JobDetailDialogProps {
  jobId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function JobDetailDialog({ jobId, open, onOpenChange }: JobDetailDialogProps) {
  const { data: job, isLoading } = useJob(jobId ?? undefined, open && !!jobId);
  const runJob = useRunJob();
  const deleteJob = useDeleteJob();

  const handleRun = () => {
    if (!job) return;
    runJob.mutate(job.id, {
      onSuccess: () => toast.success("Re-queued — running shortly"),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Failed to run job"),
    });
  };

  const handleDelete = () => {
    if (!job) return;
    deleteJob.mutate(job.id, {
      onSuccess: () => {
        toast.success("Enhancement deleted");
        onOpenChange(false);
      },
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Failed to delete job"),
    });
  };

  const rate =
    job?.input_sample_rate && job?.output_sample_rate
      ? `${Math.round(job.input_sample_rate / 1000)} kHz → ${Math.round(
          job.output_sample_rate / 1000
        )} kHz`
      : "—";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88svh] w-[calc(100vw-2rem)] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="break-all pr-6">
            {job ? job.input_key.split("/").pop() : "Enhancement"}
          </DialogTitle>
          <DialogDescription>Enhancement job detail and provenance.</DialogDescription>
        </DialogHeader>

        {isLoading || !job ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-40" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <JobStatusBadge status={job.status} />
              {job.amplification_ratio ? (
                <span className="text-sm font-semibold tabular-nums">
                  {job.amplification_ratio.toFixed(1)}× storage amplification
                </span>
              ) : null}
            </div>

            {job.status === "failed" && job.error ? (
              <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
                {job.error}
              </p>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <AudioPlayer objectKey={job.input_key} label="Original" enabled={open} />
              <AudioPlayer
                objectKey={job.status === "completed" ? job.output_key : undefined}
                label="Enhanced (48 kHz)"
                enabled={open && job.status === "completed"}
              />
            </div>

            <div className="space-y-2 rounded-md border border-border p-4">
              <Row label="Collection" value={job.collection} />
              <Row label="Quality preset" value={job.quality_preset} />
              <Row label="Sample rate" value={rate} />
              <Row
                label="Duration"
                value={job.input_duration_sec ? `${job.input_duration_sec.toFixed(2)} s` : "—"}
              />
              <Row
                label="Size"
                value={
                  job.input_size_bytes && job.output_size_bytes
                    ? `${humanizeBytes(job.input_size_bytes)} → ${humanizeBytes(
                        job.output_size_bytes
                      )}`
                    : "—"
                }
              />
              <Row label="Model" value={job.model_version ?? "—"} />
              <Row label="Device" value={job.device_used ?? "—"} />
              <Row
                label="Params"
                value={`ddim_steps=${job.params.ddim_steps}, guidance=${job.params.guidance_scale}, seed=${job.params.seed}`}
              />
              <Row label="Input key" value={<code className="text-xs">{job.input_key}</code>} />
              <Row label="Output key" value={<code className="text-xs">{job.output_key}</code>} />
              <Row label="Sidecar" value={<code className="text-xs">{job.sidecar_key}</code>} />
            </div>

            <div className="flex flex-wrap justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRun}
                disabled={runJob.isPending || job.status === "processing" || job.status === "queued"}
              >
                {job.status === "completed" || job.status === "failed" ? (
                  <RotateCw className="h-3.5 w-3.5" />
                ) : (
                  <Play className="h-3.5 w-3.5" />
                )}
                {job.status === "completed" || job.status === "failed" ? "Re-run" : "Run"}
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm" disabled={deleteJob.isPending}>
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-lg">
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete this enhancement?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This removes the enhanced WAV, its JSON sidecar, and the job
                      record from B2. The original is left untouched. This cannot
                      be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel disabled={deleteJob.isPending}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleDelete}
                      disabled={deleteJob.isPending}
                      className={buttonVariants({ variant: "destructive" })}
                    >
                      {deleteJob.isPending ? "Deleting..." : "Delete"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
