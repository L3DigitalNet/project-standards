### Executive summary

Claude Code’s corrections resolved the blocking CLI and `--json` contract issues from round 1. The revised spec is much closer to plan-ready, but two non-blocking specification gaps remain: the write-safety model still does not cover symlinked parent directories or parent-directory cleanup after failed writes, and the title value grammar still does not define how `--title` is rendered safely into the Markdown H1.

New internet research was required for Python filesystem behavior. Official Python 3.14 documentation supports the spec’s use of `os.replace` for atomic same-filesystem replacement, but also confirms why the remaining symlink-parent edge needs an explicit policy.

### Verdict

Needs minor specification correction before planning/implementation

### Audit loop status

* Audit type: Follow-up audit
* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md
* Prior audit issue count: 5
* Resolved issue count: 3
* Still open issue count: 0
* Partially resolved issue count: 2
* New issue count: 0
* Regression count: 0
* Significant findings remaining: Yes

### Adversarial review performed

I re-read the revised spec and compared it against the prior SA-001 through SA-005 ledger. I retested the revised CLI conflict matrix, JSON contract, tolerant discovery design, write model, value grammar, test coverage claims, acceptance criteria, versioning claims, and external Python filesystem assumptions against current repository files and official Python 3.14 documentation.

The strongest retests were: whether every formerly-deferred CLI behavior is now frozen; whether `new` now satisfies the README’s universal `--json` tooling contract; whether tolerant discovery avoids weakening validate/lint’s existing `DiscoveryError` contract; whether the write-safety model really blocks symlink redirection; and whether acceptance criteria could still pass while generated Markdown is malformed for realistic title input.

### Prior findings status

#### SA-001: CLI conflict and parent-directory behavior are both specified and unresolved

* Previous severity: High
* Current status: Resolved
* Evidence: The revised spec now freezes the flag conflict matrix at lines 89-99, including `PATH` + `--stdout`, missing `PATH`, `--force` + `--stdout`, and `--force` without a valid `PATH`. Parent directory policy is now chosen at lines 167-169: missing parents are auto-created, and parent path components that are non-directories fail with exit 2.
* Remaining action for Claude Code: None for the prior blocking ambiguity. Later corrections should only refine the safety edge noted under SA-004.

#### SA-002: `new` omits the project-spec JSON output contract

* Previous severity: High
* Current status: Resolved
* Evidence: The revised CLI surface includes `--json` at lines 72-85. Invariants I7 and Component 6 define JSON behavior at lines 67 and 189-218. Acceptance criteria require every command outcome to support `--json` at lines 238-239. This now aligns with the README tooling contract at `standards/project-spec/README.md:101-103`.
* Remaining action for Claude Code: None for the spec-level contract. Implementation planning should include explicit parser-error JSON tests, including bad `--profile` and flag conflicts.

#### SA-003: Empty-corpus discovery conflicts with the current discovery helper contract

* Previous severity: Medium
* Current status: Resolved
* Evidence: The revised spec now adds a distinct `collect_existing_spec_ids(cfg)` helper at lines 107-109 and defines its tolerant behavior at lines 154-158. This no longer asks `new` to reuse `collect_spec_paths` directly, whose current implementation intentionally raises `DiscoveryError` for no config, empty include, and zero-match include in `src/project_standards/specs/config.py:59-75`.
* Remaining action for Claude Code: None. Implementation should preserve existing `collect_spec_paths` behavior for `validate`/`lint`.

#### SA-004: Write safety does not address partial writes, symlinks, or non-regular targets

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The revised spec now requires atomic temp-file-plus-`os.replace` writes, target symlink refusal, non-regular target refusal, and temp cleanup on write error at lines 48, 68, and 160-169. Official Python docs confirm `os.replace` replaces an existing file and is atomic when successful on the same filesystem. However, the spec only refuses when `PATH` itself is a symlink. It does not define behavior when a parent directory component is a symlink. `Path.exists()` and `Path.is_file()` normally follow symlinks, while `Path.is_symlink()` checks only the path object itself, so `docs/link/spec.md` can still resolve through a symlinked parent to a target outside the apparent tree. The spec also says failures leave the filesystem untouched at line 169, but parent directories are created before the atomic write at line 167; if the later write fails, newly-created parent directories may remain.
* Remaining action for Claude Code: Clarify whether symlinked parent directories are allowed or refused for write targets, and whether newly-created parent directories are intentionally left behind after later write failures or should be rolled back best-effort.

#### SA-005: Flag value escaping is underspecified beyond quotes and colons

* Previous severity: Medium
* Current status: Partially resolved
* Evidence: The revised spec now rejects empty/control-character values and requires PyYAML scalar serialization for frontmatter at lines 55 and 133-136. That resolves the frontmatter corruption concern. The remaining gap is title rendering into the Markdown H1 at line 129. A title containing backticks, such as `Use \`uv\` for Specs`, can be YAML-safe but still break or distort the generated H1 code-span formatting because the spec only says the back-ticked name is substituted. Existing templates wrap the H1 title in backticks at `src/project_standards/specs/templates/spec-light-template.md:19`, `spec-standard-template.md:19`, and `spec-full-template.md:19`.
* Remaining action for Claude Code: Define the Markdown H1 title policy: reject backticks in `--title`, escape/render them with a longer code-span delimiter, or stop wrapping substituted titles in code spans.

### New blocking issues

None found.

### New non-blocking issues

None found.

### Regressions

None found.

### Remaining ambiguities and decisions needed

* Ambiguity: Are symlinked parent directories allowed in `PATH`?
* Why it matters: The spec refuses a symlink target path but still allows writes through symlinked parents unless it explicitly checks every parent component.
* Recommended clarification: State whether any symlink in the destination parent chain is refused, or document that parent symlink traversal is accepted.
* Blocking or non-blocking: Non-blocking.

