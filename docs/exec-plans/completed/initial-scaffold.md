# Build plan — `audiosr-batch`

Source of truth for the delta: the freshly-cloned starter kit at
`.claude/scratch/vcsk-083b3327-2558-47f4-90d8-e3b00482f5d6/`. Build from that tree only.

## 1. Purpose

`audiosr-batch` is a **batch audio super-resolution pipeline** for podcast networks,
oral-history archives, and music-production teams that need to restore and upscale
large libraries of degraded audio (8–22 kHz call recordings, legacy field tapes,
low-bitrate music) to 48 kHz output. It ingests low-quality audio into Backblaze B2,
runs the open-source **versatile_audio_super_resolution** (AudioSR) model **locally**
to reconstruct missing high-frequency content, and writes the high-resolution WAV
rendition plus a JSON metadata sidecar back to B2 alongside the original for provenance
and downstream training. The sample is a concrete demonstration of **write
amplification at scale**: every compressed original expands into a full-quality WAV
(typically 5–10× larger) plus a sidecar, so a 1 TB archive can become 5–10 TB in B2.
B2 is the single storage layer — accessed via the S3-compatible API with a custom
user-agent and standardized `B2_*` env vars — and no second API key is required
(AudioSR runs on-device, B2 credentials only).

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. Keep the reusable B2 scaffolding, adapt the dashboard,
add the enhancement pipeline. Backend keeps the strict `types → config → repo →
service → runtime` layering; no `boto3` outside `repo/`; files under 300 lines; every
new endpoint touches `runtime/<router>.py` + `lib/api-client.ts` + `lib/queries.ts`.

### KEEP (as-is — do not strip/rename/rebuild)
- **UI kit / design system**: `apps/web/src/components/ui/*`, tokens in `globals.css`,
  the `/design` page. Build new screens from these primitives; restyle via tokens only.
- **Bucket explorer (Files)** — **NON-NEGOTIABLE KEEP.** `/files` route,
  `apps/web/src/app/files/`, `apps/web/src/components/files/*`, and the Files sidebar
  entry. This is the full-bucket browse surface and is never removable.
- **Upload** — `/upload` route, `apps/web/src/app/upload/`,
  `apps/web/src/components/upload/*`, and the Upload sidebar entry. (Adapted only in
  target prefix + accepted types — see ADAPT. The route and sidebar entry stay.)
- **Settings** (`/settings`) and its `settings-form.tsx` — keep as the form-UX exemplar.
- Sidebar nav entries Dashboard, Upload, Files, Settings, Design System all stay.
- Backend infra: `main.py` app wiring, `runtime/health.py`, `runtime/metrics.py`,
  `runtime/ratelimit.py`, structured JSON logging, `/health` + `/metrics`, structural
  tests, the layered architecture and its enforcement tests.
- The B2 repo layer (`repo/b2_client.py`, `repo/b2_object.py`, `repo/counter.py`) —
  reused by the new job/library features (env-var rename applies, see §6).

### TRIM (remove / repurpose — this app doesn't need it)
- **Image/PDF metadata emphasis**: `service/metadata.py` keeps generic md5/sha256/size
  extraction (still useful in the file detail panel) but the image-EXIF / PDF-pages
  paths become dead weight for an audio app. Keep the module (checksums are still shown)
  but do **not** build new UI around image/PDF fields. `docs/features/metadata-extraction.md`
  is rewritten to describe the audio sidecar instead (see §5).
- **Recent-uploads / upload-chart defaults** on the dashboard are replaced (see ADAPT).
  Delete the illustrative "uploads today" framing in favor of enhancement metrics.

### ADD (new for `audiosr-batch`)
Backend (`services/api/app/`):
- `types/jobs.py` — Pydantic models: `JobStatus` enum (`queued|processing|completed|failed`),
  `EnhancementJob` (id, input_key, output_key, sidecar_key, collection, status, params,
  input_sample_rate, output_sample_rate, input_duration_sec, model_version,
  input_size_bytes, output_size_bytes, amplification_ratio, error, created_at,
  updated_at), `CreateJobRequest` (input_key, quality_preset, seed?), `EnhancementParams`
  (ddim_steps, guidance_scale, seed, model_name). Export via `types/__init__.py`.
