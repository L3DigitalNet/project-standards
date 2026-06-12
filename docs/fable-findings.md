# Fable review findings — validation source files in `src/`

**Date:** 2026-06-12 · **Branch:** `testing` · **Phase:** 1 (read-only review; no target files modified)

**Scope reviewed:** `src/project_standards/validate_frontmatter.py`, `validate_id.py`, `validate_references.py`, `id_format.py`, `registry.py`, and the schema contracts `schemas/markdown-frontmatter.schema.json` + `schemas/registry.json`. Method: three parallel module reviewers, findings re-verified against source by the consolidating session. Cross-validator duplicates are merged (the shared `collect_paths` / `load_config` hub in `validate_frontmatter.py` is imported by all other validators, so hub bugs propagate to every console script).

Sorted by severity. Phase 2 complete 2026-06-12: all 58 findings selected; 55 implemented (one commit per finding or inseparable pair, IDs in each commit subject), 3 skipped with rationale below.

---

## High

`F1` | Reliability | Severity: High | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:222-225` (also `validate_id.py:182-185`, `validate_references.py:44-48`)
- **Issue:** All three validators read files with `read_text(encoding="utf-8-sig")` and catch only `OSError` (plus `FrontmatterParseError` where relevant). A non-UTF-8 file matched by a glob raises `UnicodeDecodeError` — a `ValueError`, not an `OSError` — which escapes as an uncaught traceback and aborts the whole CI run, violating the module's own contract that parse problems "must surface as a clean validation error rather than an uncaught traceback" (`validate_frontmatter.py:48-54`). This is the only unhandled-exception path reachable from ordinary corpus input.
- **Fix:** Widen the catch to `(OSError, UnicodeDecodeError)` at all three read sites and return/emit a per-file "cannot read file" error, so one bad file fails that file, not the run.
- **Status:** implemented (commit f8c9697)

`F2` | Correctness | Severity: High | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:233-240` (write path `296-319`)
- **Issue:** `_replace_frontmatter_id`'s regex only understands single-line `id:` values. For a YAML block scalar (`id: >-` with an indented continuation line), it replaces only the `id: >-` line and orphans the continuation, producing invalid YAML — then `fix_file` writes the corrupted file and `--fix` prints `fixed:` and can exit 0. Reproduced by a reviewer: the output file fails `parse_frontmatter` on the next run. A fixer that corrupts its input while reporting success is the worst failure mode it can have.
- **Fix:** After computing `new_text_lf`, re-parse it with `parse_frontmatter` and verify the parsed `id` equals `new_id`; on any failure return `None` (degrades to "remaining violation" instead of corruption). A cheap pre-check refusing block-scalar indicators (`[>|]`) as the matched value also works; the post-rewrite parse is the complete guard.
- **Status:** implemented (commit 23f2742)

## Medium

`F3` | Effectiveness | Severity: Medium | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:268` (hub — affects `validate-frontmatter`, `validate-id`, `format-frontmatter`)
- **Issue:** `paths.update(p for p in explicit if p.is_file())` silently drops explicitly named files that do not exist. `validate-frontmatter README.md docs/renamed.md` with a typo validates whatever remains; if nothing remains, main prints "no files matched" and exits 0. Verified empirically by a reviewer: `validate-id /tmp/nope.md` prints `✓ 0 file(s) validated`, exit 0. A CI gate naming a missing file passes green — the failure a validator exists to prevent.
- **Fix:** Treat a named-but-missing file as an invocation error: collect `[p for p in explicit if not p.is_file()]` and exit 2 with "no such file". Globs and includes may legitimately match nothing; explicitly named files may not.
- **Status:** implemented (commit 34433e2)

`F4` | Reliability | Severity: Medium | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:405` (worst impact at `validate_references.py:196-202`)
- **Issue:** `load_config` silently returns defaults when the config file does not exist — right for the implicit default `.project-standards.yml`, wrong for an explicitly passed `--config`. A typo'd `--config` makes `validate-frontmatter` validate with defaults, and makes `validate-references` exit 0 with zero output (references stay disabled). Verified: `validate-references --config typo.yml` → exit 0, no output. A renamed config silently disables every cross-file check while CI stays green.
- **Fix:** Make `--config` default to `None` in each main and fall back to `_DEFAULT_CONFIG` when unset; when the operator explicitly passed a path that does not exist, exit 2 with a clear message.
- **Status:** implemented (commit 9dba4f9)

