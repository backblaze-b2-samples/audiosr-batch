<!-- last_verified: 2026-07-22 -->
# Feature: Audio Library

## Purpose
A scoped explorer of the app's own audio: each ingested original paired with its
enhanced 48 kHz rendition (when one exists), both playable inline. Scoped
strictly to `originals/` + `enhanced/` — distinct from, and complementary to, the
full-bucket File Browser at `/files`.

## Used By
- UI: `/library` page, `apps/web/src/components/library/library-view.tsx`
- API: `GET /library`

## Core Functions
- `services/api/app/service/library.py` — `get_library()` (joins originals to enhanced by derived key)
- `services/api/app/runtime/jobs.py` — `GET /library` handler
- `apps/web/src/components/library/library-view.tsx` — grouped-by-collection view with inline players + downloads
- `apps/web/src/components/jobs/audio-player.tsx` — presigned inline `<audio>` player (shared with the job detail)

## Canonical Files
- Library service: `services/api/app/service/library.py`

## Inputs
- None (loads automatically)

## Outputs
- `GET /library` → `LibraryTrack[]`: collection, original_key, original_filename, original_size_bytes/human, content_type, uploaded_at, enhanced_key?, enhanced_size_bytes?/human?, amplification_ratio?

## Flow
- Lists `originals/` and `enhanced/` via the repo
- For each original, derives the expected enhanced key (`enhanced/<collection>/<base>.wav`) and pairs it if present
- Frontend groups tracks by collection; each row shows the original player + download, and (when enhanced) the enhanced player + download, plus the amplification badge
- Playback uses short-lived presigned URLs (reuses `/files-by-key/preview`)

## Edge Cases
- Original with no enhanced rendition → shown as "original only" with a hint to enhance it
- Empty library → prompt to upload audio
- B2 unreachable → inline error state with retry

## UX States
- Empty / Loading (skeletons) / Error (retry) / Loaded (collections with paired players)

## Verification
- Test files: `services/api/tests/test_library.py`
- Required cases: original paired with enhanced (amplification computed), original without enhanced (nulls)
- Quick verify command: `pnpm test:api`
- Pass criteria: pairing + amplification correct; tests green

## Related Docs
- [Enhancement Jobs](enhancement-jobs.md)
- [File Browser](file-browser.md) — the full-bucket explorer this coexists with