- `repo/audiosr_engine.py` — the **AudioSR adapter** (the one external ML dependency,
  wrapped in `repo/` per the invariant). **Lazy-imports** `audiosr`/`torch`/`soundfile`
  *inside* the functions so API boot and the unit/structural tests never require the
  heavy stack. Exposes `enhance(input_path, output_path, params) -> EnhanceResult`
  (input_sr, output_sr=48000, input_duration_sec, model_version) and `probe(input_path)
  -> (sample_rate, duration_sec)`. Caches `build_model(...)` in a module-global so
  repeated jobs reuse the loaded model. **Device rule** (§4): honor `AUDIOSR_DEVICE`
  override, else `cuda` if `torch.cuda.is_available()` else `cpu`. **MPS is skipped by
  default** — AudioSR's latent-diffusion + torchlibrosa stack has known unsupported MPS
  ops; opt in only via `AUDIOSR_DEVICE=mps`. Raises a clear `EngineUnavailableError` when
  `audiosr` isn't importable (so the service can mark the job failed with an actionable
  message). Reference API (confirm against the installed package at build time):
  `from audiosr import build_model, super_resolution`;
  `model = build_model(model_name="basic", device=device)`;
  `wave = super_resolution(model, input_file, seed=seed, ddim_steps=ddim_steps,
  guidance_scale=guidance_scale, latent_t_per_second=12.8)`; squeeze `wave` to mono/2-D
  and write 48 kHz 16-bit PCM WAV with `soundfile.write(path, wave, 48000, subtype="PCM_16")`.
- `repo/job_store.py` — B2-backed job persistence (jobs are stored **in B2** as JSON
  manifests at `jobs/<job_id>.json`, keeping B2 the system of record). `save_job`,
  `load_job`, `list_jobs`, `delete_job` — implemented on the existing cached S3 client /
  `b2_object`/`b2_client` helpers so no new boto3 usage leaks outside `repo/`.
- `service/jobs.py` — orchestration: `create_job` (validate input_key exists under the
  originals prefix, map `quality_preset`→`EnhancementParams`, write a `queued` manifest,
  return it), `run_job` (the pipeline: set `processing`; download original via
  `get_object_bytes`; write to a temp file; call `audiosr_engine.enhance`; upload the
  enhanced WAV to `enhanced/<collection>/<name>.wav`; write the JSON sidecar to
  `enhanced/<collection>/<name>.json`; update manifest to `completed` with the computed
  fields; on any exception mark `failed` with the error string), `get_job`, `list_all_jobs`,
  `delete_job` (delete enhanced WAV + sidecar + manifest, scoped strictly to that job's
  keys), `get_enhancement_stats` (files enhanced, total original vs enhanced bytes,
  amplification ratio, avg input→output sample-rate, jobs-by-status), `get_enhancement_activity`
  (enhanced-output bytes/day for the chart). **Single-flight**: a module-level lock
  serializes enhancement runs (one AudioSR job at a time — the model is memory-heavy);
  extra runs queue behind the lock. Document the in-process/single-flight nature in
  RELIABILITY.md.
