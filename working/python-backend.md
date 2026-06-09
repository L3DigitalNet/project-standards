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

```text
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

> **`project-standards` already walked through that door.** Everything Option 3 describes is live in this repo today. The full mechanics — what `uv_build` does to `src/`, how `[project.scripts]` becomes a real executable on `PATH`, and how a _git tag_ (not a PyPI upload) ends up running on 20 consumers — are dissected in the [appendix](#appendix--how-a-build-backend-actually-ships-the-tooling-option-3-end-to-end) at the end of this note.

### Local-options summary

| Option | Invocation | Needs `PYTHONPATH=src`? | Discovery | Changes repo identity? | Effort |
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

---

## Appendix — How a build backend actually ships the tooling (Option 3, end-to-end)

Option 3 above is not hypothetical for this repo — it is the running configuration. This appendix opens the box: what the four lines of `[build-system]` set in motion, where `validate-frontmatter` physically comes from, and why "cutting a release" here means moving a git tag rather than uploading anything. Read it as the long-form answer to "what are we doing when we release the tooling?"

### 1. The PEP 517 split: who builds, who calls the builder

The single most useful idea is that **building is a two-party protocol**, standardised by [PEP 517](https://peps.python.org/pep-0517/) / [PEP 518](https://peps.python.org/pep-0518/):

- A **build _frontend_** is whatever the user runs: `uv build`, `uv pip install`, `uvx`, `uv sync`, or plain `pip`. It knows _nothing_ about how this project is laid out.
- A **build _backend_** is a library named in `pyproject.toml` that knows exactly how to turn this source tree into a distribution. Here it is `uv_build`:

  ```toml
  # pyproject.toml — the entire contract that makes this repo packageable
  [build-system]
  requires = ["uv_build>=0.11,<0.12"]   # PEP 518: deps needed *to build*, installed in an isolated env
  build-backend = "uv_build"            # PEP 517: the module the frontend imports and calls
  ```

The frontend reads `requires`, installs those build-time dependencies into a throwaway environment, imports the `build-backend` module, and calls standardised hooks on it — chiefly `build_wheel(...)` and `build_sdist(...)`. The backend does the actual packaging and hands back a file. **Neither the frontend nor the project author needs to know the other's internals** — that decoupling is why you can swap `uv_build` for `hatchling` or `setuptools` by editing two lines, and why the same `uvx` command works against any PEP 517 project on earth.

> `requires` is build-time only. It is a different dependency set from `[project].dependencies` (`jsonschema`, `pyyaml`) — those are what the tool needs _to run_; `uv_build` is what the project needs _to be built_. They never mix: `uv_build` is not installed into the consumer's runtime environment.

### 2. What `uv_build` does with this repo's `src/` layout

`uv_build` is uv's own native backend (a fast Rust implementation, no setuptools in the loop). Given this project it does three things worth understanding:

**Module discovery.** By default it expects exactly one root module at `src/<normalized-name>/__init__.py`. The project name `project-standards` is normalised by lowercasing and turning dots/dashes into underscores → `project_standards`. That is precisely why the code lives at `src/project_standards/` and `__init__.py` is present — the layout is not a convention, it is what the backend _requires_ to find the package. The `src/` prefix is the standard "src layout": it keeps the import root out of the repo root so that `import project_standards` can only succeed against the _installed_ package, never an accidental relative import during tests.

**Data-file inclusion — why the schemas travel with the code.** When building a wheel, `uv_build` includes the **entire module root** (everything under `src/project_standards/`), copies `project.license-files` into the wheel's metadata directory, and copies `project.readme` into the metadata. This is the mechanism that ships the non-Python payload this tool depends on at runtime:

```text
src/project_standards/
├── validate_frontmatter.py        ← code
├── cli.py  registry.py  …
├── schemas/                        ← JSON schema, read at runtime via Path(__file__).parent
│   ├── markdown-frontmatter.schema.json
│   └── registry.json
├── bundles/                        ← copy-adopt scaffolds shipped *inside* the package
│   ├── markdown-frontmatter/…  python-tooling/…  adr/…
└── py.typed                        ← marks the package as typed (PEP 561) for downstream basedpyright
```

Because `schemas/` and `bundles/` sit **under the module root**, they are bundled automatically — no `MANIFEST.in`, no `package_data` glob. (The rule is strict: data files must live under the module root or an explicit `tool.uv.build-backend.data` directory, or they simply won't ship. That is the structural reason the schema lives _inside_ `src/project_standards/` rather than at repo root.)

**Two artifacts.** `uv build` produces both a source distribution and a wheel into `dist/`:

```console
$ uv build
$ ls dist/
project_standards-2.0.0-py3-none-any.whl     # the wheel — a pre-built, installable zip
project_standards-2.0.0.tar.gz               # the sdist — source + metadata, built into a wheel on demand
```

The `py3-none-any` tag means "pure Python, any interpreter, any platform" — no compiled extensions, so one wheel serves every consumer. (Hold that thought; §6's zipapp fallback exists because one of the _dependencies_ is not so portable.)

### 3. The wheel's secret: `entry_points.txt` and the install-time wrapper

This is the crux — the actual answer to "how does typing `validate-frontmatter` run Python?" A wheel is just a zip with a metadata directory:

```text
project_standards-2.0.0.dist-info/
├── METADATA           # name, version, deps, readme  (from [project])
├── WHEEL              # wheel format version, build tool
├── RECORD             # every file + hash (the install manifest)
└── entry_points.txt   # ← the console-script recipe
```

The backend translates the `[project.scripts]` table verbatim into `entry_points.txt`:

```ini
# entry_points.txt, generated from pyproject.toml [project.scripts]
[console_scripts]
project-standards       = project_standards.cli:main
validate-frontmatter    = project_standards.validate_frontmatter:main
validate-id             = project_standards.validate_id:main
sync-vscode-colors      = project_standards.sync_vscode_colors:main
sync-standards-include  = project_standards.sync_standards_include:main
```

**Nothing is executable yet.** `entry_points.txt` is a _recipe_, not a program. The magic happens at **install time**: when any installer (`uv pip install`, `uv tool install`, `uv sync`) lays the wheel down, it reads `[console_scripts]` and, for each entry, _generates_ a tiny launcher script in the environment's `bin/` directory:

```python
#!/path/to/.venv/bin/python
# .venv/bin/validate-frontmatter — generated by the installer, not written by us
import sys
from project_standards.validate_frontmatter import main
if __name__ == "__main__":
    sys.exit(main())
