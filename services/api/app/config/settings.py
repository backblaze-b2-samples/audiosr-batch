from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # B2 / S3 credentials. Empty defaults so `Settings()` (and test collection)
    # never raises; main.py fails fast at startup if any are still unset.
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    # Region slug (e.g. "us-west-004"). The S3 endpoint is derived from it — see
    # the `endpoint` property. No region literal is hardcoded anywhere in source.
    b2_region: str = ""
    # Optional public base URL for building public object URLs (public buckets
    # only). The app runs fine without it (audio is served via presigned URLs).
    b2_public_url_base: str = ""

    # Compute device for the AudioSR engine. Empty = auto-detect (CUDA → CPU;
    # MPS opt-in only). See repo/audiosr_engine.py.
    audiosr_device: str = ""

    # B2 key prefixes owned by this app. Ingested originals and enhanced
    # renditions/sidecars live under these; job manifests under jobs/.
    originals_prefix: str = "originals/"
    enhanced_prefix: str = "enhanced/"
    jobs_prefix: str = "jobs/"

    api_port: int = 8000
    # Interactive API docs (/docs, /redoc, /openapi.json). On by default for
    # local dev and exploration; set false to hide the full API surface in
    # production.
    enable_docs: bool = True
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits. Raised well above the starter default because a full-quality
    # 48 kHz WAV rendition (and some legacy source tapes) can be large.
    max_file_size: int = 200 * 1024 * 1024  # 200MB

    # Optional confinement for key-addressed reads/deletes. Empty by default so
    # the by-key routes accept any key shape (they deliberately support nested
    # folders and reserved-word segments). Point a fork at a bucket shared with
    # other data? Set to e.g. "originals/" to restrict all key ops to app data.
    allowed_key_prefix: str = ""

    # Rate limiting (per client IP, per 60s window). In-process per replica —
    # documented in docs/RELIABILITY.md; horizontal scaling needs a shared
    # store (e.g. Redis). Writes/downloads get the tighter cap.
    rate_limit_per_minute: int = 120
    # Covers uploads, deletes, downloads and previews — kept generous enough
    # that a normal browsing/upload session doesn't trip it.
    rate_limit_write_per_minute: int = 60

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def endpoint(self) -> str:
        """Derive the S3 endpoint URL from the region slug.

        Kept as a property (not a stored setting) so there is a single source
        of truth and no region literal is committed to source.
        """
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def cors_origins(self) -> list[str]:
        # Drop empties so a trailing comma or API_CORS_ORIGINS="" doesn't yield
        # a stray "" origin.
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


settings = Settings()
