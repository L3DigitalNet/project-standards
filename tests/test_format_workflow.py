from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "format.yml"


# YAML parses the top-level `on:` key as the boolean True (the "Norway problem"),
# so the mapping is genuinely not str-keyed; dict[Any, Any] is the honest type and
# keeps basedpyright strict happy when indexing with True.
def _load() -> dict[Any, Any]:
    return cast("dict[Any, Any]", yaml.safe_load(_WF.read_text(encoding="utf-8")))


def test_workflow_is_reusable_with_boolean_prettier_input() -> None:
    data = _load()
    call = data[True]["workflow_call"]  # PyYAML parses the `on:` key as boolean True
    inp = call["inputs"]["prettier"]
    assert inp["type"] == "boolean"
    assert inp["default"] is True


def test_still_dual_role_direct_triggers_present() -> None:
    on = _load()[True]
    assert "push" in on and "pull_request" in on and "workflow_call" in on


def test_optout_is_job_level_and_coercion_safe() -> None:
    job = _load()["jobs"]["prettier"]
    # Job-level `if:` (SA-NEW-003) using the string-safe form (SA-001).
    assert job["if"].strip() == "${{ format('{0}', inputs.prettier) != 'false' }}"


def test_prettier_check_is_repo_wide_and_pin_matches_package_json() -> None:
    import json

    pkg: dict[str, Any] = json.loads((_WF.parent.parent.parent / "package.json").read_text("utf-8"))
    pin = pkg["devDependencies"]["prettier"]  # SSOT for the pin (no hardcoded duplicate)
    steps = _load()["jobs"]["prettier"]["steps"]
    runs = [str(s.get("run", "")) for s in steps]
    # Assert on parsed `run:` commands, not raw text (CR-NEW-002): the workflow's
    # header comment legitimately mentions `npm ci`, so a raw-text `"npm ci" not in
    # text` check would false-fail. The pinned repo-wide check must run; no step
    # may invoke `npm ci` (a consumer checkout has no lockfile).
    assert any(f"npx --yes prettier@{pin} --check ." in r for r in runs)
    assert not any("npm ci" in r for r in runs)


@pytest.mark.parametrize(
    "input_value,expected_run",
    [
        (None, True),  # direct push/PR run: inputs context empty -> runs
        (True, True),  # reusable caller prettier: true -> runs
        (False, False),  # reusable caller prettier: false -> job skipped
    ],
)
def test_optout_truth_table(input_value: object, expected_run: bool) -> None:
    # Model GitHub's `format('{0}', x) != 'false'`: None -> '' , bool -> 'true'/'false'.
    rendered = "" if input_value is None else str(input_value).lower()
    runs = rendered != "false"
    assert runs is expected_run
