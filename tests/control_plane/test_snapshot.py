from __future__ import annotations

import hashlib
from pathlib import Path

from project_standards.control_plane.snapshot import EntryKind, RepositorySnapshot
from project_standards.package_contract.paths import SafeRelativePath


def _targets(*paths: str) -> tuple[SafeRelativePath, ...]:
    return tuple(SafeRelativePath.parse(path) for path in paths)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "nested").mkdir(parents=True)
    # Deliberately larger than the 1 MiB read size so the streaming hash spans
    # several chunks; a single-chunk fixture would not exercise the boundary.
    (root / "large.bin").write_bytes(b"payload-byte" * 200_000)
    (root / "nested/small.txt").write_bytes(b"small\n")
    (root / "nested/link").symlink_to("small.txt")
    return root


def test_precondition_only_capture_matches_a_full_capture(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    targets = _targets("large.bin", "nested/small.txt", "nested/link", "nested", "absent.txt")

    full = RepositorySnapshot.capture(root, targets)
    lean = RepositorySnapshot.capture(root, targets, retain_content=False)

    assert [entry.precondition_digest for entry in full.entries] == [
        entry.precondition_digest for entry in lean.entries
    ]
    assert [entry.kind for entry in full.entries] == [entry.kind for entry in lean.entries]
    assert [entry.mode for entry in full.entries] == [entry.mode for entry in lean.entries]


def test_full_capture_keeps_exact_bytes_and_lean_capture_drops_them(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    content = (root / "large.bin").read_bytes()
    targets = _targets("large.bin")

    full = RepositorySnapshot.capture(root, targets).entries[0]
    lean = RepositorySnapshot.capture(root, targets, retain_content=False).entries[0]

    assert full.kind is EntryKind.REGULAR
    assert full.content == content
    assert full.content_digest is not None
    assert full.content_digest.value == f"sha256:{hashlib.sha256(content).hexdigest()}"
    assert lean.kind is EntryKind.REGULAR
    assert lean.content is None
    assert lean.content_digest is None
