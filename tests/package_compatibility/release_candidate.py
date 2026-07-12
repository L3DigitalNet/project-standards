"""Build disposable release-cut checkouts without mutating the source tree."""

from __future__ import annotations

import shutil
import subprocess
from hashlib import sha256
from pathlib import Path

from tests.wheel_helpers import extract_pure_python_wheel

_ROOT = Path(__file__).resolve().parents[2]
_RELEASE_EVIDENCE = Path(
    "docs/reviews/2026-07-11-consumer-standards-control-plane-release-cut-evidence.md"
)

_DIRECT_WRITER_RUNTIME_PATHS = frozenset(
    {
        "project_standards/adopt/engine.py",
        "project_standards/adopt/manifest.py",
        "project_standards/agent_handoff/cli.py",
        "project_standards/agent_handoff/planning.py",
        "project_standards/agent_handoff/providers.py",
        "project_standards/agent_handoff/validation.py",
        "project_standards/cli.py",
        "project_standards/provider_runner.py",
        "project_standards/standards_graph/catalog.py",
        "project_standards/standards_graph/cli.py",
        "project_standards/standards_graph/discovery.py",
        "project_standards/standards_graph/model.py",
        "project_standards/standards_graph/validators.py",
    }
)

_V5_FALLBACK_RUNTIME_PATHS = frozenset(
    {
        "project_standards/agent_handoff/legacy.py",
        "project_standards/specs/cli.py",
        "project_standards/sync_standards_include.py",
        "project_standards/sync_vscode_colors.py",
        "project_standards/validate_frontmatter.py",
    }
)


def _git(checkout: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=checkout,
        input=input_bytes,
        check=True,
        capture_output=True,
    ).stdout


def _git_known_worktree_paths(source_root: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=source_root,
        check=True,
        capture_output=True,
    )
    return tuple(
        sorted(
            (Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw),
            key=lambda path: path.as_posix().encode("utf-8"),
        )
    )


def release_input_digest(source_root: Path = _ROOT) -> str:
    """Hash every copied release input except the self-referential evidence file."""
    digest = sha256()
    for relative in _git_known_worktree_paths(source_root):
        if relative == _RELEASE_EVIDENCE:
            continue
        source = source_root / relative
        if not source.exists() and not source.is_symlink():
            continue
        metadata = source.lstat()
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{metadata.st_mode:o}".encode("ascii"))
        digest.update(b"\0")
        if source.is_symlink():
            digest.update(b"symlink\0")
            digest.update(source.readlink().as_posix().encode("utf-8"))
        else:
            digest.update(b"regular\0")
            digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def assert_release_evidence_current(source_root: Path = _ROOT) -> None:
    """Fail before release replay when the retained evidence predates any input."""
    digest = release_input_digest(source_root)
    expected = f"Release-input SHA-256: `{digest}`"
    evidence = (source_root / _RELEASE_EVIDENCE).read_text(encoding="utf-8")
    assert expected in evidence, (
        f"release evidence is stale; refresh the disposable proof for release-input digest {digest}"
    )


def copy_tracked_checkout(target: Path, *, source_root: Path = _ROOT) -> Path:
    """Copy Git-known working-tree paths, preserving symlink identities.

    Include non-ignored additions and omit tracked deletions so pre-commit release
    verification exercises the tree that would be committed, not the stale index.
    """
    for relative in _git_known_worktree_paths(source_root):
        source = source_root / relative
        if not source.exists() and not source.is_symlink():
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.symlink_to(source.readlink())
        else:
            shutil.copy2(source, destination)
    return target


def initialize_release_baseline(checkout: Path) -> None:
    """Create a local baseline so the exact release patch can be hashed and replayed."""
    _git(checkout, "init", "--quiet")
    _git(checkout, "add", ".")
    _git(
        checkout,
        "-c",
        "user.name=Release Evidence",
        "-c",
        "user.email=168346341+chrisdpurcell@users.noreply.github.com",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "--quiet",
        "-m",
        "tracked baseline",
    )