`F5` | Reliability | Severity: Medium | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:107-116`
- **Issue:** `_construct_no_duplicates` runs `if key in mapping:` on whatever the key node constructs to. A YAML complex key (e.g. `? [a, b]`) constructs to a `list`, and the membership test raises `TypeError: unhashable type`, which is not a `yaml.YAMLError`, so it escapes `parse_frontmatter`'s catch (`:150`) as an uncaught traceback. PyYAML's stock constructor guards this and raises `ConstructorError("found unhashable key")`; the duplicate-key override lost that guard.
- **Fix:** Wrap the membership test/insert in `try/except TypeError` and raise `yaml.constructor.ConstructorError(None, None, f"found unhashable key {key!r}", key_node.start_mark)`, so it surfaces as a clean `FrontmatterParseError`.
- **Status:** implemented (commit 9bd8023)

`F6` | Effectiveness | Severity: Medium | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:275`
- **Issue:** The no-config fallback `Path().glob("**/*.md")` recurses into hidden and vendored trees — verified to return `.venv/lib/.../README.md`. A downstream repo running with no `include` (the advertised default, `:479-480`) validates every README inside `.venv/`, `node_modules/`, `.git/`, producing mass spurious "no frontmatter found" failures; via `validate-references` the polluted index can produce false duplicate-id errors. Exclusion is applied after collection, so the full tree is walked regardless.
- **Fix:** Skip any path containing a dot-prefixed component plus `node_modules` in the fallback walk (pruning during traversal also resolves the walk cost), or refuse the bare fallback with a "configure include:" error.
- **Status:** implemented (commit 15f1a9e)

`F7` | Correctness | Severity: Medium | Effort: M | Confidence: Med

- **Location:** `src/project_standards/validate_frontmatter.py:277-288`
- **Issue:** Include patterns use `Path.glob` semantics (`*` does not cross `/`) while exclude patterns use `fnmatchcase` (`*` does cross `/`). A consumer's `exclude: ["docs/*.md"]` (intending top-level only) silently excludes every nested `.md` under `docs/` — files escape validation. Separately, `is_excluded` matches `path.as_posix()` literally, so exclude patterns never match explicitly passed absolute paths (`validate-frontmatter /repo/standards/templates/x.md` bypasses `standards/**/templates/**`) despite the docstring's "exclude is applied in all cases". The `**` divergence is a documented trade-off (comment at `:277-283`); the `*` divergence and absolute-path bypass are not.
- **Fix:** Normalize candidates to repo-relative POSIX paths before exclusion matching, and either unify the two pattern dialects or document loudly that exclude `*` spans separators.
- **Status:** implemented (commit f35356a) — absolute paths normalized to repo-relative before exclusion; the `*`-spans-separators dialect kept and documented loudly in the collect_paths docstring

`F8` | Reliability | Severity: Medium | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:405-409`
- **Issue:** `load_config` guards with `path.exists()` then reads, catching only `yaml.YAMLError`. A config that exists but is unreadable (permission denied) or is a directory raises `PermissionError`/`IsADirectoryError` — an uncaught traceback instead of the documented clean exit 2. Because `load_config` is the shared hub, all four console scripts crash identically.
- **Fix:** Catch `OSError` alongside `yaml.YAMLError` and raise `ConfigError(f"cannot read config {path}: {exc}")`, which every main already maps to exit 2.
- **Status:** implemented (commit 7e7fc28)

`F9` | Effectiveness | Severity: Medium | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:435-436, 438-441, 454-460`
- **Issue:** `validate-id` prints violations and failure summaries to stdout, but the standard's documented exit-code contract says errors and the summary print to stderr (`standards/markdown-frontmatter/README.md:466`), and `validate_frontmatter.py:599-604` does use stderr. Inside `--fix` the streams are mixed: ADR-skip warnings go to stderr (`:433`) while remaining errors go to stdout (`:436`). Stream-filtering CI tooling or stdout redirection loses diagnostics for one validator but not its siblings.
- **Fix:** Print all violation lines and ✗ summaries to `sys.stderr` in both the plain and `--fix` branches, keeping success output on stdout, matching the README contract and `validate-frontmatter`.
- **Status:** implemented (commit 2fdfff0)

