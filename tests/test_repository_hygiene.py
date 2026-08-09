from __future__ import annotations

import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MODE_POLICY_ANCHOR = "2989563cc94dfd8561404d7ad8896eb83b459225"
_PREDECESSOR = "v5.13.0"

_EXECUTABLE_ALLOWLIST = frozenset(
    {
        ".agents/hooks/agent-handoff/session_start.py",
        ".agents/skills/markdown-frontmatter/scripts/new-doc-id",
        "docs/handoff/bugs/_regen_index.py",
        "scripts/verify.sh",
        "src/project_standards/bundles/agent-handoff/hooks/session-start/session_start.py",
        "src/project_standards/bundles/markdown-frontmatter/skills/markdown-frontmatter/scripts/new-doc-id",
        "src/project_standards/validate_frontmatter.py",
        "standards/agent-handoff/hooks/session-start/session_start.py",
        "standards/markdown-frontmatter/skills/markdown-frontmatter/scripts/new-doc-id",
    }
)

_MUTABLE_NORMALIZATION_ALLOWLIST = frozenset(
    {
        "src/project_standards/__init__.py",
        "src/project_standards/specs/templates/spec-full-template.md",
        "src/project_standards/specs/templates/spec-light-template.md",
        "src/project_standards/specs/templates/spec-standard-template.md",
        "standards/project-spec/resources/tooling-notes.md",
        "standards/project-spec/templates/spec-full-template.md",
        "standards/project-spec/templates/spec-light-template.md",
        "standards/project-spec/templates/spec-standard-template.md",
    }
)

_IMMUTABLE_PROJECTION_EXCLUSIONS = frozenset(
    {
        *{
            "standards/markdown-frontmatter/versions/"
            f"{version}/skills/markdown-frontmatter/scripts/new-doc-id"
            for version in ("1.2", "1.3", "1.4", "1.5", "1.6", "1.7")
        },
        *{
            f"standards/project-spec/versions/{version}/{resource}"
            for version in ("1.1", "1.2", "1.3", "1.4", "1.5")
            for resource in (
                "resources/tooling-notes.md",
                "templates/spec-full-template.md",
                "templates/spec-light-template.md",
                "templates/spec-standard-template.md",
            )
        },
    }
)

_POST_ANCHOR_IMMUTABLE_PROJECTION_EXECUTABLES = frozenset(
    {
        ".agents/hooks/agent-handoff/session-start",
        ".agents/skills/github-workflow/bin/gh-workflow",
        "standards/agent-handoff/versions/1.10/hooks/session-start/session-start",
        "standards/agent-handoff/versions/1.11/hooks/session-start/session-start",
        "standards/github-workflow/versions/1.0/skills/github-workflow/bin/gh-workflow",
        "standards/github-workflow/versions/1.1/skills/github-workflow/bin/gh-workflow",
        "standards/markdown-frontmatter/versions/1.10/skills/markdown-frontmatter/scripts/new-doc-id",
        "standards/markdown-frontmatter/versions/1.8/skills/markdown-frontmatter/scripts/new-doc-id",
        "standards/markdown-frontmatter/versions/1.9/skills/markdown-frontmatter/scripts/new-doc-id",
        "standards/project-spec/versions/1.6/resources/tooling-notes.md",
        "standards/project-spec/versions/1.6/templates/spec-full-template.md",
        "standards/project-spec/versions/1.6/templates/spec-light-template.md",
        "standards/project-spec/versions/1.6/templates/spec-standard-template.md",
        "standards/project-spec/versions/1.7/resources/tooling-notes.md",
        "standards/project-spec/versions/1.7/templates/spec-full-template.md",
        "standards/project-spec/versions/1.7/templates/spec-light-template.md",
        "standards/project-spec/versions/1.7/templates/spec-standard-template.md",
        "standards/project-spec/versions/1.8/resources/tooling-notes.md",
        "standards/project-spec/versions/1.8/templates/spec-full-template.md",
        "standards/project-spec/versions/1.8/templates/spec-light-template.md",
        "standards/project-spec/versions/1.8/templates/spec-standard-template.md",
    }
)

# Repository tooling that became executable after the mode-policy anchor. It cannot
# join `_EXECUTABLE_ALLOWLIST`: that set is pinned to the anchor tree by the equality
# above it, so anything added there would fail the anchor-inventory assertion instead.
#
# This assertion reads the INDEX (`git ls-files -s`), so a new executable is invisible
# to it until it is staged: a gate run that is green on an untracked script goes red on
# the next run, after the commit. Add the entry in the same change that adds the script.
_POST_ANCHOR_TOOLING_EXECUTABLES = frozenset(
    {
        "scripts/bootstrap-worktree.sh",
        "scripts/build-agent-handoff-session-start.sh",
        "scripts/build-gh-workflow.sh",
        "scripts/wheel-runtime-stamp.sh",
    }
)


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        encoding="utf-8",
    ).stdout


def _index_entries() -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    for line in _git("ls-files", "-s").splitlines():
        metadata, path = line.split("\t", maxsplit=1)
        mode, blob, _stage = metadata.split()
        entries[path] = (mode, blob)
    return entries


def _tree_entries(revision: str) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    for line in _git("ls-tree", "-r", revision).splitlines():
        metadata, path = line.split("\t", maxsplit=1)
        mode, _kind, blob = metadata.split()
        entries[path] = (mode, blob)
    return entries


def test_git_mode_policy__classifies_and_normalizes_the_complete_anchor_inventory() -> None:
    entries = _index_entries()
    anchor_entries = _tree_entries(_MODE_POLICY_ANCHOR)
    classified = (
        _EXECUTABLE_ALLOWLIST | _MUTABLE_NORMALIZATION_ALLOWLIST | _IMMUTABLE_PROJECTION_EXCLUSIONS
    )
    anchor_executables = {
        path for path, (mode, _blob) in anchor_entries.items() if mode == "100755"
    }

    assert len(anchor_executables) == 43
    assert anchor_executables == classified
    assert classified <= entries.keys()
    assert {path for path, (mode, _blob) in entries.items() if mode == "100755"} == (
        _EXECUTABLE_ALLOWLIST
        | _IMMUTABLE_PROJECTION_EXCLUSIONS
        | _POST_ANCHOR_IMMUTABLE_PROJECTION_EXECUTABLES
        | _POST_ANCHOR_TOOLING_EXECUTABLES
    )
    assert {path: entries[path][0] for path in _MUTABLE_NORMALIZATION_ALLOWLIST} == dict.fromkeys(
        _MUTABLE_NORMALIZATION_ALLOWLIST, "100644"
    )


def test_git_mode_policy__preserves_predecessor_versioned_resource_blobs_and_modes() -> None:
    predecessor = _tree_entries(_PREDECESSOR)
    current = _index_entries()
    predecessor_versioned_resources = {
        path: entry
        for path, entry in predecessor.items()
        if path.startswith("standards/") and "/versions/" in path
    }

    assert {path: current[path] for path in predecessor_versioned_resources} == (
        predecessor_versioned_resources
    )
