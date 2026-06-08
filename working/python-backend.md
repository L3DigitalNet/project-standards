# Invoking migrated Python tools across many standards-adopting repos

Working notes — captured 2026-06-08. Scratch/advisory; not a managed standard doc.

## The question

We are converting per-repo bash scripts to Python in a repo that consumes the `project-standards` Python Tooling SSOT. `pyproject.toml` there deliberately has **no `[build-system]`** (non-packaged meta-repo), with `pythonpath=src`. So: how should the migrated tools be invoked?

Three options were on the table:

1. **Unified CLI** — one package, `python -m tools <subcommand>`.
2. **Per-module** — each tool runnable as `python -m tools.lint`.
3. **Add a build backend** — get true `[project.scripts]` console scripts.

The deeper concern that reframes all three: **20+ repos** will adopt standards that need the same tooling (validate/lint/track files by frontmatter, etc.). We do not want to build and maintain that tooling 20 times.

---

## The constraint that creates the question

A true "console script" (type `mytool`, it runs) is not magic. It is a small wrapper executable that a **build backend** generates at install time from a `[project.scripts]` table. No build backend → nothing is ever "installed" → no wrapper on `PATH`. That is the entire tension.

Without a build backend, code is reached by **import path**, not installation. `python -m foo` searches `sys.path` for an importable `foo`; with a `src/` layout that means `src/` must be on `PYTHONPATH` at runtime.

Key mechanics:

- `[tool.pytest.ini_options].pythonpath = ["src"]` only helps **pytest**. It does NOT put `src/` on the path for a bare `python -m`. You still need `PYTHONPATH=src python -m …` or a `uv`/env shim.
- `python -m pkg` runs `pkg/__main__.py`; `python -m pkg.mod` runs that module's `if __name__ == "__main__"` block. Same mechanism, different granularity.
- console_scripts are the ONLY one of the three that survives leaving the repo directory — the wrapper lives in the venv's `bin/`, not in `src/`.

---

## The three local invocation options

### Option 1 — Unified CLI (`python -m tools <subcommand>`)

One package with a `__main__.py` that dispatches to subcommands (argparse subparsers or Click groups). Each migrated bash script becomes a subcommand.

```
src/tools/__main__.py        →  python -m tools lint
src/tools/lint.py            →  python -m tools format
src/tools/format.py
```

- **For:** one argument parser, one `--help`, shared helpers/logging/exit-code conventions in one place. Discovery is free (`python -m tools --help`). Mirrors a bash dispatcher (`./tasks.sh lint`) → near 1:1 migration model.
- **Against:** all tools share one import namespace and dependency surface; a heavy import in one tool slows startup for all unless you lazy-import inside each subcommand.

### Option 2 — Per-module (`python -m tools.lint`)

Each tool is its own runnable module with its own `main()`.

```text
src/tools/lint.py            →  python -m tools.lint
src/tools/format.py          →  python -m tools.format
```

- **For:** maximum isolation; no central dispatcher to maintain.
- **Against:** **no unified discovery**, more verbose invocation, and you re-implement shared concerns (exit codes, common flags) per module — at which point you have half of Option 1 without its dispatcher.

### Option 3 — Add a build backend (true `[project.scripts]`)

Add `[build-system]` (the SSOT uses `uv_build`), declare scripts, and the venv gets real executables:

```toml
[build-system]
requires = ["uv_build>=0.9"]
build-backend = "uv_build"

[project.scripts]
lint   = "tools.lint:main"
format = "tools.format:main"
```

Then `uv sync` installs the project; type `lint` / `uv run lint`.

- **For:** cleanest UX — no `python -m`, no `PYTHONPATH`. Identical to how the SSOT itself ships `validate-frontmatter`.
- **Against — the real cost:** it changes **what the repo is**. "Non-packaged meta-repo" is a deliberate architectural statement. A backend means the repo builds a wheel, needs a package name/version, and every tool must live under one importable distribution. It is a one-way door worth an ADR — not a quiet default.

### Local-options summary

|  | Invocation | Needs `PYTHONPATH=src`? | Discovery | Changes repo identity? | Effort |
| --- | --- | --- | --- | --- | --- |
| **1 Unified CLI** | `python -m tools lint` | Yes (or uv shim) | built-in | No | Low |
| **2 Per-module** | `python -m tools.lint` | Yes (or uv shim) | none | No | Lowest |
| **3 Build backend** | `lint` / `uv run lint` | No | console scripts | **Yes** | Medium + ADR |

Options 1 and 2 are reversible in an afternoon; Option 3 is a one-way door you would document.

---

## The reframe: this is a distribution problem, not an invocation problem

The invocation question (`python -m` vs build backend) is **per-repo and local**. "I don't want to build the tooling 20 times" is a **distribution** concern, and it is **orthogonal**. The mistake hiding in the original three options is the assumption that the shared tools live in the consumer repo at all.

