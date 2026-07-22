import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Upload</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Ingest low-quality audio (MP3, WAV, OGG) into Backblaze B2 under a
          collection. Up to 200 MB per file. Enhance it from the Enhancements
          page.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
