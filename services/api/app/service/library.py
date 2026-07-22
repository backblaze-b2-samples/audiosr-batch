"""Audio Library — the sample's scoped explorer.

Distinct from the full-bucket `/files` browser: this joins each ingested
original (under `originals/`) to its enhanced rendition (under `enhanced/`) so
the UI can pair and play them together. Scoped strictly to the app's own two
prefixes.
"""

from app.config import settings
from app.repo import list_files
from app.types import LibraryTrack


def _derive(input_key: str) -> tuple[str, str]:
    """Return (collection, base_name) for an originals key."""
    rel = input_key
    if rel.startswith(settings.originals_prefix):
        rel = rel[len(settings.originals_prefix):]
    parts = rel.split("/")
    if len(parts) >= 2:
        collection = parts[0]
        name = "/".join(parts[1:])
    else:
        collection = "default"
        name = rel
    base = name.rsplit(".", 1)[0] if "." in name else name
    return collection, base


def get_library() -> list[LibraryTrack]:
    """List ingested originals paired with their enhanced renditions."""
    originals = list_files(prefix=settings.originals_prefix)
    enhanced = list_files(prefix=settings.enhanced_prefix)
    # Index enhanced WAVs by key for O(1) pairing.
    enhanced_by_key = {e.key: e for e in enhanced if e.key.endswith(".wav")}

    tracks: list[LibraryTrack] = []
    for orig in originals:
        collection, base = _derive(orig.key)
        expected = f"{settings.enhanced_prefix}{collection}/{base}.wav"
        enh = enhanced_by_key.get(expected)
        amp = (
            round(enh.size_bytes / orig.size_bytes, 2)
            if enh and orig.size_bytes
            else None
        )
        tracks.append(
            LibraryTrack(
                collection=collection,
                original_key=orig.key,
                original_filename=orig.filename,
                original_size_bytes=orig.size_bytes,
                original_size_human=orig.size_human,
                content_type=orig.content_type,
                uploaded_at=orig.uploaded_at,
                enhanced_key=enh.key if enh else None,
                enhanced_size_bytes=enh.size_bytes if enh else None,
                enhanced_size_human=enh.size_human if enh else None,
                amplification_ratio=amp,
            )
        )
    tracks.sort(key=lambda t: t.uploaded_at, reverse=True)
    return tracks
