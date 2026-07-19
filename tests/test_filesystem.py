from __future__ import annotations

import importlib
from contextlib import AbstractContextManager
from pathlib import Path, PurePosixPath
from typing import Protocol, cast

import pytest


class _FilesystemModule(Protocol):
    def _directory_descriptor(self, root: Path) -> AbstractContextManager[int]: ...

    def _write_bytes(
        self,
        root_descriptor: int,
        relative: PurePosixPath,
        content: bytes,
        *,
        mode: int | None,
        replace: bool,
        temporary_prefix: str,
    ) -> bool: ...

    def _prune_empty_directory(
        self,
        root_descriptor: int,
        relative: PurePosixPath,
    ) -> None: ...


def _filesystem() -> _FilesystemModule:
    try:
        module = importlib.import_module("project_standards._filesystem")
    except ModuleNotFoundError as exc:
        if exc.name != "project_standards._filesystem":
            raise
        pytest.fail("shared descriptor-relative filesystem primitives are missing")
    return cast(_FilesystemModule, module)


def test_write_bytes__existing_destination__does_not_clobber(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_bytes(b"consumer\n")
    filesystem = _filesystem()

    with filesystem._directory_descriptor(  # pyright: ignore[reportPrivateUsage]
        tmp_path
    ) as root_descriptor:
        installed = filesystem._write_bytes(  # pyright: ignore[reportPrivateUsage]
            root_descriptor,
            PurePosixPath("target.txt"),
            b"managed\n",
            mode=None,
            replace=False,
            temporary_prefix=".test-write-",
        )

    assert installed is False
    assert target.read_bytes() == b"consumer\n"
    assert not list(tmp_path.glob(".test-write-*"))


def test_write_bytes__symlinked_parent__does_not_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    filesystem = _filesystem()

    with (
        filesystem._directory_descriptor(  # pyright: ignore[reportPrivateUsage]
            root
        ) as root_descriptor,
        pytest.raises(OSError),
    ):
        filesystem._write_bytes(  # pyright: ignore[reportPrivateUsage]
            root_descriptor,
            PurePosixPath("link/escaped.txt"),
            b"managed\n",
            mode=None,
            replace=False,
            temporary_prefix=".test-write-",
        )

    assert not (outside / "escaped.txt").exists()


def test_prune_empty_directory__symlinked_namespace__does_not_delete_outside(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside_child = tmp_path / "outside" / "empty"
    outside_child.mkdir(parents=True)
    (root / "namespace").symlink_to(outside_child.parent, target_is_directory=True)
    filesystem = _filesystem()

    with (
        filesystem._directory_descriptor(  # pyright: ignore[reportPrivateUsage]
            root
        ) as root_descriptor,
        pytest.raises(OSError),
    ):
        filesystem._prune_empty_directory(  # pyright: ignore[reportPrivateUsage]
            root_descriptor,
            PurePosixPath("namespace"),
        )

    assert outside_child.is_dir()
