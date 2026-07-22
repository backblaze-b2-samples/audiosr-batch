"""Unit tests for upload filename + collection handling."""

from app.service import upload as upload_service
from app.types import FileUploadResponse

_WAV = b"RIFF\x00\x00\x00\x00WAVEfmt "


def _stub_repo(monkeypatch):
    monkeypatch.setattr(
        upload_service,
        "upload_file",
        lambda file_data, key, content_type: FileUploadResponse(
            key=key,
            filename=key.split("/")[-1],
            size_bytes=len(file_data),
            size_human="16 B",
            content_type=content_type,
            uploaded_at="2026-02-14T00:00:00Z",
            url=None,
            metadata=None,
        ),
    )
    monkeypatch.setattr(
        upload_service,
        "extract_metadata",
        lambda file_data, filename, content_type, uploaded_at=None: None,
    )


def test_upload_allows_duplicate_filename(monkeypatch):
    """B2 is always versioned — re-uploading the same name creates a new version."""
    _stub_repo(monkeypatch)
    result = upload_service.process_upload(
        file_data=_WAV,
        filename="clip.wav",
        content_type="audio/wav",
        content_length=len(_WAV),
    )
    assert result.key == "originals/default/clip.wav"


def test_upload_places_under_collection(monkeypatch):
    """A collection routes the original under originals/<collection>/."""
    _stub_repo(monkeypatch)
    result = upload_service.process_upload(
        file_data=_WAV,
        filename="ep01.wav",
        content_type="audio/wav",
        content_length=len(_WAV),
        collection="podcast-a",
    )
    assert result.key == "originals/podcast-a/ep01.wav"


def test_collection_is_sanitized(monkeypatch):
    """Unsafe collection names collapse to a single safe path segment."""
    _stub_repo(monkeypatch)
    result = upload_service.process_upload(
        file_data=_WAV,
        filename="ep01.wav",
        content_type="audio/wav",
        content_length=len(_WAV),
        collection="../evil/../",
    )
    # No path traversal escapes the originals/ prefix.
    assert result.key.startswith("originals/")
    assert ".." not in result.key
    assert result.key.count("/") == 2
