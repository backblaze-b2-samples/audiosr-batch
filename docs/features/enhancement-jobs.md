<!-- last_verified: 2026-07-22 -->
# Feature: Enhancement Jobs

## Purpose
The primary entity of the app: a durable record of one audio super-resolution
run (input file + params → 48 kHz output artifact). Create, run, track, and
delete jobs; job state is persisted in B2.

## Used By
- UI: `/jobs` page (`components/jobs/*`) — table, New Enhancement dialog, detail dialog
- API: `POST /jobs`, `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/run`, `DELETE /jobs/{id}`, `GET /jobs/stats`, `GET /jobs/stats/activity`

## Core Functions
- `services/api/app/service/jobs.py` — `create_job`, `run_job`, `get_job`, `list_all_jobs`, `delete_job`, `get_enhancement_stats`, `get_enhancement_activity`
- `services/api/app/repo/job_store.py` — `save_job`, `load_job`, `list_jobs`, `delete_manifest`
- `services/api/app/runtime/jobs.py` — HTTP handlers (create schedules `run_job` via `BackgroundTasks`)
- `apps/web/src/components/jobs/jobs-table.tsx`, `new-enhancement-dialog.tsx`, `job-detail-dialog.tsx`

## Canonical Files
- Orchestration: `services/api/app/service/jobs.py`
- Persistence: `services/api/app/repo/job_store.py`

## Inputs
- `CreateJobRequest`: input_key (an `originals/` key), quality_preset (`fast`|`balanced`|`high`), seed? (optional int)

## Outputs
- `EnhancementJob` (persisted at `jobs/<id>.json`): id, input_key, output_key, sidecar_key, collection, status, quality_preset, params, sample rates, duration, model_version, device_used, byte sizes, amplification_ratio, error, timestamps
- Side effects: enhanced WAV + JSON sidecar written under `enhanced/<collection>/`

## Primary-entity lifecycle
- **create** — New Enhancement dialog → `POST /jobs`; validates the input exists under `originals/`, maps the preset → `ddim_steps`, writes a `queued` manifest, and schedules the run.
- **read** — jobs table (`GET /jobs`) + detail dialog (`GET /jobs/{id}`); both poll while a job is `queued`/`processing`.
- **run** — the marquee verb. `POST /jobs/{id}/run` re-queues a queued/failed/completed job (also auto-scheduled on create). Runs AudioSR under the single-flight lock.
- **delete** — `DELETE /jobs/{id}` removes the job's enhanced WAV + sidecar + manifest, scoped strictly to that job's keys (never a bulk wipe). The original is left untouched.
- **edit — OMITTED (UX-justified).** A job is an immutable record of one processing run. Changing parameters means producing a *different* output, which the user does by creating a new job or re-running — an edit form would either be a no-op or silently invalidate the stored artifact/sidecar. Recorded in `omitted_ui_verbs` (`entity: "Enhancement Job", operation: "edit"`).

## Form UX (New Enhancement)
- **Source audio** — a `Select` populated from the ingested originals (finite set), never free text.
- **Quality preset** — a `Select`: Fast (25 steps), Balanced (50, default), High (100). Maps to `EnhancementParams` server-side; `guidance_scale=3.5` fixed.
- **Seed** — optional integer `Input`, placeholder `42` with a "leave blank for random" description (guidance only, no autofill button). The seed used is recorded on the job.
- A short-clip hint is shown for a fast first run. Follows `settings-form.tsx` (react-hook-form + zod + shadcn Select/FormDescription).

## Flow
- Create → `queued` manifest in B2 → BackgroundTask calls `run_job`
- `run_job` (single-flight): `processing` → download original → `audiosr_engine.enhance` → upload WAV + sidecar → `completed` with computed fields
- On any exception the job is marked `failed` with the error string (never raised out of the background task)

## Edge Cases
- input_key not under `originals/` or missing → 400 on create
- ML stack absent / engine error → job `failed` with actionable message
- Concurrent runs → serialised by the single-flight lock (extra runs queue)
- Re-run overwrites the enhanced WAV/sidecar for the same base name (B2 versions it)

## UX States
- Empty: "No enhancements yet" with a create prompt
- Loading: skeleton rows
- Error: inline `ErrorState` with retry
- Live: status badge updates via polling while queued/processing

## Verification
- Test files: `services/api/tests/test_jobs.py`
- Required cases: create persists queued with preset params, rejects non-`originals/` key, run completes and writes artifacts, run marks failed on engine error, stats aggregate
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm test:web && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all tests green, no ruff violations

## Related Docs
- [Audio Enhancement](audio-enhancement.md)
- [Audio Library](audio-library.md)
- [App Workflows](../app-workflows.md)