`F10` | Effectiveness | Severity: Medium | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_references.py:98-105`
- **Issue:** The standard explicitly endorses citing ADR ids across repositories (`standards/markdown-frontmatter/README.md:225`; same rationale in `validate_id.py:20-22`), but `_resolves` accepts only local ids and local files, so every documented cross-repo `related: ['adr-0001-otherrepo-...']` citation emits a permanent, unsuppressible `[warning] unresolved reference` on every run. Permanent false-positive noise trains consumers to ignore the warnings that matter.
- **Fix:** Recognize the well-formed ADR id shape (reuse `validate_id._ADR_ID_RE`) and skip — or downgrade to an info note — ADR-format ids that do not resolve locally; alternatively add a `references.external_ids` config knob.
- **Status:** implemented (commit e0649d3) — well-formed non-local ADR ids skipped; malformed ADR-like refs still warn

`F11` | Correctness | Severity: Medium | Effort: M | Confidence: Med

- **Location:** `src/project_standards/validate_id.py:72-75`
- **Issue:** `_VALID_DOC_TYPES` is loaded at import time from the default bundled schema, ignoring the consumer's pinned `markdown.frontmatter.version`. Latent today (the registry maps only "1.1" to that file), but the registry exists precisely to support multiple bundled contract versions: the moment a future schema revision changes the `doc_type` enum, consumers pinned to an older version get id prefixes checked against the wrong enum, silently breaking the versioned-contract promise.
- **Fix:** Resolve the doc_type enum from the effective schema for the loaded config (via `resolve_effective_schema` / `registry.frontmatter_schema_name`) inside `main` instead of a module-level constant.
- **Status:** implemented (commit b197a5e)

`F12` | Reliability | Severity: Medium | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_references.py:44-50`
- **Issue:** `build_index` silently drops unreadable files, files with malformed frontmatter, and non-mapping frontmatter — no message at all. A dropped doc's duplicate-id/ADR-sequence violations vanish, and references to its id misreport as "unresolved". The design relies on `validate-frontmatter` reporting parse errors, but that net only exists via `project-standards validate`; the standalone `validate-references` entry point can exit 0 ("references valid (0 docs...)") on a corpus where every doc has broken YAML. The skip itself is test-pinned (`tests/test_validate_references.py:43-56`), so confidence is Med on whether silence is intended.
- **Fix:** Emit a `[warning] {path}: skipped (unreadable or invalid frontmatter)` line per dropped file — warnings never fail the build, so the severity contract is preserved while the blind spot becomes visible.
- **Status:** implemented (commit d84956a) — warnings for unreadable/unparseable files; absent-frontmatter files stay silent (schema validator's finding)

## Low

`F13` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:422`, `src/project_standards/validate_references.py:47`
- **Issue:** `except OSError, FrontmatterParseError:` uses PEP 758 unparenthesized multi-exception syntax — valid on the pinned Python ≥3.14 and semantically correct, but a `SyntaxError` on every earlier interpreter, visually identical to the Python 2 `except X, name:` trap, and inconsistent with the parenthesized style used everywhere else (e.g. `validate_frontmatter.py:551`). Copy-adopt consumers vendoring snippets onto <3.14 break confusingly.
- **Fix:** Use the conventional `except (OSError, FrontmatterParseError):` at both sites.
- **Status:** implemented (commit bfca01e; the validate_references site was normalized in f8c9697/F1)

`F14` | Reliability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:263`
- **Issue:** Encoding asymmetry: `check_file` reads with `utf-8-sig` (BOM-stripped) but `fix_file` decodes plain `utf-8`, keeping U+FEFF, so `parse_frontmatter`'s `\A---` anchor fails and `fix_file` returns `None`. A BOM'd file is flagged by validation but `--fix` cannot fix it and gives no reason — validation and fixing disagree about which files have frontmatter.
- **Fix:** Strip a leading BOM after decoding in `fix_file` (and re-prepend on write to stay byte-faithful).
- **Status:** implemented (commit 6e40913)

`F15` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:230-240`
- **Issue:** For an unquoted id containing `#` with no preceding space (`id: old#id` — YAML reads the whole scalar), the lazy value/comment split assigns `#id` to the comment group, producing `id: 'new-id'#id`. PyYAML tolerates the adjacent `#`, but spec-strict parsers (e.g. the JS `yaml` package behind Prettier, which the Markdown Tooling standard ships) require whitespace before a comment, and the leftover `#id` is junk regardless. This is exactly the invalid-id input class `--fix` targets.
- **Fix:** In `_repl`, when group 3 starts with `#` and the value came from the unquoted alternative, emit a separating space (or drop the junk), producing spec-valid output.
- **Status:** implemented (commit 2a236fb)

`F16` | Effectiveness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:292-294, 412-424`
- **Issue:** When `fix_file` returns `None` for any non-ADR reason — title slugifies to empty (verified with a fully non-Latin title), missing/non-string title, BOM, undecodable bytes — `--fix` just re-prints the original violations with no indication a fix was attempted or why it failed. Only the ADR case gets a dedicated message.
- **Fix:** Return a small reason enum (or typed exceptions) from `fix_file` and print per-file skip reasons in the `--fix` loop.
- **Status:** implemented (commit 7c4fee4)

`F17` | Efficiency | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:408-424`
- **Issue:** In the `--fix` loop each failing file is read and frontmatter-parsed up to three times: `check_file`, `fix_file`, and on fix failure a third read at `:418` solely to learn the doc_type both earlier calls already had. Minor at corpus scale, but the third read can also race with a file changed between reads.
- **Fix:** Have `fix_file` return a structured result including doc_type (or accept pre-parsed text/meta), eliminating the re-read.
- **Status:** implemented (commit 7c4fee4) — the ADR special-case rides FixResult.is_adr, deleting the third read

`F18` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:438, 459`
- **Issue:** `file_count = len({e.split(":")[0] for e in all_errors})` derives the file count by splitting formatted strings on the first colon. Paths containing a colon (legal on Linux) and every Windows drive path (`C:\...` → key `"C"`) collapse distinct files, under-counting the "across M file(s)" summary. Cosmetic — exit code unaffected.
- **Fix:** Accumulate violating paths structurally (a `set[Path]` alongside the messages) and count that.
- **Status:** implemented (commit 2fdfff0)

`F19` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:158-161, 167-169`
- **Issue:** Two misleading messages: (a) `:169` tells the user the slug must match `[a-z0-9][a-z0-9-]*`, but the enforced regex (`:84`) is `^[a-z0-9]+(-[a-z0-9]+)*$` — the quoted pattern would accept `bad--slug` and `trailing-`, which the code rejects; (b) `:159-161` always appends `(got N chars)`, so a 6-char token failing on charset reads as a length problem that does not exist.
- **Fix:** (a) Quote the real pattern or describe it in words; (b) emit the length parenthetical only when the length is actually wrong, otherwise name the charset problem.
- **Status:** implemented (commit ebf38db)

`F20` | Reliability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:306, 318`
- **Issue:** `fix_file` writes in place with `path.write_bytes(...)` — truncate-then-write, so an interruption mid-write leaves a truncated document — and a write-side `OSError` (read-only file, permissions changed between read and write) propagates as an uncaught traceback, unlike read errors which are handled.
- **Fix:** Write to a sibling temp file and `os.replace` it over the original; wrap the write in `try/except OSError` and report the failure per file.
- **Status:** implemented (commit eee8d33)

`F21` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:304-309`
- **Issue:** (a) `zip(..., strict=False)` sits directly after an explicit equal-length guard — `strict=True` would self-document and fail loudly if the guard is bypassed; (b) the guard's fallback writes fully LF-normalised text, which would silently rewrite every CRLF line in the file, contradicting the function's own preserve-endings contract. Unreachable today, but it is exactly the path a future multi-line-aware fix would land in.
- **Fix:** Use `strict=True`; replace the fallback write with `return None` (refuse to fix rather than mass-normalise line endings).
- **Status:** implemented (commit 935454a)

`F22` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:70-75, 136`
- **Issue:** The safety of `doc_id.split("-", 2)` rests entirely on the comment "No valid doc_type contains a hyphen". Nothing enforces it: a future hyphenated doc_type (e.g. `how-to`) makes every id of that type misparse with confusing errors and no regression signal at schema-edit time.
- **Fix:** Pin the invariant with an assertion next to `_VALID_DOC_TYPES` or a unit test, so a hyphenated enum addition fails fast with an explanation.
- **Status:** implemented (commit 6cb45c9) — enforced in the enum loader (the module constant no longer exists after F11)

`F23` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:178-180`
- **Issue:** `check_file`'s docstring claims files whose `id`/`doc_type`/`title` fields are absent are skipped, but the function never inspects `title`, and `tests/test_validate_id.py:321-324` pins that a valid id without a title passes. A future maintainer could "restore" a title check that was deliberately removed.
- **Fix:** Drop `title` from the docstring (it remains accurate for `fix_file`).
- **Status:** implemented (commit bfca01e)

`F24` | Effectiveness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:442-447`
- **Issue:** When `--fix` fixes some files and skips ADRs (no remaining errors), stdout ends with `✓ N id(s) fixed` while the process exits 1; the only failure signal is a stderr warning that `--quiet` suppresses entirely. A green checkmark with a red exit code is a confusing contract; under `--quiet` there is zero indication why the run failed.
- **Fix:** When `adr_skipped` is non-empty, end with an explicit `✗ N ADR id(s) require manual fix` summary, mirroring how remaining errors get a ✗ line.
- **Status:** implemented (commit 2fdfff0)

`F25` | Effectiveness | Severity: Low | Effort: S | Confidence: Low

- **Location:** `src/project_standards/id_format.py:24-26` (call site `validate_id.py:291`)
- **Issue:** Generated-id uniqueness is purely probabilistic: `random_token()` draws 6 base-36 chars with no check against ids already in the corpus, and the duplicate-id check lives in `validate-references`, which is opt-in and off by default. Collision odds are negligible at corpus scale (~1e-5 at 1000 docs), but a collision produced by `--fix` in a repo that has not opted in would pass CI forever, while the README claims the token "provides global uniqueness".
- **Fix:** In the `--fix` loop, collect existing ids first and regenerate on collision (one-line retry); optionally note in the README that uniqueness enforcement requires `validate-references`.
- **Status:** implemented (commit f6fdb4e)

`F26` | Effectiveness | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/id_format.py:15-21`
- **Issue:** `slugify` has no length cap, so `--fix` on a long title produces an arbitrarily long id (a 200-char title → ~200-char id). The schema id pattern has no `maxLength`, so it validates, but unbounded ids defeat the "readable hint" purpose and get painful in `related:` lists.
- **Fix:** Truncate the slug at a word boundary (~60 chars, cut at the last hyphen) and document the bound in the standard.
- **Status:** implemented (commit 76dd23e) — 60-char word-boundary cap; bound documented in the standard README

`F27` | Reliability | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_id.py:72-75`
- **Issue:** The bundled schema is loaded at module import, so a broken wheel (missing/corrupt `schemas/`) makes every invocation — including `validate-id --help` — die with a raw traceback instead of the documented exit-2 error. `read_text()` also omits `encoding="utf-8"`, which is locale-dependent on Python 3.14 (PEP 686 lands in 3.15); harmless while the schema is ASCII.
- **Fix:** Pass `encoding="utf-8"` and move the load into a cached accessor called from `main`/`check_file` inside a try/except mapping to exit 2. (Subsumed by the F11 fix if that is taken.)
- **Status:** implemented (commit b197a5e) — folded into the F11 lazy loader: explicit utf-8, ConfigError → exit 2

`F28` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_id.py:392-395`
- **Issue:** The custom-schema detection re-implements `schema_value_is_path` (`validate_frontmatter.py:77-83`) character-for-character instead of importing it — the comment even says "Mirrors the schema_value_is_path check". If the heuristic ever changes, validate-id silently disagrees with validate-frontmatter about whether a config uses a custom schema.
- **Fix:** Import and call `schema_value_is_path` (already exported; `validate_references.py` imports it).
- **Status:** implemented (commit bfca01e)

`F29` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:130-131`
- **Issue:** `_coerce_dates` converts a `datetime.datetime` via `.date().isoformat()`, silently discarding the time. An author writing `updated: 2026-06-02 15:30:00` passes validation as if the value were `"2026-06-02"`, but the file's literal content violates the standard's "dates MUST be YYYY-MM-DD strings" rule, and downstream tools reading the raw text see the non-conformant value.
- **Fix:** Stop coercing `datetime.datetime` (let the string-typed schema reject it), or coerce only exact-midnight values; keep the `datetime.date` coercion.
- **Status:** implemented (commit a6fa8ec)

`F30` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:423-424, 435-436, 440-441, 445-448`
- **Issue:** Version values are read with `str(version_val)`, so unquoted numeric versions are float-mangled: `version: 1.10` parses as float `1.1` and becomes `"1.1"` — a consumer pinning contract "1.10" unquoted would silently resolve to the "1.1" contract instead of erroring. Applies to all four version keys.
- **Fix:** Accept only `isinstance(version_val, str)` and raise `ConfigError` (exit 2) with a "quote your version" hint for non-string values.
- **Status:** implemented (commit 943325f)

`F31` | Reliability | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_frontmatter.py:237`
- **Issue:** `sorted(validator.iter_errors(meta), key=lambda e: list(e.path))` compares raw JSON-path elements, a mix of `str` keys and `int` indices; heterogeneous paths raise `TypeError` during sort. Unreachable with the bundled schema's shape, but consumers can supply arbitrary `--schema` files where this becomes an uncaught traceback.
- **Fix:** Use a type-stable key, e.g. `key=lambda e: [str(p) for p in e.path]`.
- **Status:** implemented (commit b390591)

`F32` | Reliability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:152-153, 231-233`
- **Issue:** A present-but-non-mapping frontmatter block (a YAML list, a bare scalar, or an unterminated `---` with no closing fence) makes `parse_frontmatter` return `None`, which `validate_file` reports as "no frontmatter found at top of file". The author stares at a block that visibly exists and is told it does not; the real problems are "not a mapping" / "never closed".
- **Fix:** Distinguish the cases — a sentinel or dedicated error for present-but-non-mapping blocks, keeping `None` strictly for "no leading `---`". (Message-level change; the pass/fail outcome is already correct and test-pinned.)
- **Status:** implemented (commit 7c02b93) — message-level distinction in validate_file; parse_frontmatter's None contract unchanged so sibling validators keep their skip semantics

`F33` | Correctness | Severity: Low | Effort: M | Confidence: Med

- **Location:** `src/project_standards/validate_frontmatter.py:179, 192-196`
- **Issue:** The ADR section check toggles `in_code_fence` on any ` ``` `/`~~~` line without tracking fence character or length. Per CommonMark a fence closes only with the same character at ≥ length, so a `~~~` line inside a backtick fence, or the common four-backtick-fence-containing-three-backtick-lines docs pattern, desynchronizes the tracker — illustrative headings count as real (false pass) or real headings get swallowed (false fail). `[ \t]*` also accepts fences indented ≥4 spaces, which CommonMark treats as indented code.
- **Fix:** Record the opening fence's char and length; close only on a matching fence of ≥ length; cap leading indentation at three spaces.
- **Status:** implemented (commit 78ad1d7)

`F34` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:174`
- **Issue:** `_H2_HEADING_RE` does not strip an ATX closing sequence: `## Decision Outcome ##` (valid CommonMark) captures `Decision Outcome ##`, fails the exact match, and a valid MADR document written with closing hashes is flagged as missing all sections.
- **Fix:** Extend the regex to strip an optional trailing closing sequence: `r"^##[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$"`.
- **Status:** implemented (commit 78ad1d7)

`F35` | Effectiveness | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_frontmatter.py:42`
- **Issue:** `_FRONTMATTER_RE` requires fence lines to be exactly `---`; a single trailing space on the closing fence makes the file report "no frontmatter found" (verified). Jekyll/python-frontmatter tolerate trailing whitespace on fences, so authored-elsewhere files can flip to "missing frontmatter" here. Note the sibling regex in `validate_id._replace_frontmatter_id` (`validate_id.py:218`) does allow `---[ \t]*` — the two disagree.
- **Fix:** Allow horizontal whitespace before the newline on both fences: `\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)`.
- **Status:** implemented (commit 4c9ae99)

`F36` | Effectiveness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/schemas/markdown-frontmatter.schema.json:167`
- **Issue:** The shared date pattern `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` accepts calendar-impossible values (`2026-13-40`, `0000-00-00`) for `created`/`updated`/`reviewed`; `validate_references.check_dates` then string-compares them. jsonschema does not enforce `format: date` by default, so the pattern is the only gate.
- **Fix:** Tighten the pattern (`^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$`) or add a code-level `date.fromisoformat` check in `validate_file`. Note: a schema change is a contract change — belongs in a new schema/contract version per the versioning model.
- **Status:** implemented (commit 4b89524) — code-level date.fromisoformat check in validate_file; schema pattern untouched (no contract change)

