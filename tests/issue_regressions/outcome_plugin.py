"""Minimal pytest reporter used by the regression-ledger subprocess runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol


class _Report(Protocol):
    nodeid: str
    when: str
    outcome: str


_RECORDS: list[dict[str, object]] = []


def pytest_runtest_logreport(report: _Report) -> None:
    _RECORDS.append(
        {
            "nodeid": report.nodeid,
            "when": report.when,
            "outcome": report.outcome,
            "wasxfail": bool(getattr(report, "wasxfail", False)),
        }
    )


def pytest_sessionfinish() -> None:
    target = os.environ.get("ISSUE_REGRESSION_OUTCOMES")
    if target:
        Path(target).write_text(json.dumps(_RECORDS, sort_keys=True), encoding="utf-8")
