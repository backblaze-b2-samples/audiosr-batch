"""Unit + integration tests for audio upload validation and content sniffing."""

import pytest

from app.service import upload as upload_service
from app.service.upload import (
    UploadError,
    matches_content_signature,
    process_upload,
    sanitize_collection,
    sanitize_filename,
    validate_extension_matches_type,
)
from app.types import FileUploadResponse

# --- sanitize_filename ------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd", "passwd"),  # path components stripped
        ("a\x00b.wav", "ab.wav"),  # null byte removed
        ("my clip.wav", "my_clip.wav"),  # unsafe char substituted
        ("...hidden", "_hidden"),  # dot run collapses to _ before dot-strip
        ("", "unnamed"),  # empty → placeholder
        ("/", "unnamed"),  # only a path separator → placeholder
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "a" * 300 + ".wav",  # long name with extension
        "a" * 300,  # long name, NO extension
        "a" * 300 + "." + "b" * 250,  # absurdly long extension
    ],
)
def test_sanitize_filename_truncates_long_names(raw):
    result = sanitize_filename(raw)
    assert len(result) <= 200
    assert not result.startswith(".")


# --- sanitize_collection ----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "default"),
        ("", "default"),
        ("podcast-a", "podcast-a"),
        ("a/b/c", "a_b_c"),
        ("../../evil", "evil"),
    ],
)
def test_sanitize_collection(raw, expected):
    assert sanitize_collection(raw) == expected


# --- validate_extension_matches_type ----------------------------------------


@pytest.mark.parametrize(
    ("filename", "content_type", "expected"),
    [
        ("clip.wav", "audio/wav", True),
        ("clip.wav", "audio/x-wav", True),
        ("song.mp3", "audio/mpeg", True),
        ("song.mpeg", "audio/mpeg", True),
        ("field.ogg", "audio/ogg", True),
        ("clip.mp3", "audio/wav", False),  # extension/type mismatch
        ("noext", "audio/wav", True),  # no extension → not enforced
        ("x.pdf", "application/octet-stream", False),  # type not in map
    ],
)
def test_validate_extension_matches_type(filename, content_type, expected):
    assert validate_extension_matches_type(filename, content_type) is expected


# --- matches_content_signature ----------------------------------------------

_WAV = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 8
_OGG = b"OggS" + b"\x00" * 8
_MP3_ID3 = b"ID3\x04\x00" + b"\x00" * 8
_MP3_SYNC = b"\xff\xfb" + b"\x00" * 8


@pytest.mark.parametrize(
    ("data", "content_type", "expected"),
    [
        (_WAV, "audio/wav", True),
        (_WAV, "audio/x-wav", True),
        (b"<html>not a wav", "audio/wav", False),  # spoofed audio
        (_OGG, "audio/ogg", True),
        (b"nope", "audio/ogg", False),
        (_MP3_ID3, "audio/mpeg", True),
        (_MP3_SYNC, "audio/mpeg", True),
        (b"not mp3 bytes", "audio/mpeg", False),
    ],
)
def test_matches_content_signature(data, content_type, expected):
    assert matches_content_signature(data, content_type) is expected


# --- process_upload rejection matrix ----------------------------------------


def test_rejects_oversized_content_length(monkeypatch):
    monkeypatch.setattr(upload_service.settings, "max_file_size", 10)
    with pytest.raises(UploadError) as exc:
        process_upload(_WAV, "a.wav", "audio/wav", content_length=999)
    assert exc.value.status_code == 413


def test_rejects_oversized_body(monkeypatch):
    monkeypatch.setattr(upload_service.settings, "max_file_size", 5)
    with pytest.raises(UploadError) as exc:
        process_upload(_WAV, "a.wav", "audio/wav", content_length=None)
    assert exc.value.status_code == 413


def test_rejects_disallowed_type():
    with pytest.raises(UploadError) as exc:
        process_upload(b"data", "a.exe", "application/x-msdownload", content_length=4)
    assert exc.value.status_code == 415


def test_rejects_extension_mismatch():
    with pytest.raises(UploadError) as exc:
        process_upload(_WAV, "a.mp3", "audio/wav", content_length=len(_WAV))
    assert exc.value.status_code == 415


def test_rejects_content_signature_mismatch():
    # A .wav name and declared audio/wav, but the bytes aren't a RIFF/WAVE.
    with pytest.raises(UploadError) as exc:
        process_upload(b"not a real wav", "a.wav", "audio/wav", content_length=14)
    assert exc.value.status_code == 415


def test_rejects_empty_file():
    with pytest.raises(UploadError):
        process_upload(b"", "a.wav", "audio/wav", content_length=0)


# --- uploads_total metric increments ----------------------------------------


@pytest.mark.asyncio
async def test_successful_upload_increments_uploads_metric(client, monkeypatch):
    from app.runtime import metrics

    monkeypatch.setattr(metrics, "_upload_count", 0)
    monkeypatch.setattr(
        upload_service,
        "upload_file",
        lambda file_data, key, content_type: FileUploadResponse(
            key=key,
            filename="a.wav",
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

    resp = await client.post(
        "/upload", files={"file": ("a.wav", _WAV, "audio/wav")}
    )
    assert resp.status_code == 200

    metrics_resp = await client.get("/metrics")
    assert "uploads_total 1" in metrics_resp.text