`F37` | Effectiveness | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/schemas/markdown-frontmatter.schema.json:93`
- **Issue:** The `tags` item pattern `^[a-z0-9][a-z0-9-]*$` permits trailing and consecutive hyphens (`infra-`, `a--b`), while validate-id's kebab rule rejects exactly those shapes for id slugs — inconsistent strictness between two enforced surfaces of the same standard. The description's "Prefer lowercase kebab-case" may make the looseness intentional.
- **Fix:** Align the tags pattern with the kebab rule `^[a-z0-9]+(-[a-z0-9]+)*$` (same contract-version caveat as F36).
- **Status:** implemented (commit f94d282) — CONTRACT-STRICTNESS BUMP to the bundled 1.1 schema; repo corpus verified clean; flag in CHANGELOG at next release

`F38` | Effectiveness | Severity: Low | Effort: M | Confidence: Low

- **Location:** `src/project_standards/schemas/markdown-frontmatter.schema.json:24, 86-90`
- **Issue:** `consumer` (a 1.1 addition) is accepted regardless of the document's declared `schema_version`: a doc declaring `"1.0"` may carry `consumer:` and still validate, because one flat property set serves both enum values. If `schema_version` is meant to gate the available surface this is drift; if 1.0/1.1 share one additive surface by design, drop this finding.
- **Fix:** If gating is intended, add an `if/then` clause forbidding 1.1-only fields under `schema_version: "1.0"`, or split per-version schemas in the registry.
- **Status:** skipped — 1.0/1.1 share one additive surface by design (the registry maps a single bundled schema; the README calls 1.1 'an additive revision'); the finding's own Fix resolves to 'drop this finding'

`F39` | Reliability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/registry.py:124-158`
- **Issue:** `load_registry` validates shapes but never cross-checks that each section's `default` is a member of its `versions`, or that `adr.versions.*.supports_frontmatter` entries name bundled frontmatter versions. A registry edit bumping `"default": "1.2"` without adding the version loads cleanly and fails later as a confusing incompatibility or missing-schema error instead of a crisp load-time message.
- **Fix:** After parsing, assert default-in-versions for all four sections and `supports_frontmatter ⊆ frontmatter.versions`, raising `RegistryError` naming the offending key.
- **Status:** implemented (commit c5d2f78)

