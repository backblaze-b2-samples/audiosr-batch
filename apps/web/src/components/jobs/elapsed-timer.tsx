"use client";

import { useEffect, useMemo, useState } from "react";

/**
 * Advancing elapsed-time readout (mm:ss) for a running job. Ticks once a second
 * so a minutes-long CPU enhancement visibly shows liveness instead of looking
 * frozen. Purely presentational — it derives from `since` plus a local clock,
 * so it needs no polling or server round-trip. Anchor `since` on the job's
 * `updated_at`, which the API stamps when the job flips to `processing`.
 */
export function ElapsedTimer({
  since,
  className,
}: {
  since: string;
  className?: string;
}) {
  // `new Date(since)` is pure (parses a fixed string); NaN is handled below
  // against the ticking clock so render stays free of impure `Date.now()`.
  const start = useMemo(() => new Date(since).getTime(), [since]);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const safeStart = Number.isNaN(start) ? now : start;
  const elapsed = Math.max(0, Math.floor((now - safeStart) / 1000));
  const mm = Math.floor(elapsed / 60);
  const ss = elapsed % 60;

  return (
    <span
      className={className}
      role="timer"
      aria-label={`Processing for ${mm} minutes ${ss} seconds`}
    >
      {mm}:{String(ss).padStart(2, "0")}
    </span>
  );
}
