from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings
from app.storage.base import StorageService


class LocalStorage:
    def __init__(self, root_dir: str | Path | None = None, base_url: str | None = None) -> None:
        self.root_dir = Path(root_dir or settings.local_storage_path).expanduser().resolve()
        self.base_url = (base_url or settings.local_storage_url).rstrip("/")
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _safe_key(self, filename: str, folder: str) -> str:
        safe_name = Path(filename).name
        safe_name = safe_name.replace("../", "").replace("..\\", "")
        safe_name = safe_name.strip("/")

        digest = hashlib.sha256(safe_name.encode("utf-8")).hexdigest()[:12]
        return f"{folder.rstrip('/')}/{digest}_{safe_name}"

    def save(self, *, data: bytes, filename: str, folder: str = "uploads") -> str:
        storage_key = self._safe_key(filename, folder)
        target = self.root_dir / storage_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return storage_key

    def read(self, key: str) -> bytes:
        path = self.root_dir / key
        return path.read_bytes()

    def delete(self, key: str) -> bool:
        path = self.root_dir / key
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, key: str) -> bool:
        return (self.root_dir / key).exists()

    def public_url(self, key: str) -> str:
        return f"{self.base_url}/{key.lstrip('/')}"

    def internal_url(self, key: str) -> str:
        return self.public_url(key)

    def write_immutable(self, key: str, data: bytes) -> None:
        """Write a catalogue version without replacing an existing version."""
        target = self.root_dir / key
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != data:
                raise FileExistsError(f"Immutable storage key already contains different data: {key}")
            return

        file_descriptor, temporary_name = tempfile.mkstemp(prefix=".catalogue-", dir=target.parent)
        try:
            with os.fdopen(file_descriptor, "wb") as temporary_file:
                temporary_file.write(data)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, target)
            self._sync_directory(target.parent)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise

    def activate_pointer(self, key: str, pointer_key: str = "catalogue/live.json") -> None:
        """Atomically switch the live catalogue pointer to an immutable version."""
        pointer = self.root_dir / pointer_key
        pointer.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"key": key}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        file_descriptor, temporary_name = tempfile.mkstemp(prefix=".live-", dir=pointer.parent)
        try:
            with os.fdopen(file_descriptor, "wb") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, pointer)
            self._sync_directory(pointer.parent)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise

    def read_live_key(self, pointer_key: str = "catalogue/live.json") -> str | None:
        pointer = self.root_dir / pointer_key
        if not pointer.exists():
            return None
        payload: Any = json.loads(pointer.read_text(encoding="utf-8"))
        return str(payload["key"]) if isinstance(payload, dict) and payload.get("key") else None

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        if os.name == "nt":
            return
        directory_descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)


storage_service: StorageService = LocalStorage()
