"""Pin the shared payload-tree walker against interpreter bytecode."""

from __future__ import annotations

import shutil
from pathlib import Path

from tests.payload_tree import is_bytecode_artifact, payload_tree

_ROOT = Path(__file__).resolve().parents[1]
# A real payload with a provider directory: it is exactly the shape whose import
# leaves a cache behind on the workspace-reusing self-hosted runner.
_PAYLOAD = _ROOT / "standards/python-tooling/versions/1.14"


def _seed_cache(payload: Path) -> Path:
    cache = payload / "providers/__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    artifact = cache / "python_tooling.cpython-314.pyc"
    artifact.write_bytes(b"\xcb\r\r\n\xff\xfe\x00\x00")
    return artifact


def test_payload_tree_ignores_bytecode_left_beside_a_provider(tmp_path: Path) -> None:
    payload = tmp_path / "1.14"
    shutil.copytree(_PAYLOAD, payload)
    declared = payload_tree(payload)
    artifact = _seed_cache(payload)

    assert artifact.exists()
    assert payload_tree(payload) == declared
    # The cache is the ONLY thing hidden: an unfiltered walk differs by exactly the
    # cache directory and its compiled file, so the filter cannot mask real content.
    assert set(payload.rglob("*")) - set(payload_tree(payload)) == {artifact, artifact.parent}


def test_payload_tree_keeps_a_scratch_tree_under_a_cache_named_ancestor(tmp_path: Path) -> None:
    # `root` itself may sit anywhere; only the part of a path BELOW the walked root
    # decides, so a temp directory that happens to contain `__pycache__` in its own
    # prefix still enumerates normally.
    root = tmp_path / "__pycache__" / "repository"
    (root / "providers").mkdir(parents=True)
    source = root / "providers/provider.py"
    source.write_text("x = 1\n", encoding="utf-8")

    assert source in payload_tree(root)


def test_bytecode_artifact_covers_cache_directories_and_compiled_files() -> None:
    assert is_bytecode_artifact(Path("providers/__pycache__"))
    assert is_bytecode_artifact(Path("providers/__pycache__/provider.cpython-314.pyc"))
    assert is_bytecode_artifact(Path("providers/provider.pyo"))
    assert not is_bytecode_artifact(Path("providers/provider.py"))
