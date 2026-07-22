"""Guards for the AudioSR adapter that run WITHOUT the heavy ML stack installed.

These never import torch/audiosr — they exercise the device-selection logic and
the actionable-error path so the base test suite stays fast and torch-free
(the ML stack lives in requirements-ml.txt).
"""

import pytest

from app.repo import audiosr_engine
from app.repo.audiosr_engine import EngineUnavailableError, select_device


def test_device_override_honored(monkeypatch):
    monkeypatch.setenv("AUDIOSR_DEVICE", "cpu")
    assert select_device() == "cpu"
    monkeypatch.setenv("AUDIOSR_DEVICE", "mps")
    assert select_device() == "mps"


def test_device_defaults_to_cpu_without_torch(monkeypatch):
    # No override, and torch isn't installed in the base env → CPU (never a hard
    # GPU requirement). If torch *is* present and no CUDA, this is still cpu.
    monkeypatch.delenv("AUDIOSR_DEVICE", raising=False)
    assert select_device() in ("cpu", "cuda")


def test_enhance_raises_actionable_error_without_stack(monkeypatch, tmp_path):
    """Without audiosr installed, enhance() surfaces EngineUnavailableError so the
    service can mark the job failed with a fix hint rather than a raw ImportError."""
    monkeypatch.delenv("AUDIOSR_DEVICE", raising=False)
    src = tmp_path / "in.wav"
    src.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    out = tmp_path / "out.wav"
    try:
        import audiosr  # noqa: F401
    except Exception:
        with pytest.raises(EngineUnavailableError):
            audiosr_engine.enhance(str(src), str(out))
    else:
        pytest.skip("audiosr is installed; skipping the missing-stack guard")
