from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ShowPublicationError(ValueError):
    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        super().__init__(f"Show is missing required publish data: {', '.join(missing_fields)}")


_REFERENCE_PATH = Path(__file__).resolve().parents[4] / "challenge" / "reference.json"


def _reference_data() -> Any:
    try:
        return json.loads(_REFERENCE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _reference_values(name: str) -> set[str]:
    reference = _reference_data()
    values: Any = reference.get(name) if isinstance(reference, dict) else None
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if isinstance(value, (str, int, float))}


def validate_show_reference_fields(values: dict[str, Any]) -> None:
    """Apply optional value sets from reference.json when the fixture provides them."""
    for field_name in ("section", "category", "status"):
        allowed = _reference_values(field_name)
        value = values.get(field_name)
        if allowed and value is not None and value not in allowed:
            raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed))}")


def validate_show_for_publication(values: dict[str, Any]) -> None:
    validate_show_reference_fields(values)
    missing_fields = [field for field in ("title", "section") if not str(values.get(field) or "").strip()]
    if missing_fields:
        raise ShowPublicationError(missing_fields)
