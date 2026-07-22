import { JobsTable } from "@/components/jobs/jobs-table";

// Read the optional `?enhance=<b2-key>` deep link server-side (the upload
// success CTA links here). Reading searchParams keeps this the idiomatic Next
// way to hand a client component an initial value without a `useSearchParams`
// Suspense boundary.
export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ enhance?: string | string[] }>;
}) {
  const { enhance } = await searchParams;
  const initialEnhanceKey = Array.isArray(enhance) ? enhance[0] : enhance;

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
        <JobsTable initialEnhanceKey={initialEnhanceKey} />
      </div>
    </div>
  );
}
