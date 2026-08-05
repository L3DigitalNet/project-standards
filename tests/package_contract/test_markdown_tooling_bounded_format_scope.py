"""TC-T16-001 (REQ-088, issue #88): bound Prettier to the declared corpus.

Markdown Tooling 1.12 documents ``prettier --check .`` as its local verification
command (``versions/1.12/adopt.md:66``, ``README.md:26``, ``agent-summary.md:16``)
while the same guide separately says to pass ``markdown_globs`` and
``config_globs``. The executable half wins, so a consumer running the guide's
command traverses every Prettier-supported language and every Git-excluded
scratch tree.

Each test below pairs the *reproduction* — what the shipped dot command actually
selects, which stays true forever because it is raw Prettier behavior — with the
*requirement*: the same corpus reached through the command the 1.13 payload
renders into its managed instruction block. Keeping both halves in one test means
a lost reproduction fails loudly instead of quietly weakening the proof.

The corpus authority is ``markdown_globs`` + ``config_globs``; nothing here adds
a third glob source, and ``test_no_new_glob_authority__*`` pins that.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.issue_regressions.tool_oracle import ToolOutcome, prettier_check

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-tooling"
_PREDECESSOR = _FAMILY / "versions/1.12"
_SUCCESSOR = _FAMILY / "versions/1.13"

# The immutable predecessor's published aggregate digest (standard.toml:62).
_PREDECESSOR_DIGEST = "sha256:105d742c188f78cd908cd715a396722912d031114ea1e5e6445d1dc879a1e7b8"

# What the declared corpus must select in the fixture below: declared extension,
# tracked, and mis-formatted. Everything else in the fixture is out of corpus for
# a named reason (undeclared language, or excluded by one of three Git mechanisms).
_IN_CORPUS = ("config.json", "doc.md", "nested/tracked.md")
_UNDECLARED_LANGUAGES = ("app.ts", "page.css")
_GITIGNORED_SCRATCH = ".venv/lib/site-packages/pkg/README.md"
_EXCLUDE_FILE_SCRATCH = (
    ".scratch/review/basedpyright.json",
    ".scratch/review/notes.md",
)
_UNPARSEABLE_SCRATCH = ".scratch/review/invalid-plan.json"
_NESTED_GITIGNORED = "nested/ignored-by-nested.md"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Markdown, JSON, TypeScript, and CSS bodies that the shipped `.prettierrc.json`
# (useTabs, semi=false, proseWrap=never) all rewrite, so "selected" and "reported
# as different" are the same set and the probe needs no second measurement.
_MISFORMATTED_MARKDOWN = "# Title\n\n-   item\n"
_MISFORMATTED_JSON = '{"alpha":1,"beta":2}\n'
_MISFORMATTED_TYPESCRIPT = "const  value=1;\n"
_MISFORMATTED_CSS = "a{color:red}\n"


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _write(root: Path, relative: str, body: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture
def mixed_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build issue #88's mixed tracked/ignored corpus as a real Git repository.

    All three Git exclusion mechanisms are present because they behave
    differently: Prettier reads a root ``.gitignore`` by default, reads a *nested*
    ``.gitignore`` never, and reads ``.git/info/exclude`` never. Git honors all
    three. That asymmetry is the whole of issue #88 and is measured directly by
    ``test_probe__prettier_ignore_discovery__is_root_only``.
    """
    # ANSI in Prettier's diagnostics would make the parsed selection depend on
    # terminal color policy instead of on file matching (tool_oracle.py:269-275).
    monkeypatch.setenv("NO_COLOR", "1")

    root = tmp_path / "consumer"
    root.mkdir()
    _git(root, "init", "--quiet")

    # Anchoring trap: `.prettierrc.json` overrides use `**/*.md`, resolved relative
    # to the config file's own directory. A config read from the repository root
    # would silently not apply to these probes, so the fixture carries its own copy
    # of the payload's shipped bytes.
    (root / ".prettierrc.json").write_bytes((_SUCCESSOR / "resources/prettierrc.json").read_bytes())

    _write(root, ".gitignore", ".venv/\n")
    (root / ".git/info/exclude").write_text(".scratch/\n", encoding="utf-8")

    for relative in _IN_CORPUS:
        _write(
            root,
            relative,
            _MISFORMATTED_MARKDOWN if relative.endswith(".md") else _MISFORMATTED_JSON,
        )
    _write(root, "app.ts", _MISFORMATTED_TYPESCRIPT)
    _write(root, "page.css", _MISFORMATTED_CSS)
    _write(root, _GITIGNORED_SCRATCH, _MISFORMATTED_MARKDOWN)
    _write(root, _EXCLUDE_FILE_SCRATCH[0], _MISFORMATTED_JSON)
    _write(root, _EXCLUDE_FILE_SCRATCH[1], _MISFORMATTED_MARKDOWN)
    # Issue #88's first reproduction turns on this file: an intentionally invalid
    # test artifact inside excluded scratch, which makes Prettier exit 2.
    _write(root, _UNPARSEABLE_SCRATCH, "{\n")
    _write(root, "nested/.gitignore", "ignored-by-nested.md\n")
    _write(root, _NESTED_GITIGNORED, _MISFORMATTED_MARKDOWN)

    # No commit: `git ls-files` reads the index, and committing would need an
    # identity this fixture has no reason to require.
    _git(root, "add", "-A")
    return root


