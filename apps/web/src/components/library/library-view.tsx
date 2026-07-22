"use client";

import { useMemo } from "react";
import Link from "next/link";
import { Download, Library, RefreshCw, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { AudioPlayer } from "@/components/jobs/audio-player";
import { ApiError, getDownloadUrl } from "@/lib/api-client";
import { useLibrary } from "@/lib/queries";
import type { LibraryTrack } from "@audiosr-batch/shared";

async function download(key: string) {
  try {
    const { url } = await getDownloadUrl(key);
    window.open(url, "_blank");
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Failed to get download URL");
  }
}

function TrackRow({ track }: { track: LibraryTrack }) {
  return (
    <div className="rounded-md border border-border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-medium" title={track.original_filename}>
            {track.original_filename}
          </p>
          <p className="text-xs text-muted-foreground">
            {track.original_size_human}
            {track.enhanced_size_human ? (
              <>
                {" → "}
                {track.enhanced_size_human}
              </>
            ) : null}
          </p>
        </div>
        {track.enhanced_key ? (
          <Badge variant="ghost" className="bg-[var(--success)]/15 text-[var(--success)]">
            {track.amplification_ratio ? `${track.amplification_ratio.toFixed(1)}× enhanced` : "enhanced"}
          </Badge>
        ) : (
          <Badge variant="ghost" className="bg-muted text-muted-foreground">
            original only
          </Badge>
        )}
      </div>

      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <AudioPlayer objectKey={track.original_key} label="Original" />
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => download(track.original_key)}
          >
            <Download className="h-3.5 w-3.5" />
            Download original
          </Button>
        </div>
        <div className="space-y-2">
          {track.enhanced_key ? (
            <>
              <AudioPlayer objectKey={track.enhanced_key} label="Enhanced (48 kHz)" />
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={() => download(track.enhanced_key as string)}
              >
                <Download className="h-3.5 w-3.5" />
                Download enhanced
              </Button>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">
              Not enhanced yet — create an enhancement from the Enhancements page.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function LibraryView() {
  const { data: tracks = [], isLoading, isFetching, error, refetch } = useLibrary();

  const byCollection = useMemo(() => {
    const groups = new Map<string, LibraryTrack[]>();
    for (const t of tracks) {
      const list = groups.get(t.collection) ?? [];
      list.push(t);
      groups.set(t.collection, list);
    }
    return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [tracks]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} title="Couldn't load the library" onRetry={() => refetch()} />;
  }

  if (tracks.length === 0) {
    return (
      <EmptyState
        icon={Library}
        title="Your audio library is empty"
        description="Ingest audio on the Upload page — it appears here paired with its enhanced rendition."
        action={
          <Button asChild size="sm">
            <Link href="/upload">
              <Upload className="h-3.5 w-3.5" />
              Upload audio
            </Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          className="h-8 text-xs"
          disabled={isFetching}
          aria-label="Refresh library"
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>
      {byCollection.map(([collection, list]) => (
        <Card key={collection}>
          <CardHeader className="border-b border-border px-5 py-4">
            <CardTitle className="card-title">
              {collection}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {list.length} {list.length === 1 ? "track" : "tracks"}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 p-4">
            {list.map((t) => (
              <TrackRow key={t.original_key} track={t} />
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
