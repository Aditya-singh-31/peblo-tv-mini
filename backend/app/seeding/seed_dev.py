from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.models import Artwork, Episode, PublishRun, Season, Show, User
from app.storage.local import LocalStorage

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SEED_CANDIDATES = (
    Path(__file__).resolve().parents[4] / "challenge" / "seed_shows.json",
    Path(__file__).resolve().parents[3] / "challenge" / "seed_shows.json",
)
SEED_FILE = next((path for path in _SEED_CANDIDATES if path.exists()), _SEED_CANDIDATES[0])

_ASSET_CANDIDATES = (
    Path(__file__).resolve().parents[4] / "challenge" / "assets",
    Path(__file__).resolve().parents[3] / "challenge" / "assets",
)
ASSET_DIR = next((path for path in _ASSET_CANDIDATES if path.exists()), _ASSET_CANDIDATES[0])

_ARTWORK_TYPE_TO_FIXTURE = {
    "poster": "poster_good.jpg",
    "banner": "banner_good.jpg",
    "thumbnail": "thumb_good.jpg",
}


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def ensure_dev_users(session: Session) -> None:
    users = [
        {
            "email": settings.dev_editor_email,
            "username": "editor",
            "password": settings.dev_editor_password,
            "role": "editor",
        },
        {
            "email": settings.dev_admin_email,
            "username": "admin",
            "password": settings.dev_admin_password,
            "role": "admin",
        },
    ]

    for payload in users:
        email = payload["email"]
        if not email:
            continue

        existing = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            continue

        session.add(
            User(
                email=email,
                username=payload["username"],
                password_hash=_hash_password(payload["password"] or "change_me_dev"),
                role=payload["role"],
            )
        )

    session.commit()


def _get_show_title(source: dict[str, Any]) -> str:
    title = source.get("show_title")
    if title and title.strip():
        return title.strip()
    return source.get("title", "Untitled Show").strip() or "Untitled Show"


def _upsert_show(session: Session, source: dict[str, Any]) -> Show:
    title = _get_show_title(source)
    existing = session.execute(select(Show).where(Show.title == title)).scalar_one_or_none()
    if existing is not None:
        return existing

    categories = source.get("categories")
    if isinstance(categories, list):
        categories = ", ".join(str(c) for c in categories if c) or None
    else:
        categories = None

    show = Show(
        title=title,
        synopsis=source.get("synopsis"),
        section=source.get("section"),
        category=source.get("category"),
        categories=categories,
        status=source.get("status") or "draft",
    )
    session.add(show)
    session.flush()
    return show


def _upsert_season(session: Session, show: Show, season_number: int) -> Season:
    existing = session.execute(
        select(Season).where(Season.show_id == show.id, Season.season_number == season_number)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    season = Season(
        show_id=show.id,
        season_number=season_number,
        title=None,
        status="draft",
    )
    session.add(season)
    session.flush()
    return season


def _upsert_episode(session: Session, season: Season, source: dict[str, Any]) -> Episode:
    title = (source.get("episode_title") or source.get("title") or "").strip()
    content_group = source.get("content_group")
    language = source.get("language")

    existing = session.execute(
        select(Episode).where(
            Episode.content_group == content_group,
            Episode.language == language,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    episode = Episode(
        season_id=season.id,
        title=title or "Untitled Episode",
        synopsis=source.get("synopsis"),
        duration_seconds=source.get("duration_seconds") if source.get("duration_seconds") is not None else None,
        language=language,
        content_group=content_group,
        category=source.get("category"),
        status=source.get("episode_status") or "draft",
    )
    session.add(episode)
    session.flush()
    return episode


def _copy_asset_to_storage(storage: LocalStorage, artwork_type: str) -> str | None:
    fixture_name = _ARTWORK_TYPE_TO_FIXTURE.get(artwork_type)
    if not fixture_name:
        return None

    source_path = ASSET_DIR / fixture_name
    if not source_path.exists():
        return None

    data = source_path.read_bytes()
    return storage.save(data=data, filename=fixture_name, folder="uploads")


def _upsert_artwork(
    session: Session,
    storage: LocalStorage,
    episode: Episode,
    show: Show,
    artwork_type: str,
) -> Artwork | None:
    storage_key = _copy_asset_to_storage(storage, artwork_type)
    if not storage_key:
        return None

    existing = session.execute(
        select(Artwork).where(
            Artwork.artwork_type == artwork_type,
            Artwork.storage_key == storage_key,
            Artwork.episode_id == episode.id,
            Artwork.show_id == show.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    source_path = ASSET_DIR / _ARTWORK_TYPE_TO_FIXTURE[artwork_type]
    file_size = source_path.stat().st_size if source_path.exists() else None
    from PIL import Image

    width = None
    height = None
    mime_type = None
    if source_path.exists():
        try:
            with Image.open(source_path) as img:
                width = img.width
                height = img.height
            suffix = source_path.suffix.lower()
            if suffix == ".jpg" or suffix == ".jpeg":
                mime_type = "image/jpeg"
            elif suffix == ".png":
                mime_type = "image/png"
        except Exception:
            pass

    artwork = Artwork(
        episode_id=episode.id,
        show_id=show.id,
        artwork_type=artwork_type,
        storage_key=storage_key,
        mime_type=mime_type,
        width=width,
        height=height,
        file_size_bytes=file_size,
        notes=None,
    )
    session.add(artwork)
    session.flush()
    return artwork


def seed_database() -> None:
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_FILE}")

    session = SessionLocal()
    storage = LocalStorage()
    try:
        ensure_dev_users(session)

        seed_text = SEED_FILE.read_text(encoding="utf-8").strip()
        seed_data = json.loads(seed_text) if seed_text else []
        if not isinstance(seed_data, list):
            raise ValueError("Seed file must contain a JSON array of shows.")

        shows_by_title: dict[str, Show] = {}
        seasons_by_key: dict[tuple[int, int], Season] = {}

        for raw_row in seed_data:
            if not isinstance(raw_row, dict):
                continue

            title = _get_show_title(raw_row)
            if title not in shows_by_title:
                shows_by_title[title] = _upsert_show(session, raw_row)
            show = shows_by_title[title]

            season_number = raw_row.get("season_number")
            if season_number is None:
                season_number = 0
            season_key = (show.id, int(season_number))
            if season_key not in seasons_by_key:
                seasons_by_key[season_key] = _upsert_season(session, show, int(season_number))
            season = seasons_by_key[season_key]

            episode = _upsert_episode(session, season, raw_row)

            artwork_types = raw_row.get("artwork_available") or []
            if not isinstance(artwork_types, list):
                artwork_types = []
            for artwork_type in artwork_types:
                if artwork_type in _ARTWORK_TYPE_TO_FIXTURE:
                    _upsert_artwork(session, storage, episode, show, artwork_type)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
