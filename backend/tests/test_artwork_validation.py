from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.validation.artwork import validate_artwork_bytes

client = TestClient(app)

_ASSET_CANDIDATES = (
    Path(__file__).resolve().parents[3] / "challenge" / "assets",
    Path(__file__).resolve().parents[2] / "challenge" / "assets",
)
ASSET_DIR = next((path for path in _ASSET_CANDIDATES if path.exists()), _ASSET_CANDIDATES[0])


def _asset_bytes(name: str) -> bytes:
    return (ASSET_DIR / name).read_bytes()


def test_valid_poster_passes_validation() -> None:
    result = validate_artwork_bytes(_asset_bytes("poster_good.jpg"), "POSTER")
    assert result["artwork_type"] == "POSTER"
    assert result["width"] == 600
    assert result["height"] == 900


def test_wrong_ratio_rejected() -> None:
    with pytest.raises(ValueError, match="aspect ratio"):
        validate_artwork_bytes(_asset_bytes("poster_wrong_ratio.jpg"), "POSTER")


def test_banner_too_big_rejected() -> None:
    with pytest.raises(ValueError, match="dimensions are invalid"):
        validate_artwork_bytes(_asset_bytes("banner_too_big.png"), "BANNER")


def test_valid_banner_passes_validation() -> None:
    result = validate_artwork_bytes(_asset_bytes("banner_good.jpg"), "BANNER")
    assert result["artwork_type"] == "BANNER"
    assert result["width"] == 1280
    assert result["height"] == 720


def test_thumb_tiny_rejected() -> None:
    with pytest.raises(ValueError, match="dimensions are invalid"):
        validate_artwork_bytes(_asset_bytes("thumb_tiny.jpg"), "THUMBNAIL")


def test_valid_thumbnail_passes_validation() -> None:
    result = validate_artwork_bytes(_asset_bytes("thumb_good.jpg"), "THUMBNAIL")
    assert result["artwork_type"] == "THUMBNAIL"
    assert result["width"] == 640
    assert result["height"] == 360


def test_invalid_file_rejected() -> None:
    with pytest.raises(ValueError, match="not a valid image"):
        validate_artwork_bytes(b"not-an-image", "POSTER")


def test_file_size_limit_rejected() -> None:
    buffer = BytesIO()
    Image.new("RGB", (600, 900), color="blue").save(buffer, format="JPEG", quality=95)
    payload = buffer.getvalue() + b"x" * (200 * 1024)

    with pytest.raises(ValueError, match="200 KB limit"):
        validate_artwork_bytes(payload, "POSTER")


def test_upload_endpoint_requires_auth() -> None:
    with open(ASSET_DIR / "poster_good.jpg", "rb") as fh:
        response = client.post(
            "/admin/artwork?artwork_type=POSTER",
            files={"file": ("poster_good.jpg", fh, "image/jpeg")},
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
