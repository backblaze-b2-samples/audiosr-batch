import { LibraryView } from "@/components/library/library-view";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Audio Library</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Browse this app&apos;s audio — each ingested original paired with its
          enhanced 48 kHz rendition. Scoped to <code>originals/</code> and{" "}
          <code>enhanced/</code>; the full-bucket view lives under Files.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <LibraryView />
      </div>
    </div>
  );
}