- `runtime/jobs.py` — routes (sync `def`, threadpool, HTTPException mapping like
  `runtime/files.py`):
  - `POST /jobs` (create; schedules `run_job` via FastAPI `BackgroundTasks`) — **create**
  - `GET /jobs` (list) + `GET /jobs/{id}` (detail) — **read**
  - `POST /jobs/{id}/run` (re-run a queued/failed/completed job) — **run**
  - `DELETE /jobs/{id}` — **delete**
  - `GET /jobs/stats` + `GET /jobs/stats/activity` — dashboard aggregations
  - `GET /library` (list originals joined to their enhanced renditions, scoped to the
    sample's `originals/` + `enhanced/` prefixes) — the scoped explorer's data source
  Register the router in `main.py`.
- `service/upload.py` adaptation: accepted types trimmed to audio only
  (`audio/mpeg`, `audio/wav`, `audio/ogg`, plus `audio/x-wav`); target key becomes
  `originals/<collection>/<safe_name>` (collection defaults to `default`, taken from an
  optional form field / query param). Keep the magic-byte + extension checks; add an OGG
  signature (`OggS`) and extension mapping. `max_file_size` raised to accommodate WAV
  (e.g. 200 MB) — set via settings, documented.

Frontend (`apps/web/src/`):
- `app/jobs/page.tsx` + `components/jobs/*` — **Enhancements** (the primary-entity
  surface): a jobs table (status badge, input, sample-rate in→out, amplification,
  created), a **New Enhancement** dialog (create form, §4), a **job detail** panel/dialog
  (status, params, input/output sample rate, duration, model version, byte sizes +
  amplification, **inline audio players** for original and enhanced via presigned preview
  URLs, the sidecar JSON, B2 keys), and **Run/Re-run** + **Delete** actions. Polls via
  TanStack Query `refetchInterval` while a job is `queued`/`processing`.
- `app/library/page.tsx` + `components/library/*` — **Audio Library**, the **mandatory
  sample-specific scoped explorer**: browse the sample's own audio (originals grouped by
  collection, each with its enhanced rendition if present), inline players for both,
  download buttons. Scoped to `originals/`+`enhanced/` only — distinct from the
  full-bucket `/files` explorer (which stays).
- `app/page.tsx` + `components/dashboard/*` — **adapt** the dashboard to enhancement
  metrics: stat cards = *Files enhanced*, *Storage amplification* (enhanced÷original
  bytes, the marquee metric), *Avg bandwidth gain* (in→out sample rate), *Jobs by status*;
  chart = enhanced-output volume per day (reuse the activity-chart shape); table = recent
  enhancements (replaces recent uploads).
- `lib/api-client.ts` + `lib/queries.ts` — add fetchers + hooks + query keys for jobs
  (list/detail/create/run/delete), library, enhancement stats/activity. All fetches go
  through TanStack Query (no bare `useEffect+fetch`). Invalidate `qk.all` after mutations.
- `components/layout/app-sidebar.tsx` — **add** nav entries **Enhancements** (`/jobs`,
  icon e.g. `Waves`/`AudioLines`) and **Library** (`/library`, icon `Library`/`Music`).
  All existing entries stay.
- `packages/shared/src/types.ts` — mirror the job/library/stats TS types.

**Note on the bucket-explorer tension:** none — the full-bucket `/files` explorer is
kept unchanged and complements the scoped Audio Library. No conflict.

## 3. B2 surface (S3-compatible only — Standard #1)

All via the S3 API on the shared `boto3` client with `user_agent_extra` set. **No
b2-native API anywhere.**
- `put_object` — enhanced WAV → `enhanced/<collection>/<name>.wav`; sidecar →
  `enhanced/<collection>/<name>.json`; job manifest → `jobs/<id>.json`; ingested
  originals → `originals/<collection>/<name>` (via `/upload`).
- `get_object` — download original for processing; read manifests; read sidecars.
- `head_object` — existence/metadata checks; `/health` connectivity.
- `list_objects_v2` — list originals/enhanced (Library), list jobs, dashboard stats
  (paginated).
- `delete_object` — delete a job's enhanced WAV + sidecar + manifest (scoped to that
  job's prefix only; never a bulk/shared wipe).
- `generate_presigned_url` — inline audio playback (preview) + downloads.

No b2-native calls. Justification section: **none required** (fully S3).

## 4. Key features

1. **Local audio super-resolution with AudioSR** — the marquee. versatile_audio_super_resolution
   upscales degraded audio to 48 kHz, reconstructing high-frequency content.
2. **Batch enhancement jobs** — the primary entity; create → run → track → delete, with
   status polling and per-job provenance.
3. **Write-amplification storytelling** — dashboard surfaces the original→enhanced byte
   expansion (the "1 TB → 5–10 TB" story) as a live metric.
4. **Per-file JSON sidecar** — input/output sample rate, model version, duration written
   next to each enhanced file in B2.