* Ambiguity: Are auto-created parent directories rolled back after a later write failure?
* Why it matters: The spec says failures leave the filesystem untouched, but parent directory creation is itself a filesystem mutation.
* Recommended clarification: Either narrow the guarantee to “destination file untouched/no partial file” or require best-effort cleanup of directories created by this invocation.
* Blocking or non-blocking: Non-blocking.

* Ambiguity: How is `--title` escaped for the Markdown H1 when it contains backticks?
* Why it matters: Frontmatter can remain valid while the H1 Markdown rendering is malformed.
* Recommended clarification: Reject backticks in `--title`, or specify a Markdown code-span escaping strategy.
* Blocking or non-blocking: Non-blocking.

### Internet research performed

* Source name: Python 3.14 `os` documentation
* URL: https://docs.python.org/3.14/library/os.html#os.replace
* Access date: 2026-07-05
* What it was used to verify: Current `os.replace` overwrite and atomic rename behavior.
* Relevant conclusion: `os.replace` can silently replace an existing file when permitted, and successful replacement is atomic on the same filesystem.

* Source name: Python 3.14 `pathlib` documentation
* URL: https://docs.python.org/3.14/library/pathlib.html
* Access date: 2026-07-05
* What it was used to verify: Current `Path.exists`, `Path.is_file`, `Path.is_dir`, and `Path.is_symlink` behavior around symlinks.
* Relevant conclusion: `exists` and `is_file` normally follow symlinks, while `is_symlink` identifies the path itself as a symlink, including broken symlinks. This supports refusing target symlinks but does not cover symlinked parents unless explicitly checked.

* Source name: Python 3.14 `tempfile` documentation
* URL: https://docs.python.org/3.14/library/tempfile.html
* Access date: 2026-07-05
* What it was used to verify: Current named temporary file and secure temporary file creation behavior.
* Relevant conclusion: The temp-file approach is feasible, but implementation details still need to preserve same-directory replacement and cleanup expectations.

### Read-only validation performed

* `git status --short`: confirmed the spec is modified and a round-1 review artifact is untracked; no files were changed by this audit.
* `git branch --show-current`: confirmed branch `testing`.
* `git log --oneline -n 10`: confirmed recent history includes Spec #1 implementation and the Spec #2 design commit.
* Inspected the revised spec with `nl -ba`: re-inventoried requirements, invariants, CLI matrix, discovery design, write model, error contract, tests, acceptance criteria, non-goals, and open implementation questions.
* `git diff -- docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md`: confirmed the round-1 corrections added the CLI matrix, JSON contract, tolerant discovery, atomic write model, value grammar, and expanded tests.
* Inspected `standards/project-spec/README.md`: confirmed the README-level tooling contract still says every command offers machine-readable `--json`.
* Inspected `src/project_standards/specs/config.py`: confirmed current `collect_spec_paths` raises `DiscoveryError` for no config, empty include, and zero matches.
* Inspected `src/project_standards/specs/cli.py`: confirmed existing parser/command patterns and JSON support for existing commands.
* Inspected `src/project_standards/specs/registry.py`, `document.py`, and `commands/validate.py`: confirmed template registry, frontmatter parsing, validation behavior, sentinel pattern, and profile validation.
* Inspected bundled templates under `src/project_standards/specs/templates/` and `standards/project-spec/templates/`: confirmed frontmatter keys, sentinel, placeholder fields, and H1 backtick title shape.
* Inspected `pyproject.toml`, `uv.lock`, `.project-standards.yml`, `.github/workflows/validate-specs.yml`, `TODO.md`, and `docs/handoff/specs-plans.md`: confirmed Python 3.14 target, PyYAML dependency, coverage gate, workflow commands, project-spec exclusion status, and current handoff pointer state.
* Inspected `tests/test_spec_cli.py`: confirmed existing command tests and current JSON/exit-code expectations for Spec #1 commands.
* Performed targeted `rg` searches for PyYAML, project-spec, templates, sentinel, and spec tooling references.
* Opened official Python 3.14 docs for `os.replace`, `pathlib`, and `tempfile`: verified external filesystem assumptions.

### Recommended planning/implementation validation

* Run only after implementation: `uv run ruff format --check .`
* Run only after implementation: `uv run ruff check .`
* Run only after implementation: `uv run basedpyright`
* Run only after implementation: `uv run coverage run -m pytest`
* Run only after implementation: `uv run coverage report`
* Run only after implementation: `uv run pip-audit`
* Run only after implementation: targeted `new` tests for success, `--stdout`, `--json`, `--force`, ID collision, bad ID, ID exhaustion, empty discovery, malformed config, malformed neighbor spec, self-validation failure, existing regular file, existing directory, target symlink, broken target symlink, symlinked parent directory, parent path that is a file, write permission failure, and atomic write cleanup.
* Run only after implementation: title escaping tests for apostrophes, colons, `#`, leading/trailing spaces, non-ASCII, backticks, empty strings, newline/carriage return, and control characters.
* Run only after implementation: parser-error JSON tests for bad `--profile`, all flag conflicts, bad field values, and missing `PATH`.

### Final recommendation

Claude Code should revise the specification using the findings above

### Review ledger for next loop

* Spec path: /home/chris/projects/project-standards/docs/superpowers/specs/2026-07-04-project-spec-tooling-spec2-design.md
* Audit round: 2
* Open issue IDs: SA-004, SA-005
* Resolved issue IDs: SA-001, SA-002, SA-003
* Superseded issue IDs:
* Significant findings remaining: Yes
* Next audit should focus on: whether the revised spec defines symlinked parent directory policy, parent-directory cleanup or narrowed write-failure guarantees, and Markdown H1 escaping/rejection for titles containing backticks.