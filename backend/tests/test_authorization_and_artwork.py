from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models import Show, User


@pytest.fixture
def api_context(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'authorization.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with session_factory() as session:
        show = Show(title="Artwork show", section="featured", status="draft")
        session.add(show)
        session.commit()
        show_id = show.id
    yield TestClient(app), session_factory, show_id
    app.dependency_overrides.clear()


def _set_user(role: str | None) -> None:
    if role is None:
        app.dependency_overrides.pop(get_current_user, None)
        return
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email=f"{role}@example.com",
        username=role,
        password_hash="unused",
        role=role,
    )


def _image_bytes(width: int, height: int, format_name: str = "JPEG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color="green").save(buffer, format=format_name)
    return buffer.getvalue()


def test_unauthenticated_crud_and_publish_are_rejected(api_context) -> None:
    client, _, show_id = api_context
    _set_user(None)

    assert client.get("/admin/shows").status_code == 401
    assert client.post("/admin/shows", json={"title": "No access"}).status_code == 401
    assert client.post("/admin/catalog/publish").status_code == 401
    assert client.post(f"/admin/artwork?artwork_type=POSTER&show_id={show_id}", files={"file": ("poster.jpg", _image_bytes(600, 900), "image/jpeg")}).status_code == 401


def test_editor_can_use_crud_but_cannot_publish(api_context) -> None:
    client, _, _ = api_context
    _set_user("editor")

    created = client.post("/admin/shows", json={"title": "Editor show"})
    assert created.status_code == 201
    show_id = created.json()["id"]
    assert client.patch(f"/admin/shows/{show_id}", json={"synopsis": "Edited"}).status_code == 200
    assert client.get("/admin/shows").status_code == 200
    assert client.delete(f"/admin/shows/{show_id}").status_code == 204
    assert client.post("/admin/catalog/publish").status_code == 403


def test_artwork_uploads_valid_poster_banner_and_thumbnail(api_context) -> None:
    client, _, show_id = api_context
    _set_user("editor")
    assets = [
        ("POSTER", 600, 900),
        ("BANNER", 1280, 720),
        ("THUMBNAIL", 640, 360),
    ]
    for artwork_type, width, height in assets:
        response = client.post(
            f"/admin/artwork?artwork_type={artwork_type}&show_id={show_id}",
            files={"file": (f"{artwork_type.lower()}.jpg", _image_bytes(width, height), "image/jpeg")},
        )
        assert response.status_code == 200, response.text
        assert response.json()["artwork_type"] == artwork_type


def test_artwork_upload_rejects_invalid_file_and_oversized_file(api_context) -> None:
    client, _, show_id = api_context
    _set_user("editor")
    invalid = client.post(
        f"/admin/artwork?artwork_type=POSTER&show_id={show_id}",
        files={"file": ("broken.jpg", b"not-an-image", "image/jpeg")},
    )
    assert invalid.status_code == 422

    oversized = _image_bytes(600, 900) + b"x" * (200 * 1024)
    response = client.post(
        f"/admin/artwork?artwork_type=POSTER&show_id={show_id}",
        files={"file": ("large.jpg", oversized, "image/jpeg")},
    )
    assert response.status_code == 422
    assert "200 KB" in response.json()["detail"]
