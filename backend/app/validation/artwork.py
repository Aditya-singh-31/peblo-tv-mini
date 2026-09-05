from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image
from PIL import UnidentifiedImageError

ArtworkKind = Literal["POSTER", "BANNER", "THUMBNAIL"]


@dataclass(frozen=True)
class ArtworkSpec:
    kind: ArtworkKind
    width: int
    height: int
    ratio_width: int
    ratio_height: int
    max_size_bytes: int = 200 * 1024


ARTWORK_SPECS: dict[ArtworkKind, ArtworkSpec] = {
    "POSTER": ArtworkSpec(
        kind="POSTER",
        width=600,
        height=900,
        ratio_width=2,
        ratio_height=3,
        max_size_bytes=200 * 1024,
    ),
    "BANNER": ArtworkSpec(
        kind="BANNER",
        width=1280,
        height=720,
        ratio_width=16,
        ratio_height=9,
        max_size_bytes=200 * 1024,
    ),
    "THUMBNAIL": ArtworkSpec(
        kind="THUMBNAIL",
        width=640,
        height=360,
        ratio_width=16,
        ratio_height=9,
        max_size_bytes=200 * 1024,
    ),
}


class ArtworkValidationError(ValueError):
    pass


def _ratio_matches(width: int, height: int, ratio_width: int, ratio_height: int, tolerance: float = 0.02) -> bool:
    actual_ratio = width / height
    expected_ratio = ratio_width / ratio_height
    return abs(actual_ratio - expected_ratio) <= tolerance


def validate_artwork_bytes(data: bytes, artwork_type: str) -> dict[str, object]:
    kind = artwork_type.upper()
    if kind not in ARTWORK_SPECS:
        raise ArtworkValidationError(f"Unsupported artwork type: {artwork_type}")

    spec = ARTWORK_SPECS[kind]

    if len(data) > spec.max_size_bytes:
        raise ArtworkValidationError(f"{spec.kind.title()} is larger than the 200 KB limit.")

    try:
        with Image.open(BytesIO(data)) as img:
            img.load()
            width, height = img.size
            mime_type = Image.MIME.get(img.format or "JPEG", "application/octet-stream")
            if img.format is None:
                raise ArtworkValidationError(f"{spec.kind.title()} is not a valid image file.")
    except (UnidentifiedImageError, OSError):
        raise ArtworkValidationError(f"{spec.kind.title()} is not a valid image file.")

    if width <= 0 or height <= 0:
        raise ArtworkValidationError(f"{spec.kind.title()} dimensions are invalid. Please upload an image approximately {spec.width} × {spec.height} pixels.")

    if not _ratio_matches(width, height, spec.ratio_width, spec.ratio_height):
        raise ArtworkValidationError(
            f"{spec.kind.title()} has the wrong aspect ratio. Required ratio is {spec.ratio_width}:{spec.ratio_height}."
        )

    min_width = int(spec.width * 0.75)
    min_height = int(spec.height * 0.75)
    max_width = int(spec.width * 1.5)
    max_height = int(spec.height * 1.5)

    if width < min_width or height < min_height or width > max_width or height > max_height:
        raise ArtworkValidationError(
            f"{spec.kind.title()} dimensions are invalid. Please upload an image approximately {spec.width} × {spec.height} pixels."
        )

    return {
        "artwork_type": spec.kind,
        "width": width,
        "height": height,
        "mime_type": mime_type,
        "file_size_bytes": len(data),
    }