5. **Audio Library** — scoped explorer pairing each original with its enhanced rendition,
   both playable inline.
6. **B2 as the whole storage layer** — originals, enhanced renditions, sidecars, and job
   manifests all live in B2 via the S3 API; job state is durable in B2.

### External API provider (per-feature `deployment` field)
- **Feature: Audio super-resolution (AudioSR)** — `deployment: **local**`.
  Provider/model: **versatile_audio_super_resolution (`audiosr`, model "basic")**, run
  on-device. This is the sample's whole point and an on-device capability
  (api-provider-selection Step 2, rule 1 → LOCAL default). **Estimated cost for one full
  demo run: $0** (no external API, no key). **Env var for a key: none** — B2 credentials
  only. **Device**: CPU default, GPU autodetect **CUDA → CPU** (MPS skipped by default —
  known unsupported diffusion/torchlibrosa ops on MPS; opt-in via `AUDIOSR_DEVICE=mps`);
  never hard-requires a GPU. No other feature needs an external API.

### Genblaze orchestration
Not applicable — the description's Trending OSS is versatile_audio_super_resolution and
makes no mention of Genblaze / `genblaze-*` / `genblaze-s3`. AI calls are the local
AudioSR engine wrapped in `repo/audiosr_engine.py`; no Genblaze SDK.

### Primary-entity lifecycle (single entity: **Enhancement Job**)
- **create** — ✅ built. "New Enhancement" form.
- **read** — ✅ built. Jobs list + job detail.
- **run** — ✅ built. `POST /jobs/{id}/run` + a Run/Re-run action (also auto-scheduled on
  create). This is the marquee verb (runs AudioSR).
- **delete** — ✅ built. Removes the job's enhanced WAV + sidecar + manifest (scoped).
- **edit** — **OMITTED (UX-justified).** An enhancement job is an immutable record of one
  processing run (input file + params → output artifact). There is nothing to edit after
  the fact: changing parameters means producing a *different* output, which the user does
  by creating a new job or re-running. An edit form would either be a no-op or would
  silently invalidate the stored artifact/sidecar. → record in `omitted_ui_verbs`
  (`entity: "Enhancement Job", operation: "edit"`).

### Form UX conventions
- **Create form (New Enhancement)** — fields:
  - `inputKey` — finite set (the originals currently in B2) → **Select** dropdown. ✔ selector.
  - `qualityPreset` — finite set → **Select**: *Fast* (ddim_steps=25), *Balanced*
    (ddim_steps=50, default), *High* (ddim_steps=100). ✔ selector. Maps to
    `EnhancementParams` server-side; `guidance_scale=3.5` fixed.
  - `seed` — optional integer `Input`; placeholder `42` with FormDescription "leave blank
    for random". Guidance only, no autofill button.
  - Default hints (placeholder / FormDescription, not autofill): recommend selecting a
    **short clip (a few seconds)** for a fast first run; preset defaults to *Balanced*.
  - `collection` derived from the chosen input key's prefix — not a separate free-text field.
- **Edit form** — omitted (see above), so no edit selectors needed.
- Follow `settings-form.tsx` (react-hook-form + zod + shadcn `Select`/`FormDescription`).

## 5. Doc transforms

- `README.md` — rewrite intro, features, quick-start (new env vars §6, `audiosr` install
  note + first-run model download ~2 GB from HuggingFace, CPU/GPU note, short-clip demo
  tip), tech stack (+ AudioSR/torch/soundfile), commands unchanged.
- `AGENTS.md` — update repo map (new routers/services/repo modules + `/jobs`,`/library`),
  the app name, and the "building on this starter kit" framing to describe the built app.
- `ARCHITECTURE.md` — add the enhancement data flow (ingest → job manifest → AudioSR →
  enhanced WAV + sidecar → B2), the new layer files, and the single-flight runner.
