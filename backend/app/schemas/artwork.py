from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArtworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_id: int | None
    show_id: int | None
    artwork_type: str
    storage_key: str
    mime_type: str | None
    width: int | None
    height: int | None
    file_size_bytes: int | None
    url: str
    created_at: datetime
    updated_at: datetime
