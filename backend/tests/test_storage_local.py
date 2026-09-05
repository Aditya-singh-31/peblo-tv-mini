from __future__ import annotations

from pathlib import Path

from app.storage.local import LocalStorage


def test_local_storage_saves_and_reads_bytes(tmp_path: Path) -> None:
    storage = LocalStorage(root_dir=tmp_path / "artwork", base_url="http://localhost:8000/storage")

    key = storage.save(data=b"hello world", filename="../../avatar.png", folder="poster")

    assert key.startswith("poster/")
    assert storage.exists(key)
    assert storage.read(key) == b"hello world"
    assert "poster/" in storage.public_url(key)


def test_local_storage_delete_and_missing_key(tmp_path: Path) -> None:
    storage = LocalStorage(root_dir=tmp_path / "deleted_storage", base_url="http://localhost:8000/storage")

    key = storage.save(data=b"test-data", filename="sample.jpg", folder="banner")
    assert storage.delete(key) is True
    assert storage.exists(key) is False
    assert storage.delete("missing/key.jpg") is False


def test_local_storage_uses_safe_key_without_user_filename_paths() -> None:
    storage = LocalStorage(root_dir=Path("tmp_storage_test_2"), base_url="http://localhost:8000/storage")

    key = storage.save(data=b"abc", filename="../folder/unsafe_name.jpg", folder="thumb")

    assert "unsafe_name.jpg" in key
    assert "../" not in key
    assert "folder" not in key
