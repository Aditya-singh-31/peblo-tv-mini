from __future__ import annotations

from typing import Any


class EpisodePublicationError(ValueError):
    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        super().__init__(f"Episode is missing required publish data: {', '.join(missing_fields)}")


def validate_episode_for_publication(values: dict[str, Any], artwork_count: int) -> None:
    missing_fields: list[str] = []
    if values.get("duration_seconds") is None:
        missing_fields.append("duration_seconds")
    if artwork_count < 1:
        missing_fields.append("artwork")
    if missing_fields:
        raise EpisodePublicationError(missing_fields)