```

That generated file is the "small wrapper executable" the body of this note kept referring to. It hardcodes the interpreter (so the right venv's Python and dependencies are used) and the `module:function` target. This is why a console script is the only one of the three invocation options that survives leaving the repo directory — **the wrapper lives in `bin/`, the code lives in the installed package, and neither depends on your current working directory or `PYTHONPATH`.**

> The `name = module:function` grammar is load-bearing. `validate_frontmatter:main` means "import `project_standards.validate_frontmatter`, call its `main()`." Each of this repo's CLI modules therefore exposes a `main()` that returns an int exit code — the wrapper's `sys.exit(main())` turns that into the process exit status (0/1/2/3, as the validators document).

### 4. The twist: this repo ships a git tag, not a wheel

Here is where "how _we_ release" diverges from the textbook. The textbook says: build a wheel, `uv publish` it to PyPI, consumers `uv add` it by name. **This repo does none of that.** From `deployed.md`: _"Deployed here means published git refs on `main`."_ There is no PyPI package. So where does the wheel come from?

**It is built on the consumer's machine, on demand, from the git ref.** All three distribution paths (the A/B/C earlier in this note) lean on the build backend to do exactly that:

```bash
# A — ephemeral: uv clones project-standards at tag v2, sees [build-system],
#     runs uv_build in a throwaway env, installs the wheel, runs the wrapper — then discards it.
uvx --from git+https://github.com/L3DigitalNet/project-standards@v2 validate-frontmatter --config .project-standards.yml

