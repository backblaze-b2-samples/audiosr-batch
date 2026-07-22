<!-- last_verified: 2026-07-22 -->
# Feature: Metadata Extraction (audio sidecar + checksums)

## Purpose
Capture provenance for every enhanced file. The primary artifact is the
**per-file JSON sidecar** written next to each enhanced WAV, describing the run
(sample rates, duration, model version, params, byte sizes, amplification). A
generic checksum/size extractor is also retained for the full-bucket File
Browser's detail panel.

## Used By
- Enhancement pipeline: `service/jobs.py::run_job` writes the sidecar to `enhanced/<collection>/<name>.json`
- API: `GET /files-by-key/detail?key=…` — recomputes generic `FileMetadataDetail` on demand for any stored object (used by the Files browser)
- UI: the Files preview dialog renders generic detail via `FileMetadataPanel`

## The audio sidecar
Written alongside each enhanced rendition by `service/jobs.py::_write_sidecar`:

| Field | Meaning |
|-------|---------|
| `job_id`, `input_key`, `output_key`, `collection` | provenance / linkage |
| `input_sample_rate`, `output_sample_rate` | e.g. 16000 → 48000 |
| `input_duration_sec` | source duration |
| `model_name`, `model_version`, `device_used` | which model ran, where |
| `ddim_steps`, `guidance_scale`, `seed` | reproducibility |
| `input_size_bytes`, `output_size_bytes`, `amplification_ratio` | the write-amplification story |
| `created_at`, `completed_at` | timing |

The same fields (bar the raw sidecar) are mirrored onto the `EnhancementJob`
manifest so the UI can render them without a second fetch.

## Generic checksums (retained)
- `services/api/app/service/metadata.py` — `extract_metadata()` computes md5/sha256/size and (for image/PDF objects that may exist in the bucket) dimensions/pages. The audio app doesn't build new UI around the image/PDF fields, but the module stays because the Files browser's "Detailed metadata" disclosure recomputes it on demand for any object.

## Canonical Files
- Sidecar writer: `services/api/app/service/jobs.py::_write_sidecar`
- Generic extractor: `services/api/app/service/metadata.py`

## Inputs
- Sidecar: the completed `EnhancementJob` + computed byte sizes
- Generic: file_data bytes, filename, content_type

## Outputs
- Sidecar JSON object at `enhanced/<collection>/<name>.json`
- `FileMetadataDetail` (generic checksums + optional image/PDF fields) from `/files-by-key/detail`

## Edge Cases
- Non-image/non-PDF object in the generic path → only common fields (hashes, size, extension)
- Sidecar write failure → surfaced as a job failure (the enhanced WAV + sidecar are written in the same `run_job` step)

## Verification
- Test files: `services/api/tests/test_jobs.py` (asserts the sidecar object is written), `services/api/tests/test_file_detail.py` (generic detail)
- Quick verify command: `pnpm test:api`
- Pass criteria: sidecar written on completion; generic detail tests green

## Related Docs
- [Enhancement Jobs](enhancement-jobs.md)
- [Audio Ingest (Upload)](file-upload.md)
