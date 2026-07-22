"""Tests for the scoped Audio Library (originals paired with enhanced renditions)."""

from datetime import UTC, datetime

from app.service import library as library_service
from app.types import FileMetadata


def _fm(key: str, size: int) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.split("/")[-1],
        folder=key.rsplit("/", 1)[0] + "/",
        size_bytes=size,
        size_human=f"{size} B",
        content_type="audio/wav",
        uploaded_at=datetime.now(UTC),
        url=None,
    )


def test_library_pairs_original_with_enhanced(monkeypatch):
    originals = [_fm("originals/podcast/ep01.wav", 1000)]
    enhanced = [_fm("enhanced/podcast/ep01.wav", 8000)]

    def fake_list(prefix=""):
        return originals if prefix.startswith("originals") else enhanced

    monkeypatch.setattr(library_service, "list_files", fake_list)

    tracks = library_service.get_library()
    assert len(tracks) == 1
    t = tracks[0]
    assert t.collection == "podcast"
    assert t.enhanced_key == "enhanced/podcast/ep01.wav"
    assert t.amplification_ratio == 8.0


def test_library_original_without_enhanced(monkeypatch):
    originals = [_fm("originals/tapes/reel.wav", 1000)]

    def fake_list(prefix=""):
        return originals if prefix.startswith("originals") else []

    monkeypatch.setattr(library_service, "list_files", fake_list)

    tracks = library_service.get_library()
    assert len(tracks) == 1
    assert tracks[0].enhanced_key is None
    assert tracks[0].amplification_ratio is None
