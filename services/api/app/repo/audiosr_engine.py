"""AudioSR adapter — the one external ML dependency, contained in repo/.

Wraps the open-source `versatile_audio_super_resolution` package (`audiosr`,
model "basic"), which runs entirely on-device (no API key). Everything heavy —
`audiosr`, `torch`, `soundfile`, `numpy` — is imported *inside* the functions,
never at module import time, so:

  * `from main import app` and the unit/structural test suite never require the
    ML stack (see requirements-ml.txt — it is intentionally NOT in the base
    requirements.txt), and
  * the API process boots torch-free.

The model is cached in a module global so repeated jobs reuse the loaded weights
(the first `build_model` call downloads the ~2 GB "basic" checkpoint from the
public HuggingFace hub once, then caches it locally).
"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# The model always writes 48 kHz output — that is the whole point of the sample.
OUTPUT_SAMPLE_RATE = 48000

# (model_name, device) -> loaded latent-diffusion model. Module-global so a
# long-lived worker reuses the loaded weights across jobs.
_model_cache: dict[tuple[str, str], object] = {}


class EngineUnavailableError(RuntimeError):
    """Raised when the `audiosr` stack isn't importable.

    Lets the service mark a job `failed` with an actionable message instead of
    surfacing an opaque ImportError, e.g. when someone runs the API without
    having installed requirements-ml.txt.
    """


@dataclass(frozen=True)
class EnhanceResult:
    input_sample_rate: int
    output_sample_rate: int
    input_duration_sec: float
    model_version: str
    device_used: str


def _audiosr_version() -> str:
    try:
        from importlib.metadata import version

        return version("audiosr")
    except Exception:
        return "unknown"


def select_device() -> str:
    """Pick the compute device: AUDIOSR_DEVICE override, else CUDA, else CPU.

    MPS is deliberately skipped by default: AudioSR's latent-diffusion +
    torchlibrosa ops have known-unsupported paths on Apple MPS, so we fall back
    CUDA → CPU (never hard-require a GPU). Opt into MPS explicitly with
    AUDIOSR_DEVICE=mps.
    """
    override = os.environ.get("AUDIOSR_DEVICE", "").strip().lower()
    if override:
        return override
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except EngineUnavailableError:
        raise
    except Exception:
        # torch not importable yet — default to CPU; the real import error will
        # surface (as EngineUnavailableError) when enhance() actually runs.
        return "cpu"
    return "cpu"


def _require_audiosr():
    try:
        from audiosr import build_model, super_resolution
    except Exception as e:  # ImportError or a broken transitive import
        raise EngineUnavailableError(
            "AudioSR is not installed. Install the ML stack with "
            "`pip install -r requirements-ml.txt` in services/api. "
            f"(underlying error: {e})"
        ) from e
    return build_model, super_resolution


def _get_model(model_name: str, device: str):
    key = (model_name, device)
    cached = _model_cache.get(key)
    if cached is not None:
        return cached
    build_model, _ = _require_audiosr()
    logger.info("Loading AudioSR model '%s' onto %s (first run downloads ~2GB)", model_name, device)
    model = build_model(model_name=model_name, device=device)
    _model_cache[key] = model
    return model


def probe(input_path: str) -> tuple[int, float]:
    """Return (sample_rate, duration_seconds) for the input audio.

    Tries libsndfile via soundfile first (fast, no decode); falls back to
    librosa for formats libsndfile can't open (e.g. some MP3 builds). Both are
    part of the AudioSR ML stack, so this only runs on the enhancement path.
    """
    try:
        import soundfile as sf

        info = sf.info(input_path)
        if info.samplerate and info.frames:
            return int(info.samplerate), float(info.frames) / float(info.samplerate)
    except Exception:
        logger.debug("soundfile.info failed for %s, falling back to librosa", input_path)
    try:
        import librosa

        duration = float(librosa.get_duration(path=input_path))
        sr = int(librosa.get_samplerate(input_path))
        return sr, duration
    except Exception as e:
        raise EngineUnavailableError(
            f"Could not read audio metadata for '{input_path}': {e}"
        ) from e


def enhance(
    input_path: str,
    output_path: str,
    *,
    ddim_steps: int = 50,
    guidance_scale: float = 3.5,
    seed: int = 42,
    model_name: str = "basic",
    latent_t_per_second: float = 12.8,
) -> EnhanceResult:
    """Super-resolve `input_path` to a 48 kHz WAV at `output_path`.

    Runs the real AudioSR model on-device (CUDA → CPU auto-detect; MPS opt-in).
    Raises EngineUnavailableError if the ML stack isn't importable.
    """
    # Check the heavy stack FIRST so a missing install surfaces as an actionable
    # EngineUnavailableError rather than a raw numpy/soundfile ImportError.
    _, super_resolution = _require_audiosr()
    import numpy as np
    import soundfile as sf

    device = select_device()
    input_sr, input_duration = probe(input_path)

    model = _get_model(model_name, device)
    logger.info(
        "Enhancing %s (sr=%d, %.2fs) with ddim_steps=%d guidance=%.1f seed=%d on %s",
        input_path, input_sr, input_duration, ddim_steps, guidance_scale, seed, device,
    )
    waveform = super_resolution(
        model,
        input_path,
        seed=seed,
        guidance_scale=guidance_scale,
        ddim_steps=ddim_steps,
        latent_t_per_second=latent_t_per_second,
    )
    # AudioSR returns a numpy array shaped (batch, channels, samples); collapse
    # to a 1-D mono track and clamp to [-1, 1] so PCM_16 encoding is safe.
    wave = np.asarray(waveform, dtype=np.float32)
    wave = np.squeeze(wave)
    if wave.ndim > 1:
        # Keep the first channel if a stray channel dim survives the squeeze.
        wave = wave[0] if wave.shape[0] < wave.shape[-1] else wave[:, 0]
    wave = np.clip(wave, -1.0, 1.0)

    sf.write(output_path, wave, OUTPUT_SAMPLE_RATE, subtype="PCM_16")

    return EnhanceResult(
        input_sample_rate=input_sr,
        output_sample_rate=OUTPUT_SAMPLE_RATE,
        input_duration_sec=round(input_duration, 3),
        model_version=f"audiosr {_audiosr_version()} ({model_name})",
        device_used=device,
    )
