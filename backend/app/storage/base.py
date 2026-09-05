from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StorageService(Protocol):
    def save(self, *, data: bytes, filename: str, folder: str = "uploads") -> str:
        """Persist bytes and return a storage key."""

    def read(self, key: str) -> bytes:
        """Return stored bytes for a key."""

    def delete(self, key: str) -> bool:
        """Delete a stored object and return whether it existed."""

    def exists(self, key: str) -> bool:
        """Return whether the object exists."""

    def public_url(self, key: str) -> str:
        """Return a public or externally usable URL."""

    def internal_url(self, key: str) -> str:
        """Return an internal or app-local URL reference."""
