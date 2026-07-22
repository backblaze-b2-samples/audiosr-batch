<!-- last_verified: 2026-07-22 -->
# Feature: Audio Enhancement (AudioSR)

## Purpose
Reconstruct missing high-frequency content in degraded audio, upscaling it to a
full-quality 48 kHz WAV using the local `versatile_audio_super_resolution`
(AudioSR) model. This is the sample's marquee capability and runs entirely
on-device — no external API, no second key.

## Used By
- Service: `service/jobs.py::run_job` (invokes the engine during a job)
- API: indirectly via `POST /jobs` / `POST /jobs/{id}/run`

## Core Functions
- `services/api/app/repo/audiosr_engine.py`
  - `enhance(input_path, output_path, *, ddim_steps, guidance_scale, seed, model_name)` → `EnhanceResult`
  - `probe(input_path)` → `(sample_rate, duration_sec)`
  - `select_device()` → `"cuda" | "cpu" | <override>`
  - `EngineUnavailableError` (raised when the ML stack isn't importable)

## Canonical Files
- Engine adapter: `services/api/app/repo/audiosr_engine.py`

## Inputs
- input_path: str (a temp file holding the downloaded original)
- ddim_steps: int (25 / 50 / 100 from the Fast / Balanced / High preset)
- guidance_scale: float (fixed 3.5)
- seed: int (from the request, or a recorded random seed)
- model_name: str ("basic")

## Outputs
- A 48 kHz, 16-bit PCM WAV written to `output_path`
- `EnhanceResult`: input_sample_rate, output_sample_rate (48000), input_duration_sec, model_version, device_used

## Flow
- `run_job` downloads the original from B2 to a temp file
- `enhance()` checks the ML stack (`EngineUnavailableError` if missing), then
  imports `numpy`/`soundfile` and loads (or reuses a cached) AudioSR model on the
  selected device
- `super_resolution(model, input_file, seed, guidance_scale, ddim_steps, latent_t_per_second=12.8)`
  returns a waveform; it's squeezed to mono, clamped to [-1, 1], and written as
  48 kHz PCM_16 WAV
- The loaded model is cached in a module global keyed by `(model_name, device)`
  so repeated jobs reuse the weights

## Device rule (deployment: local)
- Honors `AUDIOSR_DEVICE` if set; else auto-detects **CUDA → CPU** and defaults to CPU.
- **Apple MPS is skipped by default** — AudioSR's latent-diffusion / torchlibrosa
  ops have known-unsupported MPS paths — so the fallback is CUDA → CPU. Opt in
  explicitly with `AUDIOSR_DEVICE=mps`.
- A GPU is never required.

## Edge Cases
- ML stack not installed (`requirements-ml.txt`) → `EngineUnavailableError` with an actionable message; the job is marked `failed`
- Unreadable / unsupported input → error recorded on the job; nothing written to `enhanced/`
- First run downloads the ~2 GB "basic" checkpoint from HuggingFace (keyless), then caches it

## Verification
- Test files: `services/api/tests/test_audiosr_engine.py` (device override, CPU default without torch, missing-stack error)
- Required cases: `AUDIOSR_DEVICE` honored, CPU default, `EngineUnavailableError` when the stack is absent
- Quick verify command: `pnpm test:api`
- Manual end-to-end: install `requirements-ml.txt`, upload a short clip, run an enhancement, confirm a 48 kHz WAV lands in `enhanced/`
- Pass criteria: engine tests green without the ML stack; a real short-clip run produces a 48 kHz WAV + sidecar in B2

## Related Docs
- [Enhancement Jobs](enhancement-jobs.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
