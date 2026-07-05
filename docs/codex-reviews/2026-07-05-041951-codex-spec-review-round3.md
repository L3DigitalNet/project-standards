### Executive summary

Claude Code’s round-3 corrections resolve the three remaining prior findings. Appendix B is now consistently classified as template-owned, replaced from the target tier, covered by precheck refusal, and pinned by tests. The `source_not_upgradeable` JSON path is now explicitly tested, and the stale load-bearing-property anchor is fixed.

New internet research was limited to rechecking the Python filesystem assumptions that still underpin the write model. No external-doc conflict was found.

### Verdict

No significant findings remain

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md
* Prior audit issue count: 3
* Resolved issue count: 3
* Still open issue count: 0
* Partially resolved issue count: 0
* New issue count: 0
* Regression count: 0
* Significant findings remaining: No

### Adversarial review performed

I re-read the revised spec and retested the prior open areas: Appendix B ownership, source upgradeability precheck coverage, target-tier Appendix B replacement, JSON failure coverage for `source_not_upgradeable`, and the stale internal anchor. I also rechecked repository evidence for template tier structure, bundled-template parity, current parser/validator limits, CLI/write-helper reuse claims, docs scope, versioning classification, and acceptance-criteria false positives.

I did not run mutating gates such as pytest, coverage, ruff, basedpyright, pip-audit, or any command that could create implementation artifacts.

### Prior findings status

#### SA-NEW-001: Appendix B is checked as canonical but not transformed to the target tier

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec now classifies Appendix B as template-owned with Appendix A/D, states Appendix A/B/D are replaced wholesale from the target tier, explains edited Appendix B is refused as `source_not_upgradeable`, and adds tests requiring target-tier Appendix B in Light→Standard and Standard→Full outputs. Repository template diffs confirm Appendix B is tier-variant, and bundled templates still match standards templates.
* Remaining action for Claude Code: None.

#### SA-NEW-002: `source_not_upgradeable` is omitted from the JSON-specific test list

* Previous severity: Low
* Current status: Resolved
* Evidence: The `--json` testing bullet now explicitly includes `source_not_upgradeable` for gap prose, edited Appendix A/B/D, and non-canonical subsection sources, with `ok:false`, `code:"source_not_upgradeable"`, and a deviation message.
* Remaining action for Claude Code: None.

#### SA-NEW-003: Stale internal anchor remains after renaming the load-bearing section

* Previous severity: Low
* Current status: Resolved
* Evidence: The old `#the-load-bearing-invariant` anchor no longer appears; the cross-reference now points to `#the-load-bearing-property--enforced-not-assumed`, matching the current section heading and table of contents.
* Remaining action for Claude Code: None.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

None found.

### Internet research performed

* Source name: Python documentation, `os.replace`
* URL: https://docs.python.org/3/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: Atomic replacement assumption in the write model.
* Relevant conclusion: Official docs still state that replacing an existing file is supported when permitted and that successful replacement is atomic on POSIX.

* Source name: Python documentation, `pathlib.Path.mkdir`
* URL: https://docs.python.org/3/library/pathlib.html#pathlib.Path.mkdir
* Access date: 2026-07-05
* What it was used to verify: Parent auto-creation behavior.
* Relevant conclusion: Official docs confirm `parents=True` creates missing parents, and `exist_ok=True` still raises when the existing path is not a directory.

* Source name: Python documentation, `pathlib.Path.samefile`
* URL: https://docs.python.org/3/library/pathlib.html#pathlib.Path.samefile
* Access date: 2026-07-05
* What it was used to verify: Same-file detection for `-o OUT == SRC`.
* Relevant conclusion: Official docs confirm `Path.samefile()` exists and can raise `OSError` when a path cannot be accessed, matching the spec’s decision to leave fallback details to planning.

### Read-only validation performed

* `pwd`: confirmed repository root is `/home/chris/projects/project-standards`.
* `git status --short`: found only untracked prior review artifacts under `docs/codex-reviews/`; no tracked working-tree edits.
* `git branch --show-current`: confirmed branch `testing`.
* `git log --oneline -n 10`: confirmed latest commit is the round-3 spec revision addressing SA-NEW-001..003.
* Inspected the revised spec with `nl -ba` and `sed`: re-inventoried requirements, ownership model, write model, JSON contract, tests, acceptance criteria, and open questions.
* `git show --unified=80 --stat 9d5fc06 -- <spec>`: confirmed the round-3 diff targeted Appendix B ownership, JSON coverage, and the stale anchor.
* `rg --files`: identified relevant source, templates, fixtures, tests, docs, workflows, and metadata.
* Inspected `registry.py`, `document.py`, `validate.py`, `specs/cli.py`, `commands/new.py`, `test_spec_new_cli.py`, `test_template_conformance.py`, `src/project_standards/README.md`, `src/project_standards/cli.py`, and `meta/versioning.md`.
* `cmp -s` on standards vs bundled light/standard/full templates: confirmed bundled templates match standards templates.
* `diff -u` on Appendix B between Light/Standard and Standard/Full templates: confirmed Appendix B differs by tier.
* `rg` over the spec: confirmed Appendix B appears consistently in precheck, ownership, replacement, error, test, acceptance, and non-goal text; confirmed the stale anchor is absent.
* `rg` over templates: confirmed tier section, subsection, References, and appendix structure matches the spec’s target-unit assumptions.
* Consulted official Python docs for `os.replace`, `Path.mkdir`, and `Path.samefile`.

### Recommended planning/implementation validation

* Run only after implementation: targeted `tests/test_spec_upgrade.py` covering Appendix B target replacement, edited Appendix B refusal, gap-content refusal, modified Appendix A/D refusal, non-canonical subsection refusal, canonical subsection insertion, aligned-fixture fidelity, and output validation.
* Run only after implementation: targeted `tests/test_spec_upgrade_cli.py` covering flag conflicts, all JSON slugs including `source_not_upgradeable`, in-place mode preservation, output overwrite behavior, symlink/non-regular refusals, parent auto-creation, output-equals-source checks, and no-write preview.
* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: dogfood `project-standards spec upgrade` preview output piped into spec validation without writing repository files.

### Final recommendation

No significant findings remain; the audit/fix loop can stop

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-05-project-spec-tooling-spec3-design.md
* Audit round: 3
* Open issue IDs:
* Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-NEW-001, SA-NEW-002, SA-NEW-003
* Superseded issue IDs:
* Significant findings remaining: No
* Next audit should focus on: no follow-up audit needed unless the specification changes again.