# B — pinned dev dep: same build, but the resolved commit is frozen in the consumer's uv.lock.
uv add --dev "project-standards @ git+https://…@v2"
```

So the build backend is not an artifact-publishing convenience here — **it is the thing that makes a bare git tag _executable_.** Without `[build-system]`, `uvx --from git+…` would clone the repo and then have no idea how to produce a runnable command from it. With it, every consumer becomes its own build frontend. The reusable CI workflow (path C) is the same story with the `uvx`/`uv run` hidden inside `.github/workflows/validate-markdown-frontmatter.yml`, so the consumer's workflow names neither the tool nor the build.

This also explains a subtlety in the pure-Python wheel tag: because the wheel is `py3-none-any`, the on-the-fly build is cheap and identical everywhere, and uv's global cache means a given commit is built once per machine and reused across repos.

### 5. What turns a tag into a contract — the release ritual

If "release" is just "move a tag," the discipline has to live in _how_ the tag is moved. `meta/versioning.md` is the governing document; the operational core:

| Step | What | Why it matters |
| --- | --- | --- |
| **Immutable full tag** | annotated, GPG-signed `vMAJOR.MINOR.PATCH` on the release commit; never moved or deleted once pushed | `@v2.0.0` and commit-SHA pins are byte-for-byte reproducible forever |
| **Moving major tag** | `vMAJOR` always points at the newest release in that major; moved by **delete-then-re-push**, never `git push --force` | `@v2` trackers inherit non-breaking fixes automatically; `--force` is blocked by the `release-pipeline` guard and can clobber branch history |
| **Version + lock bump** | bump `version` in `pyproject.toml` and regenerate `uv.lock` _in the release commit_ | so `uv tool install` / the on-demand build resolve a version that matches the tag |
| **Changelog** | move `## [Unreleased]` → `## [vX.Y.Z] — DATE`; a MAJOR must carry migration notes | the human contract beside the machine one |

The version number is not versioning a code API — it versions **the consuming repo's validation outcome**. The previously-passing rule: _if any change could turn a passing consumer into a failing one, it is MAJOR, no exceptions_ — even a bug fix. That is the whole reason `v1` was frozen at `1.2.0` and `v2` moved forward when the Python baseline jumped `>=3.11` → `>=3.14`: a breaking floor change cannot be allowed to silently reach `@v1` trackers. The tag is the blast-radius control; consumers cross the major boundary deliberately, on their own schedule.

### 6. The other build path — the `.pyz` zipapp, and why it's a constrained cousin

`scripts/build-validate-id-pyz.sh` produces a _second_, very different artifact, and contrasting it sharpens what the wheel/backend path buys you. A [zipapp](https://docs.python.org/3/library/zipapp.html) is a single executable `.pyz` file you can `scp` to a box that has neither uv nor network access:

```bash
python3 dist/validate-id.pyz --config .project-standards.yml   # no install, no venv, no uv
```

But it is built **without the backend** — `python -m zipapp` zips a hand-staged directory — and that forces three compromises the wheel never has to make, all stemming from one fact: **`zipimport` can only load pure-Python modules from inside a zip.**

- **PyYAML's C extension is deleted** (`find … -name '*.so' -delete`); PyYAML silently falls back to its slower pure-Python parser.
- **`jsonschema` is stubbed out**, not bundled — its real transitive dep `rpds-py` is a Rust extension that cannot live in a zipapp. The stub works only because `validate_id` imports `jsonschema` at module load but never actually _calls_ it.
- **Data files can't be read from inside the zip** — `Path(__file__).parent / "schemas"` raises `NotADirectoryError` against a zip member — so the generated `__main__.py` extracts the whole archive to a tempdir at startup and runs from there.

That fragility is the argument _for_ the build backend, restated from the opposite direction. The wheel path delegates all of this to a real installer and a real environment: C extensions install normally, transitive deps resolve in full, and `Path(__file__).parent` points at real files on disk. The `.pyz` is the right tool only when "must run on a locked-down host with no package manager" is a hard constraint — otherwise the `uvx`/wheel path (§4) is strictly less work and strictly more correct.

### 7. The whole pipeline in one pass

```text
   AUTHOR (this repo)                         RELEASE                       CONSUMER (×20)
   ─────────────────                          ───────                       ──────────────
   write code under                  bump version + uv.lock,          uvx --from git+…@v2 <script>
   src/project_standards/    ──▶      sign tag vX.Y.Z,         ──▶          │
   declare [project.scripts]          move major tag v2,                    ▼
   + [build-system]=uv_build          update CHANGELOG               uv clones @v2, sees [build-system],
        │                                  │                          runs uv_build → builds the wheel
        │                                  │                                 │
        ▼                                  ▼                                 ▼
   `uv build` →                     a git tag (NOT a               installer reads entry_points.txt,
   wheel with                       PyPI upload) is the            writes bin/<script> wrapper,
   entry_points.txt                 entire release artifact        wrapper runs module:main → exit code
```

The one-line takeaway: **the build backend is the hinge** that connects "I wrote a function called `main` in `src/`" to "20 repos can type `validate-frontmatter` after pinning a tag." It does so by encoding the `module:function` recipe into the wheel at build time, which the installer realises into a `PATH` executable at install time — and because the build runs on the consumer from a git ref, the only thing this repo ever "ships" is a signed, versioned tag.
