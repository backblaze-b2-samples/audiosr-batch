"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { usePreviewUrl } from "@/lib/queries";

interface AudioPlayerProps {
  objectKey: string | undefined;
  label: string;
  /** Only fetch the presigned URL when the surrounding surface is visible. */
  enabled?: boolean;
}

/**
 * Inline audio player backed by a short-lived presigned B2 URL (reuses the
 * existing `/files-by-key/preview` endpoint). Used for both the original and
 * enhanced renditions in the Enhancements detail and the Audio Library.
 */
export function AudioPlayer({ objectKey, label, enabled = true }: AudioPlayerProps) {
  const { data, isLoading, isError } = usePreviewUrl(objectKey, enabled && !!objectKey);

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      {isLoading ? (
        <Skeleton className="h-10 w-full" />
      ) : isError || !data?.url ? (
        <p className="text-xs text-destructive">Could not load audio preview.</p>
      ) : (
        <audio controls preload="none" src={data.url} className="h-10 w-full">
          Your browser does not support inline audio playback.
        </audio>
      )}
    </div>
  );
}
