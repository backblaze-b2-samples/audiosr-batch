<!-- last_verified: 2026-06-25 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients
- Uncaught exceptions are converted to a typed JSON 500 (`{"detail": "Internal server error"}`, modeled by `app.types.ErrorResponse`) by the catch-all in `timing_middleware`
- **Error responses carry CORS headers.** `CORSMiddleware` is registered LAST in `main.py` so it is the outermost middleware and wraps every response — including uncaught-exception 500s produced by the inner catch-all. This is intentional and load-bearing: if a 500 shipped without `Access-Control-Allow-Origin`, the browser would block it and the frontend would surface only an opaque "network error", hiding the real server bug. Regression-guarded by `tests/test_error_handling.py::test_unhandled_exception_500_carries_cors_headers`.

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Stateful Counters — durability caveats

The download counter and the `/metrics` counters are **in-process, per replica**. Consequences to plan for before scaling:

- **Download counter** (`app/repo/counter.py`) persists to a JSON file at `DOWNLOAD_COUNT_FILE` (default `data/download_count.json`). On an ephemeral filesystem (Railway without a mounted volume) it **resets to 0 on every redeploy**. With multiple replicas each keeps its own file/count. For durable, shared counts: mount a persistent volume, or swap the adapter for Redis/DB.
- **`/metrics` counters** live in process memory and reset on restart. Behind a load balancer, each replica reports only its own slice — scrape with an instance label and aggregate, or push to a shared collector.

## Enhancement Job Runner

- **State is durable in B2.** Every job is a JSON manifest at `jobs/<id>.json`; enhanced renditions and sidecars are objects in the bucket. There is no application database, so job history survives an API restart.
- **Single-flight, in-process.** AudioSR is memory-heavy, so a module-level lock in `service/jobs.py` serialises real enhancement runs — one job executes at a time and extra runs queue behind the lock. The run itself is a FastAPI `BackgroundTask`, so the create/re-run request returns immediately with a `queued` job and the UI polls for status.
- **In-flight status is per-replica.** The `queued`/`processing` transition and the single-flight lock live in one process. Behind a load balancer with multiple replicas, each replica has its own lock and could run a job concurrently, and a replica restart mid-run leaves a job stuck in `processing` (re-run it). For real horizontal scaling, move to a shared queue/worker (e.g. Redis/Celery) and a shared lock. Durable *state* is already in B2; only the in-flight coordination is per-replica.

## Uploads

- The upload size ceiling is **200 MB** (`MAX_FILE_SIZE`), raised above the starter default because full-quality 48 kHz WAVs and some legacy source tapes are large. Enforced while streaming, so an oversized body is rejected before it's buffered.

## Rate Limiting

- Per-IP fixed-window limiter (`app/runtime/ratelimit.py`); `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_WRITE_PER_MINUTE` are the budgets. Rejected requests get `429` with a `Retry-After` header.
- Counters are in-process per replica; horizontal scaling needs a shared store (e.g. Redis) for a global limit.

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