def mirror_release_tree(source: Path, baseline: Path) -> None:
    """Overlay one completed release tree onto an initialized tracked baseline."""
    source_files = {
        path.relative_to(source)
        for path in source.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    for path in baseline.rglob("*"):
        relative = path.relative_to(baseline)
        if ".git" in relative.parts or (not path.is_file() and not path.is_symlink()):
            continue
        if relative not in source_files:
            path.unlink()
    for relative in sorted(source_files, key=lambda item: item.as_posix().encode()):
        source_path = source / relative
        target = baseline / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            target.unlink()
        if source_path.is_symlink():
            target.symlink_to(source_path.readlink())
        else:
            shutil.copy2(source_path, target)


def set_release_version(checkout: Path, version: str = "5.0.0") -> None:
    """Set only the disposable checkout's package and root lock version."""
    replacements = (
        (checkout / "pyproject.toml", 'version = "4.3.0"', f'version = "{version}"'),
        (checkout / "uv.lock", 'version = "4.3.0"', f'version = "{version}"'),
    )
    for path, before, after in replacements:
        content = path.read_text(encoding="utf-8")
        assert content.count(before) == 1, path
        path.write_text(content.replace(before, after), encoding="utf-8")


def declare_release_cut_intent(checkout: Path) -> None:
    """Make repository-specific V5 options explicit in the disposable legacy input."""
    legacy = checkout / ".project-standards.yml"
    content = legacy.read_text(encoding="utf-8")
    anchor = 'python_tooling:\n  version: "1.0"\n'
    replacement = """python_tooling:
  version: "1.0"
  additional_dev_dependencies:
    - "types-PyYAML"
  ruff:
    line_length: 100
    extend_exclude:
      - ".claude/hooks"
      - ".codex/hooks"
      - "docs/handoff"
  pytest:
    fail_under: 85
    markers:
      - "performance: deterministic scale gates run explicitly in CI"
    coverage_exclude_also:
      - "if __name__ == .__main__.:"
"""
    assert content.count(anchor) == 1
    legacy.write_text(content.replace(anchor, replacement), encoding="utf-8")

    pyproject = checkout / "pyproject.toml"
    project = pyproject.read_text(encoding="utf-8")
    before = """[dependency-groups]
dev = [
    "pytest>=9.0",
    "ruff>=0.14",
    "basedpyright",
    "types-PyYAML",
    "coverage[toml]",
    "pip-audit",
]
"""
    after = """[dependency-groups]
dev = [
    "basedpyright",
    "coverage[toml]",
    "pip-audit",
    "pytest>=9.0",
    "ruff>=0.14.11",
    "types-PyYAML",
]
"""
    assert project.count(before) == 1
    pyproject.write_text(project.replace(before, after), encoding="utf-8")


def build_installed_release(checkout: Path, target: Path) -> Path:
    """Build one offline wheel and extract its importable installed tree."""
    output = target / "dist"
    subprocess.run(
        ["uv", "build", "--offline", "--wheel", "--out-dir", str(output)],
        cwd=checkout,
        check=True,
        capture_output=True,
    )
    (wheel,) = output.glob("*.whl")
    installed = target / "installed"
    extract_pure_python_wheel(wheel, installed)
    return installed


def release_patch(checkout: Path) -> tuple[bytes, tuple[str, ...], str]:
    """Return the complete binary-safe release patch, its paths, and SHA-256."""
    _git(checkout, "add", "--intent-to-add", ".")
    patch = _git(checkout, "diff", "--binary", "--no-ext-diff", "HEAD", "--", ".")
    paths = tuple(
        line.decode().split("\t", 1)[-1]
        for line in _git(checkout, "diff", "--name-status", "HEAD", "--", ".").splitlines()
    )
    return patch, paths, sha256(patch).hexdigest()


def replay_release_patch(baseline: Path, patch: bytes) -> None:
    """Apply the reviewed patch to a fresh tracked baseline."""
    _git(baseline, "apply", "--binary", "-", input_bytes=patch)


def classify_legacy_dependencies(root: Path) -> dict[str, tuple[str, ...]]:
    """Classify every retained legacy-authority reference in a tracked or installed tree."""
    tokens = (
        b".project-standards.yml",
        b"adopt.toml",
        b".agents/agent-handoff/manifest.json",
        b"project_standards/bundles",
        b"project_standards.adopt",
        b"apply_adoption(",
        b"execute_plan(",
    )
    classified: dict[str, list[str]] = {
        "migration-runtime": [],
        "direct-writer-runtime": [],
        "v5-fallback-runtime": [],
        "historical-or-test": [],
        "unclassified": [],
    }
    for path in root.rglob("*"):
        relative_path = path.relative_to(root)
        if (
            not path.is_file()
            or path.is_symlink()
            or ".git" in relative_path.parts
            or "__pycache__" in relative_path.parts
        ):
            continue
        try:
            content = path.read_bytes()
        except OSError:
            continue
        relative = relative_path.as_posix()
        normalized = relative.removeprefix("src/")
        is_v1_family_index = normalized.startswith(
            "project_standards/bundles/"
        ) and normalized.endswith("/standard.toml")
        if not is_v1_family_index and not any(token in content for token in tokens):
            continue
        module_relative = normalized.removeprefix("project_standards/")
        if module_relative.startswith("control_plane/"):
            category = "migration-runtime"
        elif normalized in _DIRECT_WRITER_RUNTIME_PATHS:
            category = "direct-writer-runtime"
        elif (
            normalized in _V5_FALLBACK_RUNTIME_PATHS
            or normalized.startswith("project_standards/bundles/")
            or relative.startswith("scripts/")
        ):
            category = "v5-fallback-runtime"
        elif (
            relative.startswith(("tests/", "docs/", "standards/", "meta/"))
            or normalized.startswith(("project_standards/families/", "project_standards/payloads/"))
            or normalized == "project_standards/README.md"
            or ("/" not in relative and relative.endswith((".md", ".jsonc")))
            or ".dist-info/" in relative
        ):
            category = "historical-or-test"
        else:
            category = "unclassified"
        classified[category].append(relative)
    return {key: tuple(sorted(values, key=str.encode)) for key, values in classified.items()}