- `docs/features/` — **rewrite** `dashboard.md` (enhancement metrics), `file-upload.md`
  (→ audio ingest, `originals/` prefix, audio types). **Rewrite** `metadata-extraction.md`
  → describe the **audio sidecar** (sample rates, duration, model version) plus the
  retained generic checksums. `file-browser.md` kept (full-bucket explorer) with a note
  it coexists with the Library. **New stubs**: `audio-enhancement.md` (the AudioSR run +
  device rule), `enhancement-jobs.md` (primary-entity lifecycle + omitted-edit rationale),
  `audio-library.md` (scoped explorer).
- `docs/SECURITY.md` / `docs/RELIABILITY.md` — add: single-flight in-process job runner
  (state durable in B2, but in-flight status is per-replica; horizontal scaling needs a
  shared queue), larger upload ceiling, unauthenticated single-tenant stance retained.
- `docs/app-workflows.md` / `docs/dev-workflows.md` — add the ingest→enhance→serve journey
  and how to run/test the pipeline (short-clip smoke test, torch-less test path).
- Move this plan to `docs/exec-plans/completed/initial-scaffold.md` on PASS (Phase 5).

## 6. Rename table

| From (starter kit) | To (`audiosr-batch`) | Where |
|---|---|---|
| `vibe-coding-starter-kit` | `audiosr-batch` | root `package.json` name, README, docs, image/workflow slugs |
| `@vibe-coding-starter-kit/web` | `@audiosr-batch/web` | `apps/web/package.json`, root scripts (`--filter`), lockfile |
| `@vibe-coding-starter-kit/shared` | `@audiosr-batch/shared` | `packages/shared/package.json`, every import specifier (queries.ts, api-client.ts, components) + `apps/web/package.json` dep |
| `OSS Starter Kit` (`APP_NAME`) | `AudioSR Batch` | `apps/web/src/lib/app-config.ts` |
| `File management dashboard powered by Backblaze B2` (`APP_DESCRIPTION`) | `Batch audio super-resolution pipeline powered by Backblaze B2` | `app-config.ts` |
| `OSS Starter Kit API` (FastAPI `title`) | `AudioSR Batch API` | `services/api/main.py` |
| FastAPI `description` | `Batch audio super-resolution pipeline backed by Backblaze B2` | `main.py` |
| `b2ai-oss-start` (`user_agent_extra`) | `b2ai-audiosr-batch` | `repo/b2_client.py` (Standard #2) |
| `utm_content=b2ai-oss-start` | `utm_content=b2ai-audiosr-batch` | README, `app-sidebar.tsx`, `scripts/doctor.mjs` UTM links |
| **Env `B2_KEY_ID`** | **`B2_APPLICATION_KEY_ID`** | Standard #3 — `.env.example`, `settings.py` (`b2_key_id`→`b2_application_key_id`), `main.py` REQUIRED/PLACEHOLDER, `b2_client.py`, README, `doctor.mjs`, docs |
| **Env `B2_ENDPOINT`** | **`B2_REGION`** (derive endpoint `https://s3.{B2_REGION}.backblazeb2.com`) | Standard #3 — `settings.py` (`b2_endpoint`→`b2_region` + an `endpoint` property), `main.py` REQUIRED/PLACEHOLDER, `b2_client.py` (`endpoint_url=settings.endpoint`), `.env.example`, README, `doctor.mjs`, docs |
| **Env `b2_public_url` / (unset)** | **`B2_PUBLIC_URL_BASE`** (optional) | Standard #3 — `settings.py` (`b2_public_url`→`b2_public_url_base`), `b2_client._public_url`, `.env.example` |
| `B2_APPLICATION_KEY`, `B2_BUCKET_NAME` | unchanged | already Standard #3 |

Notes:
- **Env rename is the top correctness item** — `/b2-doctor` audits Standard #3 names. Keep
  `B2_PUBLIC_URL_BASE` optional (do not add it to the required-startup gate).
- Lockfile: prefer regenerating (`pnpm install`) after renaming package names; if offline,
  do a targeted find/replace of the three package-name strings in `pnpm-lock.yaml`.
- Grep the whole tree for `vibe-coding-starter-kit`, `oss-starter-kit`, `OSS Starter Kit`,
  and `b2ai-oss-start` and confirm zero residual references (except historical
  `docs/exec-plans/completed/*` from the starter, which may be pruned).
