import { JobsTable } from "@/components/jobs/jobs-table";

export default function JobsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Enhancements</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Create, run, and track audio super-resolution jobs. Each run reconstructs
          high-frequency content with AudioSR and writes a 48 kHz WAV plus a JSON
          sidecar back to Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <JobsTable />
      </div>
    </div>
  );
}
