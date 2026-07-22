<!-- last_verified: 2026-07-22 -->
# Feature: Audio Ingest (Upload)

## Purpose
Ingest low-quality audio from the browser into Backblaze B2 under
`originals/<collection>/`, ready to be super-resolved.

## Used By
- UI: `/upload` page, upload form component
- API: `POST /upload` (multipart, with an optional `collection` form field)

## Core Functions
- `apps/web/src/components/upload/upload-form.tsx` — dropzone + progress + collection field
- `apps/web/src/components/upload/dropzone.tsx` — drag-and-drop via `react-dropzone` (audio types, 200 MB)
- `apps/web/src/lib/upload-file-types.ts` — client allow-list (mirrors the backend)
- `apps/web/src/lib/api-client.ts` — `uploadFile()` (XHR for progress; sends `collection`)
- `services/api/app/runtime/upload.py` — HTTP handler
- `services/api/app/service/upload.py` — validation + `originals/<collection>/<name>` keying
- `services/api/app/repo/b2_client.py` — `upload_file()` via boto3 `put_object`

## Canonical Files
- Upload handler: `services/api/app/runtime/upload.py`
- Service orchestration: `services/api/app/service/upload.py`

## Inputs
- file: `File` (multipart) — audio only
- collection: string (optional form field; defaults to `default`)

## Outputs
- `FileUploadResponse`: key, filename, size, content_type, uploaded_at, url, metadata
- Side effect: object stored at `originals/<collection>/<sanitized_filename>`

## Accepted types
Audio only: `audio/mpeg` (mp3), `audio/wav`, `audio/x-wav` (wav), `audio/ogg` (ogg/oga).
Everything else is rejected at the boundary. Each type has a magic-byte signature
(`ID3`/MPEG frame sync, `RIFF…WAVE`, `OggS`) that the server verifies.

## Flow
- User picks a collection and drops/selects audio in the dropzone
- Client validates size (max 200 MB) and type; rejected files stay in the queue with a reason
- XHR POSTs multipart to `/upload` with progress events
- API checks `Content-Length` early, validates the type allow-list, sanitizes the filename and the collection (single safe path segment, no traversal), enforces the size limit while streaming, rejects empty files, and verifies the magic-byte signature
- API writes to `originals/<collection>/<safe_name>` via `put_object`, extracts generic metadata (checksums), and returns `FileUploadResponse`

## Edge Cases
- File > 200 MB → client-rejected row + toast; API returns 413 if bypassed
- Non-audio type → API returns 415
- Extension/type mismatch or spoofed bytes → API returns 415
- Empty file / no filename → API returns 400
- Unsafe collection (e.g. `../`) → sanitized to a single safe segment; never escapes `originals/`
- Duplicate name → B2 versions it (buckets are always versioned)

## UX States
- Empty: dropzone with audio-only + 200 MB hint and a Collection field
- Loading / Error / Complete / Rejected: per-file progress, retry where applicable

## Verification
- Test files: `services/api/tests/test_upload_validation.py`, `test_upload_conflict.py`, `test_error_handling.py`
- Required cases: successful audio upload, oversized (413), disallowed type (415), extension mismatch (415), signature mismatch (415), empty file (400), collection routing + sanitization
- Quick verify command: `pnpm test:api`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [Enhancement Jobs](enhancement-jobs.md)
- [Metadata Extraction](metadata-extraction.md)
- [App Workflows](../app-workflows.md)
