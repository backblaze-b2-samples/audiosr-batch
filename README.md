<!-- last_verified: 2026-07-22 -->
# AudioSR Batch

Batch **audio super-resolution** on [Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-audiosr-batch). Ingest large libraries of degraded audio — 8–22 kHz call recordings, legacy field tapes, low-bitrate music — run the open-source [`versatile_audio_super_resolution`](https://github.com/haoheliu/versatile_audio_super_resolution) (AudioSR) model **locally** to reconstruct missing high-frequency content, and write a full-quality **48 kHz WAV** rendition plus a JSON metadata sidecar back to B2 alongside the original.

It's a concrete demonstration of **write amplification at scale**: every compressed original expands into a full-quality WAV (typically 5–10× larger) plus a sidecar, so a 1 TB archive can become 5–10 TB in B2. **B2 is the single storage layer** — accessed via the S3-compatible API with a custom user-agent and standardized `B2_*` env vars. No second API key is required: AudioSR runs on-device, so only B2 credentials are needed.

**What it does:**
- Ingest audio (MP3 / WAV / OGG) into B2 under `originals/<collection>/`
- Run AudioSR super-resolution jobs — create → run → track → delete, with live status
- Write the enhanced 48 kHz WAV + a JSON sidecar to `enhanced/<collection>/`
- Surface the **storage-amplification** story (original → enhanced bytes) as a live dashboard metric
- Pair each original with its enhanced rendition in a scoped **Audio Library**, both playable inline

## Architecture at a glance

- **apps/web/** — Next.js 16 + React 19 + Tailwind v4 + shadcn/ui dashboard
- **services/api/** — FastAPI backend, strict layered architecture (`types → config → repo → service → runtime`)
- **packages/shared/** — shared TypeScript types mirroring the Pydantic models
- **Backblaze B2** — originals, enhanced renditions, JSON sidecars, and job manifests all live here (no application database)

The AudioSR model is wrapped in `services/api/app/repo/audiosr_engine.py` and lazy-imported, so the API boots and the test suite run without the heavy ML stack installed.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free **[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-audiosr-batch)**.

### 1. Install dependencies

```bash
pnpm install
```

### 2. Set up the backend

```bash
cd services/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Heavy ML stack for actually running enhancements (torch + AudioSR). It is
# SEPARATE so the app boots and tests run without it. Install it when you want
# to run the pipeline:
pip install -r requirements-ml.txt
cd ../..
```

> The first enhancement run downloads the ~2 GB AudioSR "basic" checkpoint once
> from the public HuggingFace hub (keyless), then caches it. CPU works for a
> short clip; the engine auto-detects **CUDA → CPU** at runtime and defaults to
> CPU (Apple MPS is skipped by default — set `AUDIOSR_DEVICE=mps` to opt in). No
> GPU is ever required.

### 3. Add your B2 credentials

```bash
cp .env.example .env
```

Open `.env`, then head to the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-audiosr-batch) and:

1. **Create a bucket.** Note its **Endpoint** — the region slug in it goes to `B2_REGION` (an endpoint of `s3.us-west-004.backblazeb2.com` → `B2_REGION=us-west-004`). The bucket's unique name goes to `B2_BUCKET_NAME`.
2. **Create an application key** with `Read and Write` permission:
   - **keyID** → `B2_APPLICATION_KEY_ID`
   - **applicationKey** → `B2_APPLICATION_KEY` *(only shown once — paste it now)*

`B2_PUBLIC_URL_BASE` is optional (public buckets only); the app serves audio via short-lived presigned URLs regardless.

### 4. Run it

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Upload a **short** audio clip on the Upload page, then create an enhancement on the Enhancements page and watch it run. Interactive API docs (Swagger UI) are at `localhost:8000/docs`.

`pnpm dev` runs `pnpm doctor` first — a preflight check for the common setup gotchas (wrong Node/Python version, missing venv, missing or placeholder `.env`, busy ports).

## Core Features

- [Audio Enhancement](docs/features/audio-enhancement.md) — the AudioSR super-resolution run + device rule
- [Enhancement Jobs](docs/features/enhancement-jobs.md) — the primary entity: create → run → track → delete
- [Audio Library](docs/features/audio-library.md) — scoped explorer pairing each original with its enhanced rendition
- [Dashboard](docs/features/dashboard.md) — files enhanced, storage amplification, bandwidth gain, jobs by status
- [Audio Ingest (Upload)](docs/features/file-upload.md) — drag-and-drop audio upload into `originals/`
- [File Browser](docs/features/file-browser.md) — full-bucket explorer (coexists with the scoped Library)
- [Metadata Extraction](docs/features/metadata-extraction.md) — audio sidecar (sample rates, duration, model) + generic checksums
- [Design System](docs/design-system.md) — tokens, primitives, error/empty states. Live preview at `/design`.

Also included: inline error handling, single-source `.env` config validated at startup, a centralized TanStack Query data layer, structural tests, structured JSON logging, `/health` and `/metrics` endpoints, per-IP rate limiting, and magic-byte upload validation — see [SECURITY.md](docs/SECURITY.md).

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, Recharts
- TanStack Query — caching, dedup, retry, stale-while-revalidate for every fetch
- Python 3.11+, FastAPI, boto3, Pydantic v2
- **AudioSR** (`versatile_audio_super_resolution`), PyTorch, soundfile — local, on-device audio super-resolution
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:web` | Run frontend unit tests (vitest) |
| `pnpm test:api` | Run backend tests |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright e2e tests (run `pnpm --filter @audiosr-batch/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (enhancement, jobs, library, dashboard, ingest, browser, metadata) |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Claude Agent B2 Skill

Manage Backblaze B2 from your terminal using natural language (list/search, audits, stale or large file detection, security checks, safe cleanup).

Repo: [https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage](https://github.com/backblaze-b2-samples/claude-skill-b2-cloud-storage)