`F40` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:346-357`
- **Issue:** `resolve_effective_schema` rejects a custom `schema:` path combined with `frontmatter.version` ("not both"), but when `schema:` is a bundled name, a configured version silently wins — the bundled name is never cross-checked. Harmless with today's single-schema registry, but a future second bundled name reintroduces exactly the ambiguity the path case rejects loudly. The repo's own dogfood config sets both keys (`.project-standards.yml:9,12`), normalizing the pattern downstream.
- **Fix:** When both a bundled name and a version are set, verify the registry maps that version to the same schema name; raise `ConfigError` on mismatch.
- **Status:** implemented (commit bfed916)

`F41` | Reliability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:407`
- **Issue:** The config is parsed with plain `yaml.safe_load`, so duplicate keys in `.project-standards.yml` silently last-win (two `exclude:` blocks → the first is dropped; intended excludes get validated or intended includes vanish). Frontmatter parsing got `_UniqueKeyLoader` on the argument that "a duplicate key is a bug, not a valid doc" — the config that decides what gets validated deserves the same.
- **Fix:** Load the config with `_UniqueKeyLoader` and surface the duplicate-key error as `ConfigError`/exit 2.
- **Status:** implemented (commit ff25e21)

`F42` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:490-493`
- **Issue:** The `--glob` help says "Additional glob pattern relative to cwd", but per `collect_paths` (`:260-263`) supplying `--glob` suppresses the config include patterns entirely rather than adding to them — an operator expecting includes-plus-glob silently validates a smaller set.
- **Fix:** Reword to "Validate files matching PATTERN instead of the config include list (combines with explicit FILE arguments)". Same wording fix applies to `validate_id.py:353`.
- **Status:** implemented (commit d89c6a8)

`F43` | Reliability | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_frontmatter.py:520-524`
- **Issue:** `main` loads the registry unconditionally and exits 2 on failure even when `--schema` is given and no version keys are configured — i.e. when the registry is never consulted. A wheel with a corrupted `registry.json` breaks even the explicit-schema escape hatch that would otherwise keep consumer CI green.
- **Fix:** Load the registry lazily, only before first actual use (version resolution, compat gate, tooling-version checks).
- **Status:** implemented (commit b8f7f35) — registry-failure test updated to the new lazy semantic; new test pins the --schema escape hatch surviving a broken registry

