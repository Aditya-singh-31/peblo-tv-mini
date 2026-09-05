from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import get_db, require_role
from app.models import Artwork, Episode, Show, User
from app.schemas.artwork import ArtworkResponse
from app.storage.local import LocalStorage
from app.validation.artwork import ArtworkValidationError, validate_artwork_bytes

router = APIRouter(prefix="/admin", tags=["admin-artwork"])
local_storage = LocalStorage()


@router.get("/artwork", response_model=list[ArtworkResponse])
def list_artwork(
    show_id: int | None = Query(default=None, ge=1),
    episode_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> list[ArtworkResponse]:
    del current_user
    artworks = db.execute(
        select(Artwork)
        .where(
            *(condition for condition in (
                Artwork.show_id == show_id if show_id is not None else None,
                Artwork.episode_id == episode_id if episode_id is not None else None,
            ) if condition is not None)
        )
        .order_by(Artwork.artwork_type, Artwork.id)
    ).scalars().all()
    return [
        ArtworkResponse(
            **{field: getattr(artwork, field) for field in ArtworkResponse.model_fields if field != "url"},
            url=local_storage.public_url(artwork.storage_key),
        )
        for artwork in artworks
    ]


@router.post("/artwork")
def upload_artwork(
    artwork_type: str,
    file: UploadFile = File(...),
    show_id: int | None = Query(default=None, ge=1),
    episode_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if (show_id is None) == (episode_id is None):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide exactly one show_id or episode_id")
    if show_id is not None and db.get(Show, show_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Show not found")
    if episode_id is not None and db.get(Episode, episode_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    try:
        payload = file.file.read()
        metadata = validate_artwork_bytes(payload, artwork_type)
    except ArtworkValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    storage_key = local_storage.save(data=payload, filename=file.filename or "upload.bin", folder=artwork_type.lower())

    db_artwork = Artwork(
        artwork_type=str(metadata["artwork_type"]),
        storage_key=storage_key,
        mime_type=str(metadata["mime_type"]),
        width=int(metadata["width"]),
        height=int(metadata["height"]),
        file_size_bytes=int(metadata["file_size_bytes"]),
        notes=f"uploaded by {current_user.email}",
        show_id=show_id,
        episode_id=episode_id,
    )
    db.add(db_artwork)
    db.commit()
    db.refresh(db_artwork)

    return {
        "id": db_artwork.id,
        "artwork_type": db_artwork.artwork_type,
        "storage_key": db_artwork.storage_key,
        "mime_type": db_artwork.mime_type,
        "width": db_artwork.width,
        "height": db_artwork.height,
        "file_size_bytes": db_artwork.file_size_bytes,
        "url": local_storage.public_url(db_artwork.storage_key),
    }
