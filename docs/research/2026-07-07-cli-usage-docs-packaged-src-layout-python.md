---
schema_version: '1.1'
id: cli-usage-docs-packaged-src-layout-python
title: CLI Usage Documentation for Packaged src/-Layout Python Projects
description: Research on documentation conventions for packaged/installable Python CLIs — doc-site structure, entry-point-as-source-of-truth, man-page packaging limits, generated docs tooling, multi-entry-point layout, and CI drift checks for installed console scripts.
doc_type: research
status: active
created: 2026-07-07
updated: 2026-07-07
reviewed: 2026-07-07
owner: project-standards
consumer: agent
tags:
  - cli
  - packaging
  - python
  - documentation
  - entry-points
aliases:
  - packaged CLI docs
  - src-layout CLI documentation
  - console_scripts documentation standard
  - installable CLI docs
related:
  - standards/cli-documentation/README.md
source:
  - https://pip.pypa.io/en/stable/cli/pip_install
  - https://docs.astral.sh/uv/reference/cli
  - https://packaging.python.org/en/latest/specifications/entry-points
  - https://setuptools.pypa.io/en/latest/userguide/entry_point.html
  - https://setuptools.pypa.io/en/latest/userguide/datafiles.html
  - https://peps.python.org/pep-0427
  - https://discuss.python.org/t/should-there-be-a-new-standard-for-installing-arbitrary-data-files/7853
  - https://sphinx-click.readthedocs.io/en/latest/usage
  - https://github.com/mkdocs/mkdocs-click
  - https://github.com/sphinx-contrib/typer
  - https://python-cli-test-helpers.readthedocs.io/en/latest/tutorial.html
  - https://pypi.org/project/pytest-console-scripts
  - https://nvd.nist.gov/vuln/detail/CVE-2026-24049
confidence: high
visibility: public
license: Apache-2.0
---

# CLI Usage Documentation for Packaged src/-Layout Python Projects

Extends the single-file-script CLI documentation framework now published as `standards/cli-documentation/README.md` with the packaged/installable half: `src/` layout, `[project.scripts]` entry points, and consumers of the Python Tooling SSOT standard (uv, Ruff, BasedPyright, pytest).

## Summary

| Angle | Sources | Strongest finding |
| --- | --- | --- |
| Official Docs | 6 | `console_scripts`/`[project.scripts]` is the packaging-spec-defined mechanism; entry points, not raw `scripts=`, are the portable cross-platform default. |
| Best Practices | 5 | Doc-site structure should scale with subcommand-tree size: single page (ruff-style) below ~5-7 commands, one generated page per (sub)command (pip/gh-style) above that. |
| Footguns | 3+ | `data_files` is officially deprecated and unreliable with wheels; man pages shipped this way land under `sys.prefix` (the venv), not the system `MANPATH`. |
| Existing Tools | 8 | sphinx-click / mkdocs-click / sphinxcontrib-typer / sphinx-argparse-cli cover parser→docs generation for Click, Typer, and argparse respectively. |
| Security | 1 | CVE-2026-24049: path-traversal privilege-escalation bug in `wheel unpack` (fixed 0.47.0) — relevant to any doc/CI pipeline that unpacks wheels. |
| Recent Changes | 2 | PEP 772 (2026-04-16) creates a binding Python Packaging Council; OpenAI acquired Astral (2026-03-19), the maintainer of uv/Ruff/ty that this repo's tooling standard pins to. |

**Queries:** 17 · **Results parsed:** ~70 · **Deep reads:** 2 (`tavily_extract`) plus targeted snippet reads of 12+ official pages · **Follow-up pass:** no (all six angles cleared the 2-distinct-source bar on the first sweep)

## 1. Where the canonical doc lives, and how large multi-subcommand CLIs structure reference pages

The single-file-script standard's default (`docs/usage.md`, man-style headings) still holds as the **starting** shape for a packaged CLI, but real large CLIs diverge once the subcommand tree grows:

- **pip** generates one Markdown/Sphinx page per subcommand under `cli/pip_install`, `cli/pip_download`, `cli/pip` (global options/logging), each with its own `Options` section auto-extracted from pip's own optparse-based parser. [official] (<https://pip.pypa.io/en/stable/cli/pip_install>, <https://pip.pypa.io/en/stable/cli/pip_download>, <https://pip.pypa.io/en/stable/cli/pip>)
- **uv** (Astral) instead publishes one long consolidated "Commands" reference page enumerating every command and nested command (e.g. `uv`, `uv auth login`) on a single scrollable page, generated from the CLI's own argument-parsing metadata. [official] (<https://docs.astral.sh/uv/reference/cli>)
- **ruff** (Astral) has a narrow top-level command surface (`check`, `format`, `rule`, `config`, `server`) and instead invests its per-topic reference depth in **configuration** references (`/rules`, `/settings`, `/configuration`) rather than a page per subcommand — the CLI itself is thin; the surface that needs exhaustive reference depth is `pyproject.toml` settings, not subcommands. [official] (<https://docs.astral.sh/ruff/>, <https://docs.astral.sh/ruff/configuration/>)
- **gh** (GitHub CLI) is generated via Cobra's Go documentation generator into `cli.github.com/manual`, producing one page per top-level command/subcommand tree (`gh issue`, `gh pr`, `gh gpg-key`, …), each auto-emitted from the Cobra command struct metadata (this is a Go/Cobra analog of sphinx-click, not a Python tool, but it is the closest cross-language precedent to "deep multi-subcommand CLI doc site"). [official] (<https://cli.github.com/manual>)

**Inference for the standard:** the split point is subcommand-tree depth and breadth, not language. Keep the existing single-file `docs/usage.md` default while the tree is shallow (a handful of subcommands, one nesting level — this covers the large majority of internal tooling). Once a packaged CLI crosses roughly 5-7 top-level subcommands or introduces a second nesting level (subcommand groups), switch to a **generated** page-per-command layout (e.g. `docs/cli/<command>.md`, mirroring pip's `cli/pip_<verb>.md` pattern), produced by sphinx-click/mkdocs-click/sphinx-argparse-cli rather than hand-maintained, to avoid the page count becoming a hand-sync burden.

## 2. `console_scripts` / `[project.scripts]` as parser source of truth vs. `__main__`

- `[project.scripts]` (and its legacy setuptools `console_scripts` entry-point group) is the **packaging-spec-defined** mechanism: installers generate a small platform-specific wrapper executable (a text/shebang stub on POSIX, a compiled `.exe` launcher on Windows) that imports a referenced callable and invokes it with no arguments. [official] (<https://packaging.python.org/en/latest/specifications/entry-points>, <https://setuptools.pypa.io/en/latest/userguide/entry_point.html>)
- `pypa/installer` (the reference wheel-installation library) only installs `entry_points`-declared console scripts, **not** raw `scripts=` files — the legacy `scripts=` keyword is effectively unsupported for reliable cross-platform (esp. Windows) distribution; entry points replaced it precisely because a raw script has no cross-platform launcher story. [official, PyPA discourse] (<https://discuss.python.org/t/whats-the-status-of-scripts-vs-entry-points/18524>)
- **Practical consequence for docs and CI:** in a single-file script or a `__main__.py` invoked via `python -m pkg`, `argparse`'s `prog` defaults to the invoked file's basename (`sys.argv[0]`), so `--help`/error output naturally shows the script's filename. In a packaged CLI, the user-facing invocation is the **installed wrapper name** (the entry-point key, e.g. `toolname`), which is a generated launcher, not the module file — so:
  - `NAME`/`SYNOPSIS` sections must use the entry-point key as the command name, never the module path or file name.
  - Automated help/man/doc generation must shell out to the **installed** command (post `pip install .` / `uv tool install .`), not `python -m pkg.__main__` or `python pkg/cli.py` — the two invocation styles can disagree on `prog` unless the parser explicitly pins `prog=` to the entry-point name.
- Community practice (2+ independent sources: a widely cited chriswarrick.com walkthrough [blog] and the MLOps Coding Course [community]) converges on wiring `__main__.py` and `[project.scripts]` to call the _same_ `main()` so `python -m pkg` and the installed script stay behaviorally identical — but both still recommend pinning `prog` explicitly if the two invocation strings must ever diverge in shown help text. (<https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts>, <https://mlops-coding-course.fmind.dev/3.%20Productionizing/3.3.%20Entrypoints.html>)

## 3. Shipping/installing man pages with wheels and sdists

**Footgun, corroborated across an official source plus PyPA discourse plus a detailed community writeup:**

- setuptools' own docs state plainly that `data_files` **is deprecated and does not work reliably with wheels**, and direct readers instead toward in-package resource files (which do not solve OS-integration needs like man pages). [official] (<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>)
- PEP 427 (the wheel format spec) defines a `<pkg>-<ver>.data/` directory with exactly **eight** fixed `sysconfig`-mapped subkeys (`purelib`, `platlib`, `headers`, `scripts`, `data`, plus a few less common ones) — there is no dedicated "man page" category; a man page has to be placed under the generic `data` subkey and mapped to `share/man/man1/` via `sysconfig`, and every installer is free to interpret unknown subkey names differently. [official] (<https://peps.python.org/pep-0427>)
- The multi-year PyPA discourse thread "Should there be a new standard for installing arbitrary data files?" confirms **no PEP has been accepted** to formalize OS-integration files (man pages, `.desktop` launchers, systemd units) for wheels as of this research date; current behavior is implementation-defined per installer (pip vs. `installer` vs. Poetry), and wheels only reliably support the sysconfig-known path categories — installing outside `sys.prefix` is explicitly _not_ something any current proposal supports. [official, PyPA discourse] (<https://discuss.python.org/t/should-there-be-a-new-standard-for-installing-arbitrary-data-files/7853>)
- A detailed community writeup, cross-checked against Hatch's own `shared-data` feature docs, shows the practical modern replacement: Hatchling's `[tool.hatch.build.targets.wheel.shared-data]` (and Flit's analogous `shared-data`) map source files to `share/man/man1/toolname.1` inside the wheel's `.data/data/` directory — the backend-native successor to setuptools' deprecated `data_files`. [blog + official tool docs] (<https://blog.raek.se/2022/10/31/os-integration-files-in-python-packages>)

**Bottom line:** modern Python packaging _does_ still support shipping a man page (via wheel `.data/data/` + Hatchling/Flit shared-data, or setuptools `data_files` as a still-functional-but-deprecated escape hatch), but there is no first-class "man page" packaging primitive and no guarantee it lands on the runtime `MANPATH` — installed files go under `sys.prefix`, which is the **virtualenv**, not `/usr/share/man`, for the common `pip install` case. `man toolname` will frequently fail to find a wheel-installed man page unless `MANPATH` is extended or the tool is installed system-wide (e.g. via `pipx`, which does expose data files under its own prefix, or an OS package built from the sdist). **Recommendation:** treat man-page installation as best-effort/optional; document it as such; keep `--help` and `docs/usage.md` (or the generated per-command pages from §1) as the non-negotiable primary channels regardless of whether the man page installs correctly in every environment.

## 4. Docs-site generation from parser metadata

Tooling landscape for parser→docs extraction, mapped to the three dominant Python CLI frameworks:

| Framework | Sphinx tool | MkDocs tool |
| --- | --- | --- |
| Click | `sphinx-click` [official tool docs] | `mkdocs-click` [official tool docs] |
| Typer | `sphinxcontrib-typer` (2025-era, uses Typer's own Rich console formatting for HTML/text/SVG) [official tool docs] | `mkdocs-typer2` (actively maintained; explicit "pretty" table rendering; supersedes the less-maintained `mkdocs-typer`) [community] |
| argparse | `sphinx-argparse` / `sphinx-argparse-cli` (the latter specifically markets subcommand-friendly rendering) [official tool docs] | no dedicated first-party MkDocs equivalent found |

(<https://sphinx-click.readthedocs.io/en/latest/usage>, <https://github.com/mkdocs/mkdocs-click>, <https://github.com/sphinx-contrib/typer>, <https://github.com/bruce-szalwinski/mkdocs-typer> and its "2" successor, <https://pypi.org/project/sphinx-argparse-cli>)

`mkdocs-click` and `mkdocs-typer(2)` both recurse into subcommands automatically when pointed at the root command/group, generating one Markdown heading tree per invocation rather than requiring one block per subcommand — this directly supports the "generate the page-per-command tree" recommendation from §1. [official tool docs]

**Versioned docs hosting** — thin coverage: no source directly addressed a canonical version-pinned hosting pattern _specific to packaged-CLI reference pages_. Generic options surfaced (Read the Docs' native version selector for Sphinx sites; `mike` for MkDocs Material multi-version sites; or a single-version static site like `docs.astral.sh`) but none of the sources compared them for CLI-reference use specifically — flagged as an Open Question below.

## 5. Monorepo / multiple-entry-point packages

- A PyPA discourse thread on "Multiple related programs: one `pyproject.toml`, or multiple projects?" shows no settled community convention: teams split between (a) one `pyproject.toml` with several `[project.scripts]` entries sharing one dependency set, and (b) separate packages/subprojects when the programs need independent versioning or dependency isolation. [official, PyPA discourse] (<https://discuss.python.org/t/multiple-related-programs-one-pyproject-toml-or-multiple-projects/17427>)
- Two structurally identical patterns, corroborated across Click's own docs plus 3+ independent Stack Overflow threads reaching the same solution:
  1. Register each command as its own `console_scripts`/`[project.scripts]` key pointing at a distinct function (`command_1 = pkg.cli:function_command_1`), for genuinely independent commands. [official + community] (<https://click.palletsprojects.com/en/stable/entry-points>, multiple Stack Overflow threads)
  2. Register a single top-level Click "group" as the one entry point, then split subcommand implementations into separate modules under `commands/*.py` and auto-discover/register them with `add_command()` — used when subcommands share substantial context/state. [official] (<https://click.palletsprojects.com/en/stable/commands>)
- A 2024-era blog post on structuring multi-entry-point projects explicitly rejects `sys.path` hacks in favor of a proper `pyproject.toml` package with a shared internal library module consumed by each entry-point script. [blog] (<https://blog.claude.nl/posts/how-to-structure-a-python-project-with-multiple-entry-points>)

**Doc layout implication:** map one usage-reference page (or generated doc section) to each distinct **installed command name** (i.e., each `[project.scripts]` key), and factor shared concepts (a common config file format, shared environment variables, a shared exit-code table) into one cross-referenced "shared concepts" doc rather than repeating them per command — the same pattern `gh`/`kubectl`-style plugin command families use.

## 6. CI drift checks specific to installed-package CLIs

**Footgun, corroborated across 3 independent official/tool sources:** a CI suite built entirely on in-process testing (Click's `CliRunner`, direct function calls, or `python -m pkg`) does **not** prove the packaged, installed console-script entry point actually works.

- `pytest-console-scripts` [official tool docs] is a pytest plugin purpose-built to invoke the **installed** `console_scripts`/`[project.scripts]` entry point — either in-process or via a real subprocess — specifically to close the gap where module-level tests pass but the actual installed wrapper is broken (bad entry-point string, missing package metadata, etc.). (<https://pypi.org/project/pytest-console-scripts>)
- `python-cli-test-helpers` [official tool docs] frames its first-tier smoke test explicitly as _"is the entrypoint script installed?"_ — testing the `pyproject.toml` `[project.scripts]` configuration itself — before a second tier that tests importability, an explicit acknowledgment that entry-point registration is a distinct failure mode from import-level or logic-level correctness. (<https://python-cli-test-helpers.readthedocs.io/en/latest/tutorial.html>)
- Click's own testing documentation scopes `CliRunner` to **in-process** invocation (it replaces `sys.stdout`/`sys.stderr` in the current interpreter); it does not exercise the real installed wrapper, real subprocess environment-variable propagation, or the entry point's actual `prog`/`sys.argv[0]` naming. [official] (<https://click.palletsprojects.com/en/stable/testing>)

**Recommendation for the standard:** require at least one CI job that does a clean `pip install .` (or `uv pip install .` / `uv tool install .`) into a fresh environment and then runs `toolname --help` (and ideally one real subcommand) via `subprocess`, in addition to any in-process `CliRunner`/unit-level tests. This is the packaged-CLI analog of the single-file standard's "`tool --help` smoke test" requirement, but it must target the **installed** command, not the module.

## Security and Compatibility

- **CVE-2026-24049** [official — NVD, GitHub Advisory Database, GitLab Advisory DB]: the `wheel unpack` CLI command (and the vendored copy inside older setuptools) had a path-traversal bug (CWE-22, CVSS 7.1) in versions 0.40.0–0.46.1: a maliciously crafted wheel's zip entry filenames could point `chmod` operations outside the extraction directory, enabling arbitrary file-permission modification / privilege escalation. Fixed in `wheel` 0.47.0. Relevant to this topic because any documentation or CI pipeline step that unpacks a built wheel (e.g. to extract a shipped man page or inspect `RECORD`/metadata for doc-parity checks) should pin `wheel>=0.47.0`. (<https://nvd.nist.gov/vuln/detail/CVE-2026-24049>, <https://github.com/advisories/GHSA-8rrh-rw8j-w5fx>)

## Recent Changes

- **PEP 772**, accepted 2026-04-16, creates a binding **Python Packaging Council** with authority over packaging standards decisions. [official] (<https://github.com/python/peps/blob/main/peps/pep-0777.rst>, cited via Real Python's May 2026 roundup) — future proposals to formalize man-page/OS-integration-file installation (§3) will likely route through this body rather than ad hoc PyPA discourse threads; worth revisiting near any such proposal.
- **OpenAI acquired Astral** (2026-03-19), the maintainer of `uv`, `Ruff`, and `ty` — the toolchain this repo's Python Tooling SSOT standard pins to. Both parties state existing OSS licensing and open development continue, with the Astral team joining OpenAI's Codex org. [official — OpenAI and Astral's own announcements, corroborated independently by Simon Willison and the JetBrains PyCharm blog] (<https://openai.com/index/openai-to-acquire-astral>, <https://simonwillison.net/2026/Mar/19/openai-acquiring-astral>, <https://blog.jetbrains.com/pycharm/2026/03/openai-acquires-astral-what-it-means-for-pycharm-users>) — a governance change worth flagging in any standard that pins its toolchain to Astral's projects, though no functional/licensing change has occurred as of this research date.

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| --- | --- | --- | --- |
| `sphinx-click` | Active | <https://sphinx-click.readthedocs.io/en/latest/usage> | Click parser → Sphinx docs, nested command support |
| `mkdocs-click` | Active | <https://github.com/mkdocs/mkdocs-click> | Click parser → MkDocs, recursive subcommand generation |
| `sphinxcontrib-typer` | Active (2025+) | <https://github.com/sphinx-contrib/typer> | Typer/Click → Sphinx, Rich-formatted HTML/text/SVG output |
| `mkdocs-typer2` | Active | PyPI: `mkdocs-typer2` | Typer → MkDocs, maintained successor to stale `mkdocs-typer` |
| `sphinx-argparse-cli` | Active | <https://pypi.org/project/sphinx-argparse-cli> | argparse (incl. subcommands) → Sphinx |
| `pytest-console-scripts` | Active | <https://pypi.org/project/pytest-console-scripts> | Tests the _installed_ entry point, not just the module |
| `python-cli-test-helpers` | Active | <https://python-cli-test-helpers.readthedocs.io/en/latest/tutorial.html> | Tiered smoke tests: entry-point installed → importable → runs |
| Hatchling `shared-data` / Flit `shared-data` | Official build-backend feature | <https://blog.raek.se/2022/10/31/os-integration-files-in-python-packages> | Modern backend-native replacement for deprecated `data_files`; can ship man pages |

None of these individually cover the full packaged-CLI documentation lifecycle end to end (parser→docs, entry-point testing, and man-page shipping are three separate concerns handled by three separate tool families) — no single existing solution supersedes building this out as a standard.

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | What is the recommended versioned-docs-hosting pattern specifically for packaged-CLI reference pages (Read the Docs version selector vs. `mike`/MkDocs Material versioning vs. single-version static sites like `docs.astral.sh`)? | Sources described the generation tooling (§4) but none directly compared hosting/versioning strategies for CLI reference docs specifically; only one angle-relevant source surfaced. |
| 2 | Does the new PEP 772 Python Packaging Council have any active proposal to formalize man-page/OS-integration-file installation in wheels? | No source found addressing post-PEP-772 packaging-council agenda items; worth a follow-up check nearer a proposal date. |

## Handoff

Persisted at `docs/research/2026-07-07-cli-usage-docs-packaged-src-layout-python.md`. Downstream skills that may consume it:

- `superpowers:brainstorming` — feed the two Open Questions and the §1/§5 doc-layout tradeoffs into a design conversation before drafting future packaged-CLI refinements to `standards/cli-documentation/README.md`.
- `feature-dev:feature-dev` — start the packaged-CLI documentation-standard authoring work with this background, including the CI-drift-check requirement from §6.

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| <https://pip.pypa.io/en/stable/cli/pip_install> | pip install — pip documentation | current | official |
| <https://pip.pypa.io/en/stable/cli/pip_download> | pip download — pip documentation | current | official |
| <https://pip.pypa.io/en/stable/cli/pip> | pip — pip documentation | current | official |
| <https://docs.astral.sh/uv/reference/cli> | Commands \| uv | current | official |
| <https://docs.astral.sh/ruff/> | Ruff — Astral Docs | current | official |
| <https://docs.astral.sh/ruff/configuration/> | Configuring Ruff — Astral Docs | current | official |
| <https://cli.github.com/manual> | GitHub CLI Manual | current | official |
| <https://packaging.python.org/en/latest/specifications/entry-points> | Entry points specification | current | official |
| <https://setuptools.pypa.io/en/latest/userguide/entry_point.html> | Entry Points — setuptools docs | current | official |
| <https://discuss.python.org/t/whats-the-status-of-scripts-vs-entry-points/18524> | What's the status of scripts vs entry_points? | 2023 | official (PyPA discourse) |
| <https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts> | Python Apps the Right Way: entry points and scripts | 2014 (still cited) | blog |
| <https://mlops-coding-course.fmind.dev/3.%20Productionizing/3.3.%20Entrypoints.html> | 3.3. Entrypoints — MLOps Coding Course | current | community |
| <https://setuptools.pypa.io/en/latest/userguide/datafiles.html> | Data Files Support — setuptools docs | current | official |
| <https://peps.python.org/pep-0427> | PEP 427 – The Wheel Binary Package Format 1.0 | current | official |
| <https://discuss.python.org/t/should-there-be-a-new-standard-for-installing-arbitrary-data-files/7853> | Should there be a new standard for installing arbitrary data files? | 2022–2025 | official (PyPA discourse) |
| <https://blog.raek.se/2022/10/31/os-integration-files-in-python-packages> | OS Integration Files in Python Packages | 2022 | blog |
| <https://sphinx-click.readthedocs.io/en/latest/usage> | sphinx-click usage docs | current | official |
| <https://github.com/mkdocs/mkdocs-click> | mkdocs-click | current | official |
| <https://github.com/sphinx-contrib/typer> | sphinxcontrib-typer | current | official |
| <https://github.com/bruce-szalwinski/mkdocs-typer> | mkdocs-typer | current | community |
| <https://pypi.org/project/sphinx-argparse-cli> | sphinx-argparse-cli | current | official |
| <https://discuss.python.org/t/multiple-related-programs-one-pyproject-toml-or-multiple-projects/17427> | Multiple related programs: one pyproject.toml, or multiple projects? | 2022–2025 | official (PyPA discourse) |
| <https://click.palletsprojects.com/en/stable/entry-points> | Packaging Entry Points — Click Documentation | current | official |
| <https://click.palletsprojects.com/en/stable/commands> | Commands and Groups — Click Documentation | current | official |
| <https://blog.claude.nl/posts/how-to-structure-a-python-project-with-multiple-entry-points> | How to structure a python project with multiple entry points | 2024 | blog |
| <https://pypi.org/project/pytest-console-scripts> | pytest-console-scripts | current | official |
| <https://python-cli-test-helpers.readthedocs.io/en/latest/tutorial.html> | Python CLI Test Helpers — Tutorial | current | official |
| <https://click.palletsprojects.com/en/stable/testing> | Testing Click Applications — Click Documentation | current | official |
| <https://nvd.nist.gov/vuln/detail/CVE-2026-24049> | CVE-2026-24049 Detail — NVD | 2026 | official |
| <https://github.com/advisories/GHSA-8rrh-rw8j-w5fx> | GitHub Advisory: wheel path traversal | 2026 | official |
| <https://github.com/python/peps/blob/main/peps/pep-0777.rst> | PEP 772 reference (via peps repo) | 2026 | official |
| <https://realpython.com/python-news-may-2026> | A New Python Packaging Council and Other News for May 2026 | 2026-05 | community |
| <https://openai.com/index/openai-to-acquire-astral> | OpenAI to acquire Astral | 2026-03-19 | official |
| <https://simonwillison.net/2026/Mar/19/openai-acquiring-astral> | Thoughts on OpenAI acquiring Astral and uv/ruff/ty | 2026-03-19 | blog |
| <https://blog.jetbrains.com/pycharm/2026/03/openai-acquires-astral-what-it-means-for-pycharm-users> | OpenAI Acquires Astral: What It Means for PyCharm Users | 2026-03 | community |