`F44` | Reliability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:270-275` (also reachable via `validate_id.py:401`)
- **Issue:** `Path().glob(...)` raises `NotImplementedError: Non-relative patterns are unsupported` for absolute patterns — verified via `validate-id --glob '/etc/*.md'`. An absolute `--glob` or config include crashes with a traceback (exit 1, looking like a validator crash) instead of the documented exit-2 invocation error.
- **Fix:** Wrap the glob calls in `try/except (NotImplementedError, ValueError)` and raise `ConfigError` ("glob patterns must be relative to the repo root") so every caller exits 2 cleanly.
- **Status:** implemented (commit db8b69c)

`F45` | Reliability | Severity: Low | Effort: S | Confidence: Low

- **Location:** `src/project_standards/validate_frontmatter.py:602, 608` (same pattern in `validate_id.py`, `validate_references.py`)
- **Issue:** Summaries print `✓`/`✗`; on a console with a non-UTF-8 locale (Windows cp1252, mis-configured self-hosted runners) `print` raises `UnicodeEncodeError`, turning a clean pass/fail into a traceback. GitHub-hosted Linux runners are UTF-8, so practical impact is limited to self-hosted/Windows consumers.
- **Fix:** Use ASCII (`OK`/`FAIL`) or reconfigure stdout/stderr with `errors="replace"` at entry.
- **Status:** implemented (commit 35fd5f7) — errors='replace' reconfigure at all three mains' entry; ✓/✗ glyphs kept (tests pin them)

`F46` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_frontmatter.py:107-116, 154`
- **Issue:** `_construct_no_duplicates` is annotated `-> dict[str, Any]` but builds `dict[Any, Any]` — YAML keys can be `bool` (`on:` under YAML 1.1), ints, or dates — and the result is laundered through `cast("dict[str, Any]", ...)` in `parse_frontmatter`. No runtime bug today (`additionalProperties: false` rejects them), but the types misstate the contract and hide the YAML key-coercion quirk from maintainers.
- **Fix:** Annotate the constructor `-> dict[Any, Any]` and explicitly reject (or stringify) non-string keys in `parse_frontmatter` before the cast.
- **Status:** implemented (commit b603a05)

