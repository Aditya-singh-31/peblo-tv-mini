from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


SeasonStatus = Literal["draft", "published"]


class SeasonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season_number: int = Field(ge=0)
    title: str | None = Field(default=None, max_length=255)
    status: SeasonStatus = "draft"

    @field_validator("title")
    @classmethod
    def blank_title_is_null(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SeasonUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season_number: int | None = Field(default=None, ge=0)
    title: str | None = Field(default=None, max_length=255)
    status: SeasonStatus | None = None

    @field_validator("title")
    @classmethod
    def blank_title_is_null(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SeasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    show_id: int
    season_number: int
    title: str | None
    status: SeasonStatus
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def is_trailer(self) -> bool:
        return self.season_number == 0