**They should not.** Migrating bash→Python _inside_ each repo is the thing that makes you build 20 times. Hoisting the shared tools into one packaged repo makes you build once.

### `project-standards` already IS the "build once" package

From its `pyproject.toml`:

```toml
[project.scripts]
validate-frontmatter = "project_standards.validate_frontmatter:main"

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"
```

It was built exactly **once**, versioned `2.0.0` behind the moving `v2` tag (`v1` frozen at `1.2.0`). The 20 consumers never build it — they consume it.

> The earlier "Option 3: add a build backend" was right — but for the WRONG repo. The build backend belongs on the ONE repo that ships the tools (this one already has it), not on each of the 20 consumers.

### Two different "tools" got conflated

- **Shared standard tooling** (frontmatter validate, link/track, lint orchestration) is a **PRODUCT** — built once, versioned, distributed.
- **Repo-specific scripts** are **LOCAL** — they stay home.

The standards already encode the discipline:

- **copy-adopt** is for _config_ (markdownlint, prettier, editorconfig — static, harmless to duplicate).
- **packaged distribution** is for _code_ (never duplicate executable logic).

---

## Distribution models (build once → consume 20×)

Because the tool is packaged in `project-standards`, a consumer reaches it three ways. You will likely use all three for different surfaces.

### A. Ephemeral `uvx` — no install, nothing in the consumer's deps

```bash
uvx --from git+https://…/project-standards@v2 validate-frontmatter \
    --config .project-standards.yml
```

uv fetches, caches, runs. Best for **pre-commit hooks** and ad-hoc local runs. The consumer gains zero Python footprint — no `src/`, no build backend, no `pyproject` churn. Cleanest fit for repos that are not Python projects at all.

### B. Pinned dev dependency — reproducible, lockfile-tracked

```bash
uv add --dev "project-standards @ git+https://…@v2"
uv run validate-frontmatter …
```

The tool's version is captured in the consumer's `uv.lock`. Best when a repo wants deterministic, offline-capable runs and already has a `uv` project. Costs one dependency entry per repo.

### C. Reusable CI workflow — the consumer doesn't even name the tool

This is what the standard already does ("downstream repos run via a reusable CI workflow"). The consumer's workflow is a few lines:

```yaml
uses: …/project-standards/.github/workflows/validate.yml@v2
```

The invocation lives in the shared workflow; 20 repos reference it; fixing the tool = one tag bump.

### Why this kills the "build 20 times" problem

| Concern | Copy/migrate into 20 repos | Centralized package (A/B/C) |
| --- | --- | --- |
| Build effort | 20× (and 20 `src/` layouts, 20 backends) | **1×, in `project-standards`** |
| Bug fix | edit 20 repos | edit once, bump `v2`, repos re-pin |
| Version drift | guaranteed | one contract, enforced by tag |
| Consumer footprint | a `src/` package each | none (A) or one dep line (B) |
| Discovery / UX | reinvented per repo | one `--help`, one CLI |

The cost you trade INTO is **coordination, not labor**: one breaking change now hits 20 repos at once. That is precisely why this repo froze `v1` at `1.2.0` and moved `v2` — the version tag is the blast-radius control. Consumers re-pin on THEIR schedule, not yours.

"Build once" and "many CLI subcommands" compose: as you add linting/tracking tools, they become new `[project.scripts]` entries (or subcommands of one unified CLI) in the `project-standards` `pyproject` — and all 20 repos get them on the next re-pin for free.

---

## Decision procedure for the repo you're actually in

Sort each bash script being migrated into one bucket:

- **"Every standards-adopting repo needs this"** (frontmatter validate, link-check, file tracking) → **do NOT migrate it locally.** Add it as a console script in `project-standards`, alongside `validate-frontmatter`. The consumer gets it via A / B / C.
- **"Genuinely specific to this one repo"** → migrate locally, and NOW Option 1 (unified `python -m` CLI) is the right call. You will have far fewer of these than you think.

### Recommendation

- For **shared tooling**: centralize in `project-standards` (build backend + `[project.scripts]` — already present), distribute via `uvx` / dev-dependency / reusable CI workflow. Build once.
- For **the few genuinely local scripts**: Option 1 (unified CLI). It honors the no-build-system constraint, gives bash-dispatcher ergonomics, and centralizes exit-code/logging conventions. Smooth the `PYTHONPATH` wart with a `uv`/Make alias so users type `uv run tools lint`, never raw `PYTHONPATH=src python -m`.
- Reach for a **local build backend (Option 3)** only if "these tools must be runnable from outside the repo / installed standalone" becomes a real requirement — and treat dropping the non-packaged design as an ADR.

### The one question that decides the shape

Of the bash scripts being converted, **how many are repo-specific vs. the same validation/lint/track logic all 20 repos will want?** If the honest answer is "mostly the latter," the work is not a per-repo migration at all — it is _extending the `project-standards` package CLI_ and wiring the reusable workflow.