`F47` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_references.py:90-94`
- **Issue:** Inconsistent empty-string handling in `_ref_values`: list items are filtered with `isinstance(v, str) and v`, but the scalar branch appends unconditionally, so `superseded_by: ''` (schema-valid via `anyOf` with no `minLength`) produces the confusing warning `unresolved reference ''` while `related: ['']` is silently ignored.
- **Fix:** Apply the same truthiness filter to the scalar branch so the two forms agree.
- **Status:** implemented (commit 0855189)

`F48` | Correctness | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_references.py:141-154`
- **Issue:** `a_id = doc.meta.get("id")` may be `None` (the index keeps docs without an id), and `None` then flows into the membership test (always true) and the message, yielding `"'None' is superseded_by 'note-x'"` — a nonsense warning instead of a clear "doc has no id" diagnosis.
- **Fix:** Skip reciprocity for docs whose own id is absent/non-string (`if not isinstance(a_id, str): continue`), optionally with a dedicated warning.
- **Status:** implemented (commit c76f1ab)

`F49` | Correctness | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_references.py:131-140`
- **Issue:** `supersedes_map`/`superseded_by_map` are dict comprehensions keyed by id; when two docs share an id (already an error elsewhere), the comprehension keeps only the last doc's set, so reciprocity against that id is computed from an arbitrary duplicate — unreliable warnings in the same run that reports the duplicate.
- **Fix:** Merge sets per id (`setdefault(...).update(...)`) or skip reciprocity for ids with `len(index.by_id[id]) > 1`.
- **Status:** implemented (commit 6fbc215)

`F50` | Correctness | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_references.py:26, 166-168`
- **Issue:** ADR sequence numbers are keyed by the raw digit string, so `adr-0001-...` and `adr-00001-...` (both valid per `_ADR_ID_RE`'s `[0-9]{4,}`) are numerically the same ADR 1 but are not flagged as duplicates.
- **Fix:** Key by `int(m.group(1))`; keep the original strings in the message.
- **Status:** implemented (commit 20b6abb)

`F51` | Correctness | Severity: Low | Effort: S | Confidence: Low

- **Location:** `src/project_standards/validate_references.py:75-80`
- **Issue:** Date ordering uses lexicographic string comparison — correct only for zero-padded ISO dates. Schema validation is a separate tool that may not have run (standalone invocation, or schema errors in the same run): a non-padded `created: '2026-9-1'` compares wrongly, producing false errors or missed ones.
- **Fix:** Parse with `datetime.date.fromisoformat` in try/except and skip (or warn on) unparseable values.
- **Status:** implemented (commit 4737919)

`F52` | Reliability | Severity: Low | Effort: M | Confidence: Med

- **Location:** `src/project_standards/validate_references.py:212, 218`
- **Issue:** The repo root is `Path.cwd()` and globs are cwd-relative; run from a subdirectory (or with `--config ../other/.project-standards.yml`) the pass silently indexes the wrong tree — includes match nothing and it prints `✓ references valid (0 docs, 0 warning(s))`, exit 0. There is no "no files matched" guard like `validate_frontmatter.py:582-585`.
- **Fix:** Print "no managed docs matched" (and consider non-zero) when `index.docs` is empty instead of a success summary; optionally derive the root from the config file's directory or document cwd==repo-root as a hard precondition.
- **Status:** implemented (commit 866ce89) — empty-index stderr note + cwd==repo-root precondition documented; root derivation deliberately unchanged (cwd contract shared with the sibling tools)

`F53` | Effectiveness | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_references.py:101-102`
- **Issue:** A ref carrying an anchor (`docs/arch.md#section`) is rejected with the generic `unresolved reference` message even when the file exists; the actual rule is "anchors are not document references". The standard documents "use document-level links, not section-level links" as convention, but the warning text misdiagnoses the cause. Behavior is test-pinned, so this is a message/docs improvement.
- **Fix:** Emit a specific message ("section anchors are not valid document references") for the `#` case; optionally document the rule in the references section of the README.
- **Status:** implemented (commit f6fd2ad)

`F54` | Correctness | Severity: Low | Effort: M | Confidence: Med

- **Location:** `src/project_standards/validate_references.py:103-105`
- **Issue:** Platform-dependent resolution holes in `_resolves` (basedpyright is configured `pythonPlatform = "All"`, so portability is in-contract): a Windows drive ref (`C:/x.md`) bypasses the absolute-path guard; backslash traversal (`..\x`) is not caught textually; `is_file()` follows symlinks, so a symlink pointing outside the repo defeats the `../` guard; case-insensitive filesystems resolve refs that Linux CI then warns on.
- **Fix:** Replace the textual guards with containment: `(repo_root / ref).resolve()` must be `is_relative_to(repo_root.resolve())` — collapsing drive/backslash/symlink cases into one check. Case sensitivity can stay documented as Linux-canonical.
- **Status:** implemented (commit 52af66c)

`F55` | Effectiveness | Severity: Low | Effort: L | Confidence: High

- **Location:** `src/project_standards/validate_references.py:84-114` (scope)
- **Issue:** Body links are never validated — the tool inspects only four frontmatter fields, yet nothing else in the toolchain checks that body links resolve, so a broken `[x](docs/gone.md)` ships green through every consuming repo. The standard explicitly documents this as a known gap deferred to a future schema revision (README "Links and related documents": "the validator does not check link form, in frontmatter or in document bodies"), so this is a tracked contract-scope gap, not a code bug — recorded here for completeness.
- **Fix:** An opt-in body-link pass (extract inline/reference links outside code fences; resolve path targets against the repo root), or leave to the planned future major as documented.
- **Status:** skipped — the standard explicitly defers body-link validation to a planned future major ('the validator does not check link form, in frontmatter or in document bodies'); tracked contract gap, not a code bug

`F56` | Reliability | Severity: Low | Effort: S | Confidence: Med

- **Location:** `src/project_standards/validate_references.py:203-206`
- **Issue:** With `references.enabled: true` plus a custom `schema:` path, the entire pass is skipped; under `--quiet` (which `project-standards validate -q` forwards) even the skip note is suppressed, so an explicitly enabled check silently does nothing. The note also goes to stdout while the analogous note in `cli.py:219` goes to stderr.
- **Fix:** Print the skip note to stderr even under `--quiet` when the config explicitly enables references (one line for an enabled-but-skipped check is worth it). Stream change requires updating `test_main_custom_schema_skips`.
- **Status:** implemented (commit 866ce89) — note moved to stderr and survives --quiet when references are explicitly enabled; pinned test updated for the stream change

`F57` | Efficiency | Severity: Low | Effort: L | Confidence: High

- **Location:** cross-module (`validate_references.py:42-57` with `cli.py:198-229`)
- **Issue:** Within each validator every file is read and parsed exactly once, but via `project-standards validate` the corpus is read+frontmatter-parsed three times (once per validator), and `fix` five-plus times. Fine at tens-to-hundreds of files; recorded because the architecture has no shared parsed-document index to grow into. Informational — no action needed now.
- **Fix:** If corpus size ever grows, introduce a shared parsed index passed between the validators in `cli.py`.
- **Status:** skipped — informational by its own terms ('Fix: none needed now'); no action at current corpus scale

`F58` | Maintainability | Severity: Low | Effort: S | Confidence: High

- **Location:** `src/project_standards/validate_references.py:38-39, 55-56`
- **Issue:** `Index.ids` is fully redundant with `Index.by_id` (`ids == set(by_id)` always; both populated under the same condition). Two structures encoding one fact invites drift from a future path that updates one but not the other.
- **Fix:** Drop `ids` and use `ref in index.by_id` in `_resolves` (same O(1) membership).
- **Status:** implemented (commit 2372fc7)