def _reported(outcome: ToolOutcome) -> tuple[str, ...]:
    """Return the paths Prettier named, from either its list or its diagnostics.

    The two invocation shapes report differently: `--list-different` prints bare
    paths, while `--check` prints `[warn] <path>` plus prose banners ("Checking
    formatting...", "Code style issues found in N files."). Whitespace is the
    discriminator -- every banner has some, no fixture path does -- so a path
    containing a space would be dropped. None exists here, and introducing one
    would need a different parser rather than a wider filter.
    """
    paths: set[str] = set()
    for line in _ANSI.sub("", outcome.output).splitlines():
        stripped = line.strip()
        if stripped.startswith(("[error]", "[warn]")):
            stripped = stripped.split("]", 1)[1].strip().split(":", 1)[0].strip()
        if stripped and not stripped.startswith("[") and not any(map(str.isspace, stripped)):
            paths.add(stripped)
    return tuple(sorted(paths))


def _documented_dot_outcome(root: Path) -> ToolOutcome:
    """Run the command 1.12 documents verbatim: `prettier --check .`."""
    return prettier_check(_ROOT, root, (".",), config_path=root / ".prettierrc.json")


def _rendered_local_command(overrides: JsonObject) -> str | None:
    """Return the local Prettier command the payload renders, if it renders one.

    T16's fix belongs in the managed instruction block because that block already
    knows the selected globs; until it renders a command there is nothing for a
    consumer or an agent to run except the unbounded dot form.
    """
    payload = _payload(_SUCCESSOR)
    config = load_option_schema(_SUCCESSOR, payload.manifest).resolve_options(overrides)
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="markdown-tooling",
            version=payload.manifest.payload.version,
            provider_id="render-semantic",
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots={
                "planned_contribution": {
                    "id": "agents-instructions",
                    "target": "AGENTS.md",
                    "adapter": "markdown-block",
                    "scope": "block:markdown-tooling",
                }
            },
        )
    )
    assert result.content is not None
    block = result.content.decode()
    for line in block.splitlines():
        candidate = line.strip()
        if "prettier" in candidate and candidate.startswith(("git ", "npx ")):
            return candidate
    return None


# `xargs` maps any child status in 1..125 onto 123, so the normative command
# cannot re-emit Prettier's own 1-vs-2 distinction. Pass/fail is preserved, and
# the discriminator that matters here is whether any `[error]` diagnostic was
# produced at all -- see `_assert_no_hard_error`.
_BOUNDED_STATUSES = frozenset({0, 1, 123})


def _assert_no_hard_error(outcome: ToolOutcome) -> None:
    """Assert a bounded run produced findings at most, never a hard error.

    Issue #88's symptom is a formatting check that turns into an unrecoverable
    parse or permission error on files the repository already excluded. Prettier
    reports that class as `[error]`, so its absence is the direct proof, and it
    survives the status collapse `xargs` imposes.
    """
    assert "[error]" not in _ANSI.sub("", outcome.output), outcome.output
    assert outcome.returncode in _BOUNDED_STATUSES, outcome.output


