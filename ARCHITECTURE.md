<!-- last_verified: 2026-07-15 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with enhancement metrics (files enhanced, storage amplification, bandwidth gain, jobs by status), enhanced-output volume chart, recent enhancements
  - Enhancements (`/jobs`): create / run / track / delete super-resolution jobs
  - Audio Library (`/library`): scoped explorer pairing originals with enhanced renditions, inline audio players
  - Audio upload with drag-and-drop, progress tracking
  - Full-bucket file browser with preview, download, delete
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for audio upload, enhancement jobs, library, listing, deletion
  - B2 S3 integration via boto3
  - **AudioSR super-resolution engine** (`repo/audiosr_engine.py`) — local, on-device, lazy-imported
  - B2-backed job persistence (`repo/job_store.py`) — no application database
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (incl. `EnhancementJob`, `LibraryTrack`, `EnhancementStats`)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, EnhancementJob, LibraryTrack, ...)
    config/                Settings loaded from environment (B2_REGION → endpoint property)
    repo/                  B2 S3 client + AudioSR engine + B2-backed job store (data access)
    service/               Business logic (upload, files, metadata, jobs, library)
    runtime/               FastAPI route handlers (upload, files, jobs, health, metrics)
  tests/                   pytest tests (structural + integration; torch-free)
  requirements.txt         Light core deps (API boots + tests pass on these)
  requirements-ml.txt      Heavy ML stack (torch + audiosr) — installed separately
```

### Enhancement Data Flow

```
Ingest:   Browser → POST /upload (audio) → service validates → repo put_object
          → B2 originals/<collection>/<name>

Enhance:  Browser → POST /jobs → service.create_job writes a `queued` manifest
          → B2 jobs/<id>.json; a FastAPI BackgroundTask calls service.run_job
          → (single-flight lock) download original → AudioSR engine (48 kHz)
          → put_object enhanced/<collection>/<name>.wav + .json sidecar
          → manifest updated to `completed` with sample rates, sizes, amplification

Serve:    Browser → /library or /jobs/{id} → presigned URLs (reuse /files-by-key/preview)
          → inline <audio> playback of original + enhanced
```

**Single-flight runner.** AudioSR is memory-heavy, so a module-level lock in
`service/jobs.py` serialises real enhancement runs — one job executes at a time,
extra runs queue behind the lock. Durable job state lives in B2; in-flight status
is per-replica (see [RELIABILITY.md](docs/RELIABILITY.md)).

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  - `originals/<collection>/<name>` — ingested source audio
  - `enhanced/<collection>/<name>.wav` — 48 kHz super-resolved rendition
  - `enhanced/<collection>/<name>.json` — provenance sidecar (sample rates, duration, model, sizes, amplification)
  - `jobs/<id>.json` — job manifests (the system of record for job state)
  - Listing and metadata via S3 `list_objects_v2` / `head_object`; no application database

## External Services

- **Backblaze B2 S3 API** — object storage, retrieval, deletion, presigned URLs
- **AudioSR model** — `versatile_audio_super_resolution`, run **locally / on-device**. No external API call and no second API key; the "basic" checkpoint is downloaded once from the public HuggingFace hub (keyless) and cached.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Ingest**: Browser -> `POST /upload` (multipart, audio only) -> API validates -> service writes to B2 `originals/<collection>/` -> response
- **Enhance**: Browser -> `POST /jobs` -> `queued` manifest -> BackgroundTask `run_job` (single-flight) -> AudioSR -> enhanced WAV + sidecar to B2 -> manifest `completed`
- **Track**: Browser -> `GET /jobs` / `GET /jobs/{id}` -> service reads manifests from B2 (polled while queued/processing)
- **Library**: Browser -> `GET /library` -> service joins `originals/` with `enhanced/` -> paired tracks
- **Serve**: Browser -> `/files-by-key/preview?key=...` -> presigned URL -> inline `<audio>` playback
- **Delete**: Browser -> `DELETE /jobs/{id}` -> service deletes the enhanced WAV + sidecar + manifest (scoped to that job's keys)

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Enhancement engine (repo adapter): `services/api/app/repo/audiosr_engine.py`
- Job orchestration + single-flight runner: `services/api/app/service/jobs.py`
- B2-backed job store: `services/api/app/repo/job_store.py`
- Layered API handler: `services/api/app/runtime/jobs.py` (and `runtime/upload.py`)
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`, `repo/b2_object.py`
- Pydantic models: `services/api/app/types/` (`jobs.py`, `files.py`, `upload.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Audio Enhancement](docs/features/audio-enhancement.md)
- [Enhancement Jobs](docs/features/enhancement-jobs.md)
- [Audio Library](docs/features/audio-library.md)
- [Dashboard](docs/features/dashboard.md)
- [Audio Ingest (Upload)](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
