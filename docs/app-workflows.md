<!-- last_verified: 2026-07-22 -->
# App Workflows

User journeys inside the application.

## Ingest → Enhance → Serve (the core journey)

1. **Ingest.** User goes to `/upload`, sets a **Collection** (e.g. a podcast name),
   and drops audio (MP3/WAV/OGG). It's stored at `originals/<collection>/<name>` in B2.
2. **Enhance.** User goes to `/jobs` (Enhancements) → **New enhancement**, selects
   the ingested file, picks a quality preset (Fast/Balanced/High), optionally a seed,
   and submits. A `queued` job appears and starts running (single-flight).
3. **Track.** The job row updates live (queued → processing → completed). AudioSR
   reconstructs high-frequency content and a 48 kHz WAV + JSON sidecar are written
   to `enhanced/<collection>/`.
4. **Serve.** In the job detail dialog (or the Audio Library) the user plays the
   original and enhanced renditions inline and downloads either.
- See: [Enhancement Jobs](features/enhancement-jobs.md), [Audio Enhancement](features/audio-enhancement.md)

## Create & Run an Enhancement

- User navigates to `/jobs`
- Clicks **New enhancement** → selects a source file (Select), a quality preset
  (Select), and an optional seed (blank = random)
- Job is created (`queued`) and auto-scheduled; status polls to `processing` → `completed`
- Open the job to see sample rates, duration, model/device, byte sizes, amplification,
  inline players for original + enhanced, and the B2 keys
- **Re-run** re-queues the job; **Delete** removes the enhanced WAV + sidecar + manifest (original untouched)
- See: [Enhancement Jobs](features/enhancement-jobs.md)

## Browse the Audio Library

- User navigates to `/library`
- Tracks are grouped by collection; each shows the original (player + download) and,
  when present, the enhanced rendition (player + download) with an amplification badge
- Scoped to `originals/` + `enhanced/` — the full-bucket view is under `/files`
- See: [Audio Library](features/audio-library.md)

## View Dashboard

- User navigates to `/`
- Stat cards: Files enhanced, Storage amplification (enhanced ÷ original bytes),
  Avg bandwidth gain (sample rate in→out), Jobs by status
- Chart: enhanced-output bytes per day; Table: recent enhancements
- See: [Dashboard](features/dashboard.md)

## Upload Audio

- User navigates to `/upload`, sets a collection, drops/selects audio (max 200 MB)
- Per-file progress; success toast; failures stay retryable
- See: [Audio Ingest (Upload)](features/file-upload.md)

## Browse & Manage the Whole Bucket

- User navigates to `/files` — tree view of every object (originals, enhanced,
  sidecars, job manifests), with preview/download/delete
- See: [File Browser](features/file-browser.md)