def _bounded_outcome(root: Path, command: str) -> ToolOutcome:
    """Execute a rendered command against the fixture through the pinned tools."""
    node_modules = root / "node_modules"
    node_modules.symlink_to((_ROOT / "node_modules").resolve(), target_is_directory=True)
    try:
        completed = subprocess.run(
            ["bash", "-c", command],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        node_modules.unlink()
    return ToolOutcome(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def test_red__undeclared_languages__must_leave_the_bounded_selection(
    mixed_corpus: Path,
) -> None:
    """TC-T16-001: only `markdown_globs` + `config_globs` languages are traversed."""
    reproduction = _reported(_documented_dot_outcome(mixed_corpus))
    assert set(_UNDECLARED_LANGUAGES) <= set(reproduction), (
        "reproduction lost: the documented dot command no longer reaches "
        f"undeclared languages; it reported {reproduction}"
    )

    command = _rendered_local_command({})
    assert command is not None, (
        "package 1.13 renders no bounded local Prettier command, so the only "
        "executable guidance is still the unbounded `prettier --check .`"
    )
    bounded = _reported(_bounded_outcome(mixed_corpus, command))
    assert not set(_UNDECLARED_LANGUAGES) & set(bounded)


def test_red__git_excluded_scratch__must_leave_the_bounded_selection(
    mixed_corpus: Path,
) -> None:
    """TC-T16-001: `.git/info/exclude` scratch is never traversed."""
    outcome = _documented_dot_outcome(mixed_corpus)
    reproduction = _reported(outcome)
    assert set(_EXCLUDE_FILE_SCRATCH) <= set(reproduction)
    assert _UNPARSEABLE_SCRATCH in reproduction
    # Issue #88 comment 1: the failure is a hard error, not a formatting finding.
    assert outcome.returncode == 2, outcome.output

    command = _rendered_local_command({})
    assert command is not None, (
        "package 1.13 renders no bounded local Prettier command, so Git-excluded "
        "scratch is still reachable by the documented verification step"
    )
    bounded = _bounded_outcome(mixed_corpus, command)
    _assert_no_hard_error(bounded)
    assert not {path for path in _reported(bounded) if path.startswith(".scratch/")}


def test_red__gitignored_scratch__must_leave_the_bounded_selection(
    mixed_corpus: Path,
) -> None:
    """TC-T16-001: issue #88 comment 2's cache trees stay out of the selection."""
    command = _rendered_local_command({})
    assert command is not None, (
        "package 1.13 renders no bounded local Prettier command, so there is "
        "nothing to prove ignored generated trees against"
    )
    bounded = _reported(_bounded_outcome(mixed_corpus, command))
    assert _GITIGNORED_SCRATCH not in bounded
    assert _NESTED_GITIGNORED not in bounded


def test_red__rendered_command__selects_exactly_the_declared_corpus(
    mixed_corpus: Path,
) -> None:
    """TC-T16-001 set parity: the rendered command's corpus is the declared one."""
    command = _rendered_local_command({})
    assert command is not None, (
        "package 1.13's managed instruction block renders scope prose but no "
        "runnable command, so set parity cannot be measured"
    )
    bounded = _bounded_outcome(mixed_corpus, command)
    _assert_no_hard_error(bounded)
    assert _reported(bounded) == _IN_CORPUS


def test_red__no_new_glob_authority__rendered_command_follows_selected_globs(
    mixed_corpus: Path,
) -> None:
    """TC-T16-001: the corpus is `markdown_globs` + `config_globs`, nothing else."""
    # Negative control, passing today: the fix must not widen the option surface.
    assert (_SUCCESSOR / "config.schema.json").read_bytes() == (
        _PREDECESSOR / "config.schema.json"
    ).read_bytes()

    narrowed: JsonObject = {"markdown_globs": ["nested/**/*.md"], "config_globs": ["**/*.json"]}
    command = _rendered_local_command(narrowed)
    assert command is not None, (
        "package 1.13 renders no bounded local Prettier command, so a narrowed "
        "glob selection cannot reach the local recipe at all"
    )
    for glob in ("nested/**/*.md", "**/*.json"):
        assert glob in command
    assert "**/*.yml" not in command
    bounded = _reported(_bounded_outcome(mixed_corpus, command))
    assert "doc.md" not in bounded
    assert "nested/tracked.md" in bounded


def test_probe__prettier_ignore_discovery__is_root_only(mixed_corpus: Path) -> None:
    """Characterize why glob bounding alone cannot close issue #88.

    Prettier's default ignore set is ``[.gitignore, .prettierignore]`` resolved
    from the working directory only. A nested ``.gitignore`` is not consulted and
    ``.git/info/exclude`` is never consulted, while ``git ls-files`` honors all
    three. This is the evidence for choosing a tracked-file selection over a
    pure-glob one, and for rejecting ``--ignore-path .git/info/exclude`` (whose
    patterns would anchor to ``.git/info/``).
    """
    reported = _reported(_documented_dot_outcome(mixed_corpus))

    assert _GITIGNORED_SCRATCH not in reported, "root .gitignore should be honored"
    assert _NESTED_GITIGNORED in reported, "nested .gitignore is not read by Prettier"
    assert set(_EXCLUDE_FILE_SCRATCH) <= set(reported), ".git/info/exclude is not read"

    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md", "*.json", "*.jsonc", "*.yml", "*.yaml"],
        cwd=mixed_corpus,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    selected = {entry for entry in tracked.split("\0") if entry}

    assert selected == {*_IN_CORPUS, ".prettierrc.json"}
    assert not {path for path in selected if path.startswith((".venv/", ".scratch/"))}
    assert _NESTED_GITIGNORED not in selected


def test_negative_control__predecessor_1_12__remains_byte_immutable() -> None:
    """The released 1.12 payload must not move while 1.13 is authored."""
    manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    integrity = validate_payload_integrity(_PREDECESSOR, manifest)

    assert manifest.payload.version.value == "1.12"
    assert integrity.aggregate_digest.value == _PREDECESSOR_DIGEST
