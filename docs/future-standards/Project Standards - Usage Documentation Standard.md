---
title: 'Project Standards - Usage Documentation Standard'
source: 'https://chatgpt.com/g/g-p-6a24ec06cda08191be0c41f4bfaefada/c/6a4d1f3b-48dc-83ea-b03f-3bbb316a53c9'
---

**You:**

I have several get repositories for projects that each have many different tools included that our user facing or acquire user interaction. Typical documentation is more developer based, and I want to add on a strictly user facing documentation layer for using tooling. I would like this to be in a wiki like structure with lots of cross referencing. I don’t want to host it separately from it will live within the get repository that it concerns since these are mostly for my own cases. Perform a comprehensive search to consider the different solutions that might work given these constraints. A basic directory tree of organized marked on files would work, but it can be annoying fussing with markdown viewers which are typically bolted on separately from Texas editors that I work with. I’m potentially thinking about something that allows a static web server to be spun up on the local machine for viewing the repo documentation live in a web browser in a much more easy to consume fashion

---

**ChatGPT:**

I’ll treat this as a repo-local user-docs architecture decision, not a generic “best docs tool” list. I’m going to compare mature static/wiki-ish options against your constraints: Markdown-first, cross-linkable, local preview server, no separate hosted CMS, and low friction across multiple repos.

I’m already seeing a likely split: “wiki app” tools are worse fits because they introduce a running service, DB, or sync layer; static documentation generators fit the repo-local/local-browser requirement much better. MkDocs/Material is emerging as the practical default, with VitePress/Starlight as strong JS-side alternatives.

# Repo-local user-facing documentation systems

**Date:** July 7, 2026

## Bottom line

Use **MkDocs + Material for MkDocs** as the default for your per-repository user-facing docs layer.

It fits your constraints best: Markdown files live inside the same Git repo, it has a local live-preview server, produces a browser-friendly static site, has built-in search, supports normal relative Markdown links, and stays close to your Python/Markdown workflow. MkDocs explicitly targets “project documentation with Markdown,” uses a single YAML config, and ships a live dev server with auto-reload. Material adds a much better reading/search/navigation experience on top. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org+2![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org+2](https://www.mkdocs.org/?utm_source=chatgpt.com)

My recommended pattern:

```
repo/
  README.md
  mkdocs.yml
  user-docs/
    index.md
    start-here.md
    tools/
      index.md
      tool-a/
        index.md
        quickstart.md
        commands.md
        examples.md
        troubleshooting.md
      tool-b/
        index.md
        quickstart.md
        commands.md
        examples.md
    workflows/
    concepts/
    reference/
    troubleshooting/
    glossary.md
```

Set `docs_dir: user-docs` so the user-facing layer is intentionally separate from developer docs, specs, ADRs, implementation notes, and README content. MkDocs supports configuring the documentation source directory and output site directory. [![](https://www.google.com/s2/favicons?domain=https://mkdocs.readthedocs.io&sz=128)mkdocs.readthedocs.io+1](https://mkdocs.readthedocs.io/en/0.13.3/user-guide/configuration/?utm_source=chatgpt.com)

---

## Recommendation

### Primary choice: MkDocs + Material

This is the best default for your case.

Why it fits:

| Requirement | Fit |
| --- | --- |
| Lives inside each Git repo | Yes. Plain Markdown plus `mkdocs.yml`. |
| User-facing, not developer-facing | Easy to isolate with `user-docs/` or `docs/user/`. |
| Wiki-like cross-referencing | Use normal relative Markdown links; MkDocs rewrites them to HTML links during build. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org](https://www.mkdocs.org/user-guide/writing-your-docs/?utm_source=chatgpt.com) |
| Browser-based reading | `mkdocs serve` gives local browser preview at localhost with auto-reload. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org](https://www.mkdocs.org/getting-started/?utm_source=chatgpt.com) |
| Search | MkDocs includes a default search plugin; Material improves the experience. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org+1](https://www.mkdocs.org/user-guide/configuration/?utm_source=chatgpt.com) |
| Low operational burden | No database, no hosted wiki, no sync service. |
| LLM-friendly | Source remains ordinary Markdown in the repo. |
| Multi-project repeatability | Use the same `mkdocs.yml` pattern in every repo. |

Material also has tags support, which helps recover some wiki-like discoverability across a larger documentation set without turning the docs into an unstructured graph. [![](https://www.google.com/s2/favicons?domain=https://squidfunk.github.io&sz=128)squidfunk.github.io](https://squidfunk.github.io/mkdocs-material/plugins/tags/?utm_source=chatgpt.com)

Suggested local workflow:

```Bash
uv add --dev mkdocs mkdocs-material
uv run mkdocs serve
uv run mkdocs build --strict
```

Use `mkdocs build --strict` as a CI/local check so broken internal links and warnings become failures; MkDocs has validation settings for link diagnostics intended to work with strict builds. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org+1](https://www.mkdocs.org/user-guide/configuration/?utm_source=chatgpt.com)

One caveat: MkDocs core itself has not been moving as quickly as some newer JS-based tools, while Material remains very actively used and maintained. For your use case, that is not a dealbreaker because the core job is stable: Markdown in, static docs site out. If you were building a large public docs platform with heavy custom interactivity, I would weigh VitePress, Starlight, or Docusaurus more heavily.

---

## Strong alternatives

### VitePress

VitePress is the best alternative if you want a very fast, modern JS docs stack without Docusaurus’s React/MDX weight. It is a Vite/Vue-powered static site generator that turns Markdown into docs, supports file-based routing, has a local search option, and gives a very good dev-server experience. [![](https://www.google.com/s2/favicons?domain=https://vitepress.dev&sz=128)VitePress+2![](https://www.google.com/s2/favicons?domain=https://vitepress.dev&sz=128)VitePress+2](https://vitepress.dev/?utm_source=chatgpt.com)

Use it when:

| Use VitePress if… | Avoid it if… |
| --- | --- |
| You already have Node/Vite/Vue tooling in the repo. | You want the docs tooling to stay Python/uv-native. |
| You want a slick docs site with minimal ceremony. | You dislike maintaining JS package/tooling for docs. |
| You want Markdown-first docs but may add Vue components later. | You want completely boring Markdown with no temptation toward components. |

It is a credible second choice. For your Python-heavy CLI/tooling projects, I would still default to MkDocs.

---

### Astro Starlight

Starlight is a polished Astro-based documentation framework. It supports Markdown, MDX, and Markdoc, has built-in site navigation/search/i18n features, and is explicitly designed for documentation sites. [![](https://www.google.com/s2/favicons?domain=https://starlight.astro.build&sz=128)Starlight+2![](https://www.google.com/s2/favicons?domain=https://starlight.astro.build&sz=128)Starlight+2](https://starlight.astro.build/?utm_source=chatgpt.com)

Use it when:

| Use Starlight if… | Avoid it if… |
| --- | --- |
| You want a modern public-docs-quality reading experience. | You want the lowest possible repo/doc structure overhead. |
| You may later want custom pages/components. | You do not want `src/content/docs/` and Astro project structure in utility repos. |
| You are comfortable with Astro/Node. | You want plain `docs/` or `user-docs/` to be the docs root with minimal framework assumptions. |

Starlight is excellent, but it is more “site framework” than “just render my repo-local Markdown docs.”

---

### Docusaurus

Docusaurus is powerful and mature, especially for public-facing product docs. It supports MDX, autogenerated sidebars, versioning, docs/blog/pages, and React customization. [![](https://www.google.com/s2/favicons?domain=https://docusaurus.io&sz=128)Docusaurus+2![](https://www.google.com/s2/favicons?domain=https://docusaurus.io&sz=128)Docusaurus+2](https://docusaurus.io/?utm_source=chatgpt.com)

Use it when:

| Use Docusaurus if… | Avoid it if… |
| --- | --- |
| You need polished public product docs. | You want simple local-only docs for personal tools. |
| You need versioned docs tied to releases. | MDX/React feels like unnecessary surface area. |
| You may want marketing/docs/blog in one site. | You want pure Markdown with minimal build complexity. |

For your stated use case, Docusaurus is probably more platform than you need.

---

## Lightweight/specialized options

### mdBook

mdBook is very good when the documentation is book-like: a linear guide, handbook, or manual. It uses Markdown, has live rebuild/refresh via `mdbook serve`, and produces a clean static site. [![](https://www.google.com/s2/favicons?domain=https://rust-lang.github.io&sz=128)rust-lang.github.io](https://rust-lang.github.io/mdBook/guide/creating.html?utm_source=chatgpt.com)

Use it for:

```
user-manual/
  book.toml
  src/
    SUMMARY.md
    introduction.md
    installation.md
    usage.md
    reference.md
```

Good fit for “one tool, one manual.” Weaker fit for “many tools, many cross-linked topic pages.”

---

### Docsify

Docsify is the lowest-friction web-rendered Markdown option. It does not generate static HTML at build time; it loads/parses Markdown in the browser and can use a static server or GitHub Pages. It has plugins including full-text search. [![](https://www.google.com/s2/favicons?domain=https://docsify.js.org&sz=128)Docsify+1](https://docsify.js.org/?utm_source=chatgpt.com)

Use it when:

| Use Docsify if… | Avoid it if… |
| --- | --- |
| You want near-zero setup. | You want build-time validation. |
| You want `index.html` + Markdown files. | You want stronger navigation control and link checking. |
| Docs are small and personal. | Docs should be durable, linted, and CI-checked. |

It is tempting, but I would not make it your standard. The lack of a real build step is convenient until you want validation, link integrity, and repeatable output.

---

### Sphinx + MyST

Sphinx is the most powerful technical-documentation engine here. It supports reStructuredText or MyST Markdown, strong cross-referencing, references across projects, citations, glossaries, tables, code blocks, and deep structured docs. [![](https://www.google.com/s2/favicons?domain=https://www.sphinx-doc.org&sz=128)Sphinx Documentation+2![](https://www.google.com/s2/favicons?domain=https://www.sphinx-doc.org&sz=128)Sphinx Documentation+2](https://www.sphinx-doc.org/?utm_source=chatgpt.com)

Use it when:

| Use Sphinx/MyST if… | Avoid it if… |
| --- | --- |
| You need serious cross-reference semantics. | You just need readable user docs for CLI tools. |
| You need API docs generated from Python. | You do not want Sphinx config/extension complexity. |
| You need citations, glossary, object refs, intersphinx. | You want simple Markdown and simple local preview. |

For your user-facing tooling docs, Sphinx is probably overkill unless you also need generated API/reference docs from Python objects.

---

## Wiki-like tools

### Gollum

Gollum is the closest match to a true Git-backed local wiki. It is a Git-powered wiki with a local frontend and supports Markdown plus additional wiki/documentation features such as Mermaid, PlantUML, math, macros, redirects, and more. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/gollum/gollum/?utm_source=chatgpt.com)

Use it only if browser-side wiki editing is important.

It is not my default recommendation because your desired artifact is really **repo-local user documentation**, not a collaborative mutable wiki. Gollum’s wiki model is useful, but it is less suited to disciplined product/user docs with a stable navigation structure.

---

### Quartz

Quartz is strong for digital gardens, backlinks, graphs, and note networks. Its own documentation describes it as a static-site generator for transforming Markdown content into functional websites. [![](https://www.google.com/s2/favicons?domain=https://quartz.jzhao.xyz&sz=128)Quartz](https://quartz.jzhao.xyz/?utm_source=chatgpt.com)

I would not use Quartz for formal user docs unless backlinks/graph navigation matter more than task-oriented documentation. It leans toward networked notes, not product manuals. Given your prior direction away from Obsidian-style workflows, Quartz is probably the wrong default.

---

### Foam / VS Code wiki extensions

Foam is a VS Code + Git personal knowledge management system with wiki links, backlinks, graph visualization, tags, and publishing support. [![](https://www.google.com/s2/favicons?domain=https://foambubble.github.io&sz=128)Foam Bubble](https://foambubble.github.io/foam/?utm_source=chatgpt.com)

This solves the editing/navigation side inside VS Code, but not the “local static web docs site for each repo” requirement as cleanly as MkDocs/VitePress/Starlight. It is better for a personal knowledge base than user-facing repo docs.

---

## Tools I would reject for this use case

| Tool/category | Why I would not use it as the standard |
| --- | --- |
| **BookStack** | Good self-hosted wiki, but it is an application/platform, not repo-local Markdown docs. BookStack describes itself as self-hosted wiki software for organizing information. [![](https://www.google.com/s2/favicons?domain=https://www.bookstackapp.com&sz=128)BookStack](https://www.bookstackapp.com/?utm_source=chatgpt.com) |
| **Wiki.js** | Has Git storage sync, but it introduces a wiki service and sync layer. That is unnecessary if the docs already live in each repo. [![](https://www.google.com/s2/favicons?domain=https://docs.requarks.io&sz=128)Wiki.js](https://docs.requarks.io/storage/git?utm_source=chatgpt.com) |
| **DokuWiki** | File-based and no DB, but it is still a wiki app with its own conventions rather than repo-local Markdown docs. [![](https://www.google.com/s2/favicons?domain=https://www.dokuwiki.org&sz=128)dokuwiki.org](https://www.dokuwiki.org/dokuwiki?utm_source=chatgpt.com) |
| **Backstage TechDocs** | Built around docs-as-code and MkDocs, but intended for a developer portal and CI/CD publishing. Overkill for local personal project docs. [![](https://www.google.com/s2/favicons?domain=https://backstage.io&sz=128)backstage.io+1](https://backstage.io/docs/features/techdocs/creating-and-publishing/?utm_source=chatgpt.com) |
| **Antora** | Excellent for large multi-repo, versioned product docs, but AsciiDoc-first and heavier than needed. Antora is designed for docs composed from one or more versioned content repositories. [![](https://www.google.com/s2/favicons?domain=https://antora.org&sz=128)antora.org](https://antora.org/?utm_source=chatgpt.com) |
| **Hugo + Docsy** | Capable and mature, but more general static-site machinery than needed. Docsy is a Hugo theme, and Hugo handles the static build from Markdown/HTML sources. [![](https://www.google.com/s2/favicons?domain=https://www.docsy.dev&sz=128)Docsy+1](https://www.docsy.dev/docs/?utm_source=chatgpt.com) |
| **GitBook SaaS** | Good reading experience, but it moves you toward a hosted docs platform rather than repo-local tooling. GitBook positions itself as a knowledge platform with Git sync and AI features. [![](https://www.google.com/s2/favicons?domain=https://www.gitbook.com&sz=128)gitbook.com](https://www.gitbook.com/?utm_source=chatgpt.com) |

---

## Proposed standard

For each repo that contains user-facing tools:

```
repo/
  README.md                 # project/dev landing page
  mkdocs.yml                # user-docs site config
  user-docs/
    index.md                # user landing page
    start-here.md           # first-use orientation
    tools/
      index.md
      <tool-name>/
        index.md
        quickstart.md
        usage.md
        commands.md
        options.md
        examples.md
        troubleshooting.md
    workflows/
    concepts/
    reference/
    troubleshooting/
    glossary.md
```

Use Diátaxis as the content model: tutorials, how-to guides, reference, and explanation. The framework is explicitly built around those four user needs, and that maps well to tool documentation: quickstarts/tutorials for learning, workflows/how-tos for tasks, command/options pages for reference, and concepts/troubleshooting for explanation. [![](https://www.google.com/s2/favicons?domain=https://diataxis.fr&sz=128)diataxis.fr+1](https://diataxis.fr/?utm_source=chatgpt.com)

A practical `mkdocs.yml` shape:

```YAML
site_name: '<Project Name> User Docs'
docs_dir: user-docs
site_dir: .site/user-docs

theme:
  name: material
  features:
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - search.suggest
    - search.highlight

plugins:
  - search
  - tags

markdown_extensions:
  - admonition
  - toc:
      permalink: true

validation:
  links:
    absolute_links: warn
    unrecognized_links: warn
```

For larger docs, add navigation tooling only when needed. `mkdocs-literate-nav` lets you maintain navigation as Markdown rather than a giant YAML list, while `mkdocs-awesome-nav` gives directory-level navigation control without listing every page manually. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub+1](https://github.com/oprypin/mkdocs-literate-nav?utm_source=chatgpt.com)

## Final ranking

| Rank | Tool | Verdict |
| --- | --- | --- |
| 1 | **MkDocs + Material** | Best default. Boring, Markdown-first, browser-friendly, repo-local, Python-compatible. |
| 2 | **VitePress** | Best lightweight JS alternative. Excellent if the repo already uses Vite/Node. |
| 3 | **Astro Starlight** | Best modern docs-site UX, but more framework structure. |
| 4 | **Docusaurus** | Best for public/versioned product docs, heavier than needed here. |
| 5 | **mdBook** | Great for linear manuals, less good for wiki-like tool collections. |
| 6 | **Docsify** | Very simple, but weaker validation and durability. |
| 7 | **Sphinx + MyST** | Most powerful, but too heavy unless you need rich semantic cross-references or API docs. |
| 8 | **Gollum / Quartz / Foam** | Useful wiki/note tools, but not ideal as the standard for formal repo-local user docs. |

## Sources

Key sources used: MkDocs, Material for MkDocs, VitePress, Astro Starlight, Docusaurus, mdBook, Docsify, Sphinx/MyST, Antora, Hugo/Docsy, Gollum, Quartz, Wiki.js, BookStack, Backstage TechDocs, and Diátaxis official/project documentation.

---

**You:**

MK docs plus material is perfect. Create a comprehensive adoption document that I can feed to an agent working in my repo to adopt the your recommended stack. Reiterate that this is specifically for the user facing documentation for usage of the tools in the repo. It is not for developer, documentation handoff documentation scratch purposes. It’s not for explanation of how something was built or what’s inside of it that the user doesn’t see. This is strictly for telling the user how to use the tools at the repo provides beyond that is out of scope.

---

**ChatGPT:**

I’ll turn this into an implementer-ready adoption spec, with hard scope boundaries so the agent does not turn the docs tree into a developer wiki. I’ll verify the current MkDocs/Material config surface against official docs before writing the final document.

The official docs confirm the core mechanics we want: MkDocs uses Markdown files under a docs directory, `mkdocs.yml` config, local live preview, static build output, configurable validation, and Material adds browser-side search/navigation/tags without needing a separate service.

Here is a copy-pasteable adoption document for an agent. I verified the MkDocs/Material details against the current official docs before writing it: MkDocs uses Markdown source files plus `mkdocs.yml`, supports configurable `docs_dir`/`site_dir`, has a local live-preview server, strict validation, static build output, and Material adds search, navigation, and tags support. [![](https://www.google.com/s2/favicons?domain=https://squidfunk.github.io&sz=128)squidfunk.github.io+5![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org+5![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)mkdocs.org+5](https://www.mkdocs.org/user-guide/writing-your-docs/)

# Adopt MkDocs + Material for Repo-Local User-Facing Tool Documentation

Date: 2026-07-07

## Executive summary

Adopt **MkDocs + Material for MkDocs** in this repository to create a repo-local, browser-readable, wiki-like documentation layer for the tools this repository provides.

This documentation layer is **strictly user-facing**. Its only purpose is to explain how a user installs, configures, runs, operates, interprets, and troubleshoots the tools exposed by this repository.

This is **not** a developer documentation system. It is **not** for architecture notes, implementation explanations, ADRs, coding-agent handoffs, scratch notes, build-history notes, test strategy, internal design rationale, or explanations of code internals that are not visible to the user.

The final result should be:

````
repo/
  mkdocs.yml
  user-docs/
    index.md
    start-here.md
    tools/
      index.md
      <tool-name>/
        index.md
        quickstart.md
        usage.md
        commands.md
        examples.md
        troubleshooting.md
    workflows/
    reference/
    troubleshooting/
    glossary.md```

MkDocs is the documentation engine. Material for MkDocs is the browser-facing theme and UX layer. The docs are stored as normal Markdown files in the repository and viewed locally through `mkdocs serve`. MkDocs also builds a static site output directory when needed.

## Hard scope boundary

### In scope

Only document information a user needs in order to use the tools in this repository.

In-scope content includes:

| Content type | In scope examples |
| --- | --- |
| Tool overview | What the tool does from the user’s perspective |
| Installation/setup | How to install or prepare the tool for use |
| Quickstart | Minimal path from nothing to first successful use |
| Commands | Commands, subcommands, flags, options, arguments |
| Configuration | User-visible config files, environment variables, settings, defaults |
| Inputs | Accepted files, directories, parameters, formats, encodings |
| Outputs | Generated files, console output, logs visible to the user, exit codes |
| Workflows | Task-oriented usage guides |
| Examples | Copy-pasteable command examples and expected behavior |
| Troubleshooting | User-visible failures and recovery steps |
| Safety notes | Destructive operations, dry-run behavior, backups, overwrite behavior |
| Glossary | Terms the user must understand to operate the tools |

### Out of scope

Do **not** put the following in `user-docs/`:

<table><tbody><tr><td><span>Content type</span></td><td><span>Out of scope examples</span></td></tr><tr><td><span>Developer documentation</span></td><td><span>Code architecture, package layout, module responsibilities</span></td></tr><tr><td><span>Implementation notes</span></td><td><span>Why an algorithm was chosen, how internals are structured</span></td></tr><tr><td><span>ADRs</span></td><td><span>Architecture decision records or design rationale</span></td></tr><tr><td><span>Agent handoff material</span></td><td><span>LLM session notes, implementation plans, scratchpads</span></td></tr><tr><td><span>Internal TODOs</span></td><td><span>Developer TODOs, refactor plans, known code debts</span></td></tr><tr><td><span>Test documentation</span></td><td><span>Test strategy, fixtures, mocks, coverage rationale</span></td></tr><tr><td><span>Build internals</span></td><td><span>CI implementation details unless users must run them</span></td></tr><tr><td><span>API internals</span></td><td><span>Function/class docs unless they are part of a public user interface</span></td></tr><tr><td><span>Historical notes</span></td><td><span>Development history, migration notes irrelevant to users</span></td></tr><tr><td><span>Spec material</span></td><td><span>Requirements/specification details not directly needed for usage</span></td></tr></tbody></table>

The correct test is:

> Would a user need this information to successfully use the repository’s tools?

If no, keep it out of `user-docs/`.

## Adopted stack

Use:

````

MkDocs Material for MkDocs Markdown files mkdocs.yml local browser preview via mkdocs serve static output via mkdocs build```

MkDocs is appropriate because it is a static site generator for project documentation written in Markdown and configured through a single YAML file. Material for MkDocs provides a stronger user-facing reading experience, including navigation and browser-side search. MkDocs supports a local live preview server that rebuilds as files change, and the built site is static output rather than a separate hosted service or database-backed wiki.

Do not adopt a separate hosted wiki, CMS, database-backed documentation app, or external documentation portal for this task.

## Dependency policy

Documentation build tooling is a repository development dependency, not a runtime dependency of the tools.

If this is a Python repository using `uv`, add docs tooling as development tooling. Prefer a dedicated dependency group if the repository already uses dependency groups clearly; otherwise use the normal dev group.

Recommended simple command:

````
uv add --dev mkdocs mkdocs-material```

This keeps documentation tooling out of the project’s runtime dependencies. `uv` development dependencies are declared under `[dependency-groups]` and are local-only development dependencies rather than published/runtime package dependencies.

If the repository already uses a separate docs group, use:

````

uv add --group docs mkdocs mkdocs-material```

Do not add MkDocs or Material to `[project.dependencies]`.

## Required files

Create or update:

````
mkdocs.yml
user-docs/
.gitignore```

Do not place the user documentation under an existing developer-oriented `docs/` directory unless the repository already has a clearly established convention for `docs/user/`. Prefer `user-docs/` because the name makes the scope boundary explicit.

MkDocs allows the documentation source directory to be configured with `docs_dir`, so using `user-docs/` instead of the default `docs/` is intentional and supported.

## Required `.gitignore` entries

Add these if not already present:

````

.site/ site/```

Use `.site/user-docs/` as the configured MkDocs build output. Build output should not be committed. MkDocs documentation explicitly recommends ignoring generated site output when using source control.

## Required `mkdocs.yml`

Create `mkdocs.yml` at the repository root.

Use this as the starting point and replace placeholder values:

````
site_name: '<REPO NAME> User Guide'
site_description: 'User-facing usage documentation for the tools provided by this repository.'

docs_dir: user-docs
site_dir: .site/user-docs

strict: true
use_directory_urls: true

theme:
  name: material
  features:
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - search.highlight
    - search.suggest
    - content.code.copy

plugins:
  - search
  - tags:
      tags_allowed:
        - cli
        - tui
        - gui
        - configuration
        - installation
        - quickstart
        - workflow
        - reference
        - examples
        - troubleshooting
        - output
        - safety

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
  - pymdownx.details
  - pymdownx.superfences

validation:
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn

nav:
  - Home: index.md
  - Start here: start-here.md
  - Tools:
      - tools/index.md
  - Workflows:
      - workflows/index.md
  - Reference:
      - reference/index.md
  - Troubleshooting:
      - troubleshooting/index.md
  - Glossary: glossary.md```

Important notes:

1. If `plugins:` is set, explicitly include `search`; MkDocs’ default plugin list is replaced when the config declares plugins.
2. `strict: true` makes warnings fail the build. MkDocs also exposes this as `mkdocs build --strict`.
3. Material’s tags plugin can enforce a controlled tag list with `tags_allowed`; a page referencing a tag outside the list should fail the build.
4. Keep the initial feature set conservative. Do not add blog, social cards, custom CSS, custom JavaScript, publishing, analytics, or external hosting unless explicitly requested later.

## Required directory tree

Create this baseline tree:

````

user-docs/ index.md start-here.md tools/ index.md workflows/ index.md reference/ index.md troubleshooting/ index.md glossary.md```

For each user-facing tool in the repository, create:

````
user-docs/tools/<tool-name>/
  index.md
  quickstart.md
  usage.md
  commands.md
  examples.md
  troubleshooting.md```

Use lowercase kebab-case directory and file names.

Examples:

````

user-docs/tools/docmend/ user-docs/tools/flatdir/ user-docs/tools/archive-cleaner/```

Do not create directories for internal packages, modules, libraries, test helpers, scripts, or private utilities unless they are directly exposed to users as tools.

## Navigation policy

Use explicit `nav:` entries in `mkdocs.yml` for the initial adoption.

Every Markdown page under `user-docs/` should either appear in `nav:` or be intentionally excluded with a documented reason. Because this is user-facing documentation, orphan pages are usually a mistake.

After creating tool pages, update `nav:` like this:

````
nav:
  - Home: index.md
  - Start here: start-here.md
  - Tools:
      - tools/index.md
      - Tool Name:
          - Overview: tools/tool-name/index.md
          - Quickstart: tools/tool-name/quickstart.md
          - Usage: tools/tool-name/usage.md
          - Commands: tools/tool-name/commands.md
          - Examples: tools/tool-name/examples.md
          - Troubleshooting: tools/tool-name/troubleshooting.md
  - Workflows:
      - workflows/index.md
  - Reference:
      - reference/index.md
  - Troubleshooting:
      - troubleshooting/index.md
  - Glossary: glossary.md```

Do not let navigation become a dumping ground. If a page does not have a clear place in the navigation, reconsider whether it belongs in user-facing docs.

## Link policy

Use normal Markdown links to other Markdown files.

Preferred:

````

See [the command reference](commands.md). See [configuration reference](../../reference/configuration.md).```

Avoid links to generated `.html` files in source Markdown.

Avoid bare absolute local paths.

Do not use Obsidian-style wikilinks.

Good:

````
[Quickstart](quickstart.md)
[Examples](examples.md)
[Global troubleshooting](../../troubleshooting/index.md)```

Bad:

````

[[Quickstart]] <a href="quickstart.html">Quickstart</a> [Quickstart](/site/tools/tool-name/quickstart.html)```

MkDocs supports regular Markdown files in nested directories, and the file layout determines the generated page URLs.

## Page front matter policy

Use minimal YAML front matter on all user-facing pages.

Example:

````
---
title: Quickstart
description: First successful use of <tool-name>.
tags:
  - quickstart
  - cli
---

# Quickstart```

Allowed tags are the tags listed in `mkdocs.yml`.

Do not add status metadata, draft metadata, reviewer metadata, internal ownership metadata, implementation metadata, or agent workflow metadata to user-facing pages.

## Content model

Use a simplified Diátaxis-inspired structure, but keep it scoped to user-facing tool usage. Diátaxis separates documentation into tutorials, how-to guides, reference, and explanation, which is useful here because it prevents mixing task guidance, factual reference, and conceptual background into the same page.

For this repository, map that model as follows:

<table><tbody><tr><td><span>User need</span></td><td><span>Where it goes</span></td><td><span>Purpose</span></td></tr><tr><td><span>“Get me started”</span></td><td><code dir="ltr"><span>quickstart.md</span></code><span>, </span><code dir="ltr"><span>start-here.md</span></code></td><td><span>First successful use</span></td></tr><tr><td><span>“Help me do a task”</span></td><td><code dir="ltr"><span>usage.md</span></code><span>, </span><code dir="ltr"><span>workflows/</span></code></td><td><span>Goal-oriented steps</span></td></tr><tr><td><span>“Tell me exactly what options exist”</span></td><td><code dir="ltr"><span>commands.md</span></code><span>, </span><code dir="ltr"><span>reference/</span></code></td><td><span>Accurate factual reference</span></td></tr><tr><td><span>“Help me understand enough to use it correctly”</span></td><td><code dir="ltr"><span>index.md</span></code><span>, limited concept sections</span></td><td><span>Only user-visible concepts</span></td></tr><tr><td><span>“Help me recover from a problem”</span></td><td><code dir="ltr"><span>troubleshooting.md</span></code></td><td><span>Symptoms, causes, fixes</span></td></tr></tbody></table>

Do not create broad explanation pages about internals. Explanation is allowed only when it helps the user operate the tool correctly.

## Required page purposes

### `user-docs/index.md`

Purpose: landing page for the user documentation site.

Must include:

* What repository/toolset this documentation covers.
* A short list of available tools.
* A “start here” link.
* Links to tool pages.
* A statement that this site documents user-facing usage only.

Do not include:

* Project architecture.
* Developer setup.
* Contributor notes.
* Internal implementation summary.

### `user-docs/start-here.md`

Purpose: orient a new user.

Must include:

* Prerequisites the user needs.
* How to choose the right tool if the repo has multiple tools.
* The fastest path to first useful output.
* Links to tool quickstarts.

### `user-docs/tools/index.md`

Purpose: catalog the user-facing tools in the repo.

For each tool, include:

* Tool name.
* One-sentence user-facing purpose.
* Link to quickstart.
* Link to command reference.

Only include tools the user can actually run or interact with.

### `user-docs/tools/<tool-name>/index.md`

Purpose: overview page for one tool.

Must include:

* What the tool does.
* When to use it.
* When not to use it.
* Inputs.
* Outputs.
* Link to quickstart.
* Link to command reference.
* Link to troubleshooting.

Do not explain how the tool is implemented.

### `user-docs/tools/<tool-name>/quickstart.md`

Purpose: first successful use.

Must include:

* Minimal prerequisites.
* Minimal command or interaction.
* Expected output.
* One next link to deeper usage.

Keep this page short.

### `user-docs/tools/<tool-name>/usage.md`

Purpose: task-oriented usage guide.

Must include:

* Common usage patterns.
* Step-by-step workflows.
* Safe defaults.
* Notes about destructive or irreversible operations.
* Links to examples and command reference.

### `user-docs/tools/<tool-name>/commands.md`

Purpose: factual command reference.

Must include, where applicable:

* Invocation syntax.
* Subcommands.
* Positional arguments.
* Flags/options.
* Defaults.
* Accepted values.
* Exit codes.
* Environment variables.
* Config files.
* Output files.
* Examples for each common command.

Do not include internal parser implementation details.

### `user-docs/tools/<tool-name>/examples.md`

Purpose: copy-pasteable examples.

Each example should include:

* Goal.
* Command/input.
* Expected result.
* Notes about assumptions.

### `user-docs/tools/<tool-name>/troubleshooting.md`

Purpose: user-visible problem recovery.

Use this structure:

````

## Symptom

What the user sees.

## Likely cause

The most likely user-relevant cause.

## Fix

Steps to resolve it.

## Prevention

How to avoid it next time.```

Do not document stack traces for developers unless the user is likely to see them and needs a recovery action.

### `user-docs/workflows/index.md`

Purpose: cross-tool task guides.

Use this when a user task involves more than one tool or page.

Example topics:

- “Prepare a directory before running Tool A.”
- “Convert files, validate output, then archive results.”
- “Recover from a failed run.”

### `user-docs/reference/index.md`

Purpose: global reference material shared by multiple tools.

Examples:

- Common config file format.
- Common environment variables.
- Shared output conventions.
- Shared exit codes.
- Supported file types.

Do not place per-tool command reference here unless the same reference applies across tools.

### `user-docs/troubleshooting/index.md`

Purpose: global troubleshooting.

Examples:

- Permission errors.
- Missing dependencies.
- Path problems.
- Encoding problems.
- Output location confusion.

### `user-docs/glossary.md`

Purpose: define terms users must understand.

Keep definitions usage-oriented. Do not include developer jargon unless the user must know it.

## Tool discovery process for the agent

Before writing tool pages, identify all user-facing tools in the repository.

Use this process:

1. Inspect root files:
   - `README.md`
   - `pyproject.toml`
   - command entry points
   - scripts directories
   - existing usage docs
   - CLI help output
2. Identify executable/user-facing entry points.
3. Exclude internal helpers.
4. For each candidate, determine:
   - How a user invokes it.
   - Whether it has `--help`.
   - Whether it has subcommands.
   - What input it expects.
   - What output it produces.
   - What errors a user may need to recover from.
5. Create documentation only for confirmed user-facing tools.

Do not invent tools based on internal module names.

## Command reference source of truth

Prefer actual help output and current source behavior.

For each CLI-style tool, attempt:

````
<tool> --help
<tool> <subcommand> --help
python -m <module> --help
uv run <tool> --help
uv run python -m <module> --help```

Use whichever invocation matches the repository.

Command reference pages must match actual exposed behavior. Do not document flags, environment variables, defaults, or outputs that are not present in the current tool.

If behavior cannot be verified, do not publish it as fact in user docs. Put unresolved questions in the final implementation report, not inside `user-docs/`.

## User-facing wording rules

Write to the user, not to the maintainer.

Use:

````

Run this command. Set this option. The tool writes output to... Use this when...```

Avoid:

````
This module implements...
The parser internally...
The agent should...
We chose this design because...
Future work...
TODO...```

Use concrete examples over abstract explanation.

Use short pages with strong headings.

Prefer task headings:

````

## Convert a directory

## Preview changes before writing files

## Write output to a separate location```

Avoid implementation headings:

````
## Processing pipeline
## Internal architecture
## Parser behavior```

## Safety and destructive operation policy

If a tool can overwrite, delete, rename, move, encrypt, decrypt, archive, transform, or bulk-edit files, its docs must clearly document:

* Whether it modifies files in place.
* Whether it has a dry-run mode.
* Whether it creates backups.
* How output paths are chosen.
* What happens on name conflicts.
* How to verify results before committing changes.
* How to recover or rerun safely.

Use Material admonitions for user-visible safety notes:

````

!!! warning "This can overwrite files" This command writes changes in place. Run with `--dry-run` first.```

Do not overuse admonitions. Reserve them for information that changes user behavior.

## Example page template: tool overview

````
---
title: <Tool Name>
description: User guide for <tool-name>.
tags:
  - cli
---

# <Tool Name>

<One-sentence description of what the tool does for the user.>

## When to use it

Use `<tool-name>` when you need to...

## When not to use it

Do not use `<tool-name>` when...

## Inputs

- ...

## Outputs

- ...

## Typical workflow

1. ...
2. ...
3. ...

## Next

- [Quickstart](quickstart.md)
- [Usage guide](usage.md)
- [Command reference](commands.md)
- [Troubleshooting](troubleshooting.md)```

## Example page template: quickstart

````

---

title: Quickstart description: First successful use of <tool-name>. tags:

- quickstart
- cli

---

# Quickstart

This page shows the shortest path to a successful `<tool-name>` run.

## Prerequisites

- ...

## Run the tool

````bash
<command>```

## Expected result

The tool should...

## Next

See [usage](usage.md) for common workflows.

````

## Example page template: command reference

````markdown
---
title: Command reference
description: Commands and options for <tool-name>.
tags:
  - reference
  - cli
---

# Command reference

## Invocation

````bash
<tool-name> [OPTIONS] <ARGUMENTS>```

## Commands

<table><tbody><tr><td><span>Command</span></td><td><span>Purpose</span></td></tr><tr><td><code dir="ltr"><span>&lt;command&gt;</span></code></td><td><span>...</span></td></tr></tbody></table>

## Arguments

<table><tbody><tr><td><span>Argument</span></td><td><span>Required</span></td><td><span>Description</span></td></tr><tr><td><code dir="ltr"><span>&lt;argument&gt;</span></code></td><td><span>Yes</span></td><td><span>...</span></td></tr></tbody></table>

## Options

<table><tbody><tr><td><span>Option</span></td><td><span>Default</span></td><td><span>Description</span></td></tr><tr><td><code dir="ltr"><span>--example</span></code></td><td><code dir="ltr"><span>false</span></code></td><td><span>...</span></td></tr></tbody></table>

## Exit codes

<table><tbody><tr><td><span>Code</span></td><td><span>Meaning</span></td></tr><tr><td><code dir="ltr"><span>0</span></code></td><td><span>Success</span></td></tr><tr><td><code dir="ltr"><span>1</span></code></td><td><span>User-correctable error</span></td></tr></tbody></table>

## Environment variables

<table><tbody><tr><td><span>Variable</span></td><td><span>Description</span></td></tr><tr><td><code dir="ltr"><span>&lt;NAME&gt;</span></code></td><td><span>...</span></td></tr></tbody></table>

## Examples
````
````

<example command>```

````

## Example page template: troubleshooting

```markdown
---
title: Troubleshooting
description: Common <tool-name> problems and fixes.
tags:
  - troubleshooting
---

# Troubleshooting

## `<error message or symptom>`

### Symptom

The user sees...

### Likely cause

This usually means...

### Fix

1. ...
2. ...
3. ...

### Prevention

...```

## Cross-reference policy

Cross-link aggressively, but keep links useful.

Good cross-links:

* Quickstart to command reference.
* Command reference to examples.
* Troubleshooting item to relevant configuration reference.
* Tool overview to related workflows.
* Workflow to each tool it uses.

Do not create decorative links.

Do not link every mention of a term. Link the first useful occurrence.

## Screenshots and diagrams

Do not add screenshots or diagrams by default.

Add them only if they help the user operate the tool.

Allowed:

* Screenshot of a GUI/TUI state the user must recognize.
* Diagram of user-visible input/output flow.
* Example output image if the tool produces visual output.

Not allowed:

* Architecture diagrams.
* Internal data-flow diagrams.
* Class/module diagrams.
* Developer-only pipeline diagrams.

If images are added, place them under:

````

user-docs/assets/```

Reference them with relative Markdown links.

## README integration

Do not move the main project README into `user-docs/`.

Add a small section to `README.md` pointing to the user docs:

````
## User documentation

User-facing documentation for the tools in this repository lives in [`user-docs/`](user-docs/).

To view it locally as a browser site:

```bash
uv run mkdocs serve```

````

Keep the README short. The full usage documentation belongs in `user-docs/`.

## Local preview commands

The primary local viewing command is:

````bash
uv run mkdocs serve```

Then open the local MkDocs server in a browser.

If using a dedicated docs dependency group and the dependencies are not installed by default, use the repository’s established `uv` group workflow.

Build with:

````

uv run mkdocs build --strict```

The build must pass before the adoption is considered complete.

MkDocs’ live preview server automatically rebuilds the site when documentation files change. Material’s documentation also confirms `mkdocs serve --livereload` as the live preview workflow.

## Build validation

The docs build must fail on:

- Broken internal links.
- Broken heading anchors.
- Unrecognized relative links.
- Pages omitted from navigation.
- Invalid tags.
- MkDocs warnings.

Use:

````
uv run mkdocs build --strict```

Do not leave warnings unresolved.

## Adoption workflow for the agent

Complete the adoption in this order.

### Phase 1: Inspect

1. Inspect the repository.
2. Identify user-facing tools.
3. Identify existing user-facing usage content.
4. Identify existing developer/internal docs that must not be moved into `user-docs/`.
5. Identify actual command help output and entry points.

### Phase 2: Install/configure

1. Add MkDocs and Material for MkDocs as dev/docs dependencies.
2. Create `mkdocs.yml`.
3. Add `.site/` and `site/` to `.gitignore`.
4. Create the baseline `user-docs/` tree.
5. Add minimal index pages.

### Phase 3: Write tool docs

For each user-facing tool:

1. Create the tool page directory.
2. Create overview, quickstart, usage, commands, examples, and troubleshooting pages.
3. Populate the command reference from actual help output/source behavior.
4. Add realistic examples.
5. Add troubleshooting only for user-visible problems.
6. Add cross-links.

### Phase 4: Wire navigation

1. Add every page to `mkdocs.yml` navigation.
2. Keep navigation user-task-oriented.
3. Make sure tool names are clear and human-readable.

### Phase 5: Validate

1. Run local build:

    ```
    uv run mkdocs build --strict```

2. Fix all warnings/errors.
3. Run local preview:

    ```
    uv run mkdocs serve```

4. Confirm the browser navigation, search, tags, and cross-links work.

### Phase 6: Report

Produce a concise implementation report outside `user-docs/` or in the final agent response.

The report should include:

* Files created.
* Files modified.
* Tools documented.
* Commands used to validate.
* Any user-facing behavior that could not be verified.
* Any recommended follow-up questions.

Do not place the implementation report inside `user-docs/`.

## Quality checklist

The adoption is complete only when all of these are true:

* `mkdocs.yml` exists at repository root.

* `docs_dir` is set to `user-docs`.

* `site_dir` is set to `.site/user-docs`.

* MkDocs and Material are development/docs dependencies, not runtime dependencies.

* `.site/` and `site/` are ignored.

* `user-docs/index.md` explains that the docs are user-facing usage docs.

* Every documented tool is actually user-facing.

* Every user-facing tool has overview, quickstart, usage, commands, examples, and troubleshooting pages.

* Command references are based on actual current behavior.

* Internal architecture and implementation notes are excluded.

* ADRs, specs, handoff notes, scratch notes, and TODOs are excluded.

* Navigation includes all pages.

* Cross-links use normal Markdown links to `.md` files.

* Tags are from the allowed tag list.

* `uv run mkdocs build --strict` succeeds.

* `uv run mkdocs serve` works for local browser viewing.


## Final instruction to the agent

Do not treat this as a general documentation cleanup.

Do not create a developer wiki.

Do not move internal notes into the user docs.

Do not explain how the tools are built unless that information is directly necessary for a user to operate them.

The goal is a clean, repo-local, browser-readable, Markdown-authored **user guide** for the tools this repository provides.

* * *

**You:**

Does this system have the capability to ingest user notes directly within the user interface for example if I’m working with a tool and following the documentation and then I noticed a bug in the tool or a behavior that I want changed is it possible to make a wiki entry or or a note or some other sort of communication mechanism within the browser interface to then get feedback for implementation when I have my coding agent review it later

* * *

**ChatGPT:**

The important distinction: MkDocs/Material is a static documentation viewer, not a writable wiki. I’ll verify the supported interaction hooks, then give you a repo-local pattern that preserves the “user docs only” boundary while still capturing feedback for agents.

No — **MkDocs + Material does not natively ingest notes, bug reports, or change requests from the browser UI into the repo.** It is fundamentally a **static documentation site generator**: Markdown files in the repo become a browser-readable static site, and the local dev server previews/reloads that site as files change. It is excellent for reading and navigating docs, but it is not a writable wiki or issue tracker. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)MkDocs](https://www.mkdocs.org/)

The closest built-in/official-adjacent features are useful but not what you described:

| Mechanism | What it does | Fit for your use case |
| --- | --- | --- |
| `repo_url` / `edit_uri` | Adds links from docs pages back to the source repository/page. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)MkDocs](https://www.mkdocs.org/user-guide/configuration/) | Good for “edit this page,” not for capturing tool feedback while using docs. |
| Material feedback widget | “Was this page helpful?” style page feedback, usually tied to analytics or a custom integration. [![](https://www.google.com/s2/favicons?domain=https://squidfunk.github.io&sz=128)GitHub Pages](https://squidfunk.github.io/mkdocs-material/setup/setting-up-site-analytics/) | Good for docs quality signals, not structured bug/change notes. |
| Giscus/comments | Adds a third-party comment system using GitHub Discussions as backend. [![](https://www.google.com/s2/favicons?domain=https://squidfunk.github.io&sz=128)GitHub Pages](https://squidfunk.github.io/mkdocs-material/setup/adding-a-comment-system/) | Useful, but no longer purely repo-local/static; creates external discussion state. |
| GitHub issue forms | Structured bug/feature request forms in GitHub issues. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms?utm_source=chatgpt.com) | Good if you accept GitHub Issues as the feedback sink. |

## The right design

Keep `user-docs/` read-only and user-facing. Add a **separate feedback intake layer** outside `user-docs/`.

Recommended repo shape:

````

repo/ mkdocs.yml user-docs/ # published user-facing usage docs only feedback/ README.md inbox/ .gitkeep templates/ bug.md behavior-change.md docs-issue.md tools/ docs-feedback/ # optional helper CLI/server

````

The key rule: **feedback notes are not user documentation.** They are implementation intake for you and coding agents, so they should not live under `user-docs/`.

## Best option for your workflow

Use a small repo-local feedback capture tool that writes Markdown files into `feedback/inbox/`.

For example:

```Bash
uv run docs-feedback new
````

It would prompt for:

```
Type: bug | behavior-change | docs-issue | question
Tool:
Docs page:
Observed behavior:
Expected behavior:
Steps to reproduce:
Notes:
```

Then write:

```
feedback/inbox/2026-07-07-tool-name-bug-short-title.md
```

That gives your later coding agent a clean intake queue without contaminating the user docs.

## If you want capture directly from the browser

That is possible, but it requires a **custom local companion service**, not just MkDocs.

Pattern:

```
Browser docs page
  ↓ POST to localhost
127.0.0.1:<port>/feedback
  ↓ writes markdown file
repo/feedback/inbox/<timestamp>-<slug>.md
```

Implementation stack could be:

```
FastAPI local-only service
127.0.0.1 binding only
simple HTML/JS form injected into MkDocs Material
Markdown output files under feedback/inbox/
```

This would let you click something like **“Capture feedback for this page”** while reading the docs, fill in a form, and have it write a structured Markdown note into the repo for agent review.

But I would treat that as **phase 2**, because it adds moving parts: a local server, browser JavaScript, security boundaries, file-writing permissions, and another process to run alongside `mkdocs serve`.

## Practical recommendation

Start with this:

```
feedback/
  README.md
  inbox/
  templates/
    bug.md
    behavior-change.md
    docs-issue.md
```

Add a simple command later:

```Bash
uv run docs-feedback new --page tools/foo/commands.md --type bug
```

Then optionally add a local browser button that calls it through a localhost service.

That gives you the workflow you want without pretending MkDocs is a writable wiki. The docs stay clean and user-facing; feedback becomes structured repo-local implementation input for your coding agent.

---

**You:**

Would it be possible to just add a hard link, for example, to every major section in a MK docs page that just linked to a GitHub issues form on github.com with the title pre-populated and then all the users has to do is fill out the issue request and send it

---

**ChatGPT:**

Yes. That is probably the cleanest low-friction solution.

Not a filesystem hard link, but a normal Markdown hyperlink in the MkDocs page that opens GitHub’s **new issue** page with the correct issue form, title, and some fields prefilled.

GitHub explicitly supports opening new issues with URL query parameters such as `title`, `body`, `labels`, `assignees`, `projects`, and `template`; it also supports query-parameter prefills for custom text fields in issue forms. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue) GitHub issue forms are YAML files stored under `.github/ISSUE_TEMPLATE/`, and they support structured fields such as text inputs, textareas, dropdowns, checkboxes, and uploads. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)

## Recommended pattern

Keep `user-docs/` read-only, but add small links like this under major sections:

```Markdown
[Report a problem or request a change for this section](https://github.com/OWNER/REPO/issues/new?template=tool-feedback.yml&title=%5Btool-name%5D%20Feedback%3A%20Commands%20-%20Dry%20run&doc-page=user-docs%2Ftools%2Ftool-name%2Fcommands.md&section=Dry%20run)
```

Rendered in the docs, the user clicks the link, GitHub opens the issue form, and the user fills in the remaining fields.

## Better issue form shape

Create:

```
.github/
  ISSUE_TEMPLATE/
    tool-feedback.yml
```

Example:

```YAML
name: Tool feedback
description: Report a bug, confusing behavior, or requested change while using a documented tool.
title: "[Tool feedback]: "
labels:
  - triage
  - user-feedback
type: task

body:
  - type: markdown
    attributes:
      value: |
        Use this form for feedback about using a tool in this repository.

  - type: input
    id: tool
    attributes:
      label: Tool
      description: Which tool does this concern?
      placeholder: example-tool
    validations:
      required: true

  - type: input
    id: doc-page
    attributes:
      label: Documentation page
      description: Which documentation page led you here?
      placeholder: user-docs/tools/example-tool/commands.md
    validations:
      required: false

  - type: input
    id: section
    attributes:
      label: Documentation section
      description: Which section were you reading?
      placeholder: Dry run
    validations:
      required: false

  - type: dropdown
    id: feedback-kind
    attributes:
      label: Feedback type
      options:
        - Bug
        - Behavior change request
        - Documentation issue
        - Question
    validations:
      required: true

  - type: textarea
    id: observed
    attributes:
      label: What happened?
      description: Describe the behavior, bug, confusing output, or desired change.
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: What did you expect instead?
    validations:
      required: false

  - type: textarea
    id: steps
    attributes:
      label: Steps, command, or context
      description: Paste the command, inputs, relevant output, or steps to reproduce.
      render: shell
    validations:
      required: false
```

Then your MkDocs section link could be:

```Markdown
[Give feedback on this section](https://github.com/OWNER/REPO/issues/new?template=tool-feedback.yml&title=%5Bexample-tool%5D%20Feedback%3A%20Dry%20run&tool=example-tool&doc-page=user-docs%2Ftools%2Fexample-tool%2Fcommands.md&section=Dry%20run)
```

GitHub’s form schema uses each field’s `id` as the canonical identifier for URL query-parameter prefills, so fields like `tool`, `doc-page`, and `section` are reasonable prefill targets. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema)

## Why this is a good fit

This preserves the boundary cleanly:

```
user-docs/                    # user-facing usage docs only
.github/ISSUE_TEMPLATE/       # structured feedback intake
GitHub Issues                 # implementation queue for you/agents
```

It avoids custom local servers, browser-side write access, JavaScript injection, or turning MkDocs into a fake wiki. It also gives your coding agent a natural review target later: open issues labeled `user-feedback`, `tool-feedback`, `bug`, or `behavior-change`.

## Caveats

For a private repo, the person clicking the link must have GitHub access to create issues. Labels, assignees, milestones, and project-prefill behavior can depend on repository permissions; form-level defaults in the YAML are safer than relying entirely on URL labels. GitHub also returns errors for invalid query URLs or URLs that exceed server length limits, so keep prefilled bodies short. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue)

My recommendation: add these links at the **page level and major H2 sections**, not every small subsection. Too many links will clutter the docs. Use wording like:

```Markdown
[Report a problem or request a change for this section](...)
```

That gives you the feedback loop you wanted without breaking the “user docs are only for using the tools” rule.

---

**You:**

I’d like to use these down to say the H3 level. Can I just have a very small square icon as the link that sits in line with the heading off to the right side somewhere that’ll be the entire link and it won’t be a thick of an entire line or much space that way, we can still have fairly accurate position information from where the document I clicked that get fed through the request.

---

**ChatGPT:**

Yes. That is feasible, and it is a good fit for H2/H3-level feedback.

I would **not manually hard-code a GitHub URL beside every heading** unless the docs are tiny. Better pattern: add one small JavaScript file to MkDocs/Material that automatically appends a tiny feedback icon to every `h2` and `h3`, then builds the GitHub issue-form URL from the current page URL, heading text, and heading anchor.

MkDocs supports `extra_css` and `extra_javascript` for small theme tweaks, and Material explicitly supports this customization path. MkDocs also supports normal Markdown/HTML authoring and Material supports customization through added assets. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)MkDocs+1](https://www.mkdocs.org/user-guide/customizing-your-theme/?utm_source=chatgpt.com) GitHub issue forms can be prefilled by URL query parameters, including custom fields whose IDs match the form field IDs. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs+1](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema?utm_source=chatgpt.com)

## Recommended implementation

Add this:

```
user-docs/
  assets/
    feedback-links.css
    feedback-links.js
```

Then in `mkdocs.yml`:

```YAML
extra_css:
  - assets/feedback-links.css

extra_javascript:
  - assets/feedback-links.js
```

## Example issue form fields

Your `.github/ISSUE_TEMPLATE/tool-feedback.yml` should include stable IDs like these:

```YAML
name: Tool feedback
description: Report a bug, confusing behavior, or requested behavior change while using the documented tools.
title: "[Tool feedback]: "
labels:
  - user-feedback
  - triage

body:
  - type: input
    id: doc_page
    attributes:
      label: Documentation page
    validations:
      required: false

  - type: input
    id: doc_section
    attributes:
      label: Documentation section
    validations:
      required: false

  - type: input
    id: doc_anchor
    attributes:
      label: Documentation anchor
    validations:
      required: false

  - type: input
    id: doc_url
    attributes:
      label: Documentation URL
    validations:
      required: false

  - type: dropdown
    id: feedback_type
    attributes:
      label: Feedback type
      options:
        - Bug
        - Behavior change request
        - Documentation issue
        - Question
    validations:
      required: true

  - type: textarea
    id: observed
    attributes:
      label: What happened?
      description: Describe the behavior, bug, confusing output, or desired change.
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: What did you expect instead?
    validations:
      required: false

  - type: textarea
    id: steps
    attributes:
      label: Steps, command, or context
      description: Paste the command, input, output, or steps to reproduce.
      render: shell
    validations:
      required: false
```

GitHub requires issue form field IDs to be unique, and those IDs are the canonical identifiers used for URL-prefilled custom form fields. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema?utm_source=chatgpt.com)

## Auto-add icon beside H2/H3 headings

`user-docs/assets/feedback-links.js`:

```JavaScript
(function () {
  const owner = "OWNER";
  const repo = "REPO";
  const template = "tool-feedback.yml";

  function buildIssueUrl(heading) {
    const sectionTitle = heading.textContent.replace("□", "").trim();
    const anchor = heading.id || "";
    const pagePath = window.location.pathname;
    const fullUrl = anchor
      ? `${window.location.origin}${window.location.pathname}#${anchor}`
      : window.location.href;

    const params = new URLSearchParams({
      template,
      title: `[Tool feedback]: ${sectionTitle}`,
      doc_page: pagePath,
      doc_section: sectionTitle,
      doc_anchor: anchor,
      doc_url: fullUrl,
    });

    return `https://github.com/${owner}/${repo}/issues/new?${params.toString()}`;
  }

  function addFeedbackLinks() {
    document.querySelectorAll(".md-typeset h2[id], .md-typeset h3[id]").forEach((heading) => {
      if (heading.querySelector(".section-feedback-link")) {
        return;
      }

      const link = document.createElement("a");
      link.className = "section-feedback-link";
      link.href = buildIssueUrl(heading);
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.title = "Report a problem or request a change for this section";
      link.setAttribute("aria-label", `Report feedback for section: ${heading.textContent.trim()}`);
      link.textContent = "□";

      heading.appendChild(link);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addFeedbackLinks);
  } else {
    addFeedbackLinks();
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(addFeedbackLinks);
  }
})();
```

Material uses instant navigation in some configurations, so the `document$.subscribe(...)` part matters if you enable that feature later. It makes the links reappear after Material swaps page content without a full browser reload.

## CSS for a tiny right-side icon

`user-docs/assets/feedback-links.css`:

```CSS
.md-typeset h2,
.md-typeset h3 {
  position: relative;
}

.md-typeset .section-feedback-link {
  float: right;
  margin-left: 0.5rem;
  font-size: 0.7em;
  line-height: 1;
  opacity: 0.35;
  text-decoration: none;
}

.md-typeset .section-feedback-link:hover,
.md-typeset .section-feedback-link:focus {
  opacity: 1;
  text-decoration: none;
}
```

That gives you a tiny square link beside each H2/H3 without consuming a whole line.

## Why auto-generation is better than manual links

Manual per-heading links work, but they are brittle. If you rename a heading, move a file, or change a section anchor, your prefilled metadata can go stale. The small JavaScript approach derives the metadata from the rendered page, so it stays accurate enough for agent review:

```
doc_page     = current docs page path
doc_section  = visible heading text
doc_anchor   = generated heading anchor
doc_url      = full browser URL with #anchor
```

That gives your later coding agent a precise source location without turning the docs into a writable wiki.

## One caveat

This will open GitHub. It will not work fully offline, and private repos require the user to be authenticated and authorized to create issues. GitHub also documents that invalid query URLs can fail, and overly long URLs can hit server length limits, so keep prefilled fields short. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs](https://docs.github.com/enterprise-cloud%40latest/issues/tracking-your-work-with-issues/creating-an-issue?utm_source=chatgpt.com)

---

**You:**

I don’t want integrating this system to cause pollution and visual clutter within my repo. Can I have everything that this system requires the located in root/docs/usage. Same path for every repo I keep consistent structure between them.

---

**ChatGPT:**

Yes — **use `root/docs/usage/` as the standard location.** That is a cleaner structure than scattering `mkdocs.yml`, assets, feedback JS/CSS, and Markdown pages across the repo root.

The one real exception is **GitHub Issue Forms**: GitHub requires issue form YAML files under `.github/ISSUE_TEMPLATE/`, so that part cannot live under `docs/usage/` if you want GitHub’s native issue-form UI. Everything MkDocs-specific can live under `docs/usage/`. GitHub’s docs state that issue forms must be added to `.github/ISSUE_TEMPLATE`, while MkDocs supports specifying a non-default config path with `-f` / `--config-file`. [![](https://www.google.com/s2/favicons?domain=https://docs.github.com&sz=128)GitHub Docs+1](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)

Recommended structure:

```
repo/
  docs/
    usage/
      mkdocs.yml
      content/
        index.md
        start-here.md
        tools/
          index.md
          <tool-name>/
            index.md
            quickstart.md
            usage.md
            commands.md
            examples.md
            troubleshooting.md
        workflows/
          index.md
        reference/
          index.md
        troubleshooting/
          index.md
        glossary.md
        assets/
          feedback-links.css
          feedback-links.js
      overrides/              # optional; only if deeper theme customization is needed
      .site/                  # generated output; gitignored
```

Use this `mkdocs.yml` location:

```
docs/usage/mkdocs.yml
```

Then run:

```Bash
uv run mkdocs serve -f docs/usage/mkdocs.yml
uv run mkdocs build --strict -f docs/usage/mkdocs.yml
```

That works because MkDocs allows the config file path to be specified explicitly, and path-based options such as `docs_dir` and `site_dir` are resolved relative to the config file location. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)MkDocs+1](https://www.mkdocs.org/user-guide/configuration/)

Inside `docs/usage/mkdocs.yml`, use:

```YAML
site_name: '<REPO NAME> User Guide'
site_description: 'User-facing usage documentation for the tools provided by this repository.'

docs_dir: content
site_dir: .site

strict: true
use_directory_urls: true

theme:
  name: material
  features:
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - search.highlight
    - search.suggest
    - content.code.copy

plugins:
  - search
  - tags:
      tags_allowed:
        - cli
        - tui
        - gui
        - configuration
        - installation
        - quickstart
        - workflow
        - reference
        - examples
        - troubleshooting
        - output
        - safety

extra_css:
  - assets/feedback-links.css

extra_javascript:
  - assets/feedback-links.js

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
  - pymdownx.details
  - pymdownx.superfences

validation:
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn

nav:
  - Home: index.md
  - Start here: start-here.md
  - Tools:
      - tools/index.md
  - Workflows:
      - workflows/index.md
  - Reference:
      - reference/index.md
  - Troubleshooting:
      - troubleshooting/index.md
  - Glossary: glossary.md
```

This keeps the root visually clean while staying idiomatic. MkDocs documents `docs_dir` as the source Markdown directory and `site_dir` as the generated output directory, both configurable; it also documents that CSS/JS customizations can live inside the documentation directory and be referenced through `extra_css` / `extra_javascript`. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)MkDocs+1](https://www.mkdocs.org/user-guide/configuration/)

Root-level impact becomes minimal:

```
repo/
  .github/
    ISSUE_TEMPLATE/
      tool-feedback.yml       # only needed for GitHub issue forms
  docs/
    usage/
      ...                     # entire usage-docs system
  pyproject.toml              # docs dependencies only, if Python/uv repo
  uv.lock                     # updated dependency lockfile
  .gitignore                  # ignore docs/usage/.site/
```

Add this to `.gitignore`:

```gitignore
docs/usage/.site/
```

I would revise the standard from `user-docs/` to **`docs/usage/content/`**. The top-level `docs/usage/` directory becomes the complete usage-docs subsystem, and `content/` is the actual MkDocs source tree. That avoids root clutter and avoids mixing generated output with source Markdown.

---

**You:**

Update the adoption document with these new changes and require requirements. The adoption document should also give generic advice or guidelines to the agent that consumes it to make sure that it properly up-to-date its own instructions to reinforce the scope and intended audience of the system, and to ensure that the agent has the awareness of the correct tools and process for the agent to update and work with the content when updating and making changes, etc. My different repository tend to use different agent handoff systems and other LLM custom interfaces so right this is guidance in a way that the receiving agent will understand that it needs to implement it into its own systems using its own judgment based on repo conventions.

---

**ChatGPT:**

I’ll update the adoption spec to standardize everything under `docs/usage/`, keep GitHub issue forms as the only required external path, and add agent-instruction integration guidance that adapts to each repo’s existing handoff system.

Below is the updated adoption document with the new `docs/usage/` standard, H2/H3 feedback-link mechanism, GitHub issue-form exception, and agent-instruction integration guidance.

# Adopt Repo-Local MkDocs + Material Usage Documentation

Date: 2026-07-07

## Executive summary

Adopt **MkDocs + Material for MkDocs** as the standard repo-local system for **user-facing usage documentation**.

This system is for documenting how users operate the tools provided by the repository. It is not a developer wiki, design-history store, coding-agent scratchpad, architecture notebook, ADR collection, implementation journal, or project handoff area.

All MkDocs usage-documentation files must live under:

````
docs/usage/```

This location is the standard path for every repository using this system.

The only required exception is GitHub issue forms. GitHub issue forms must live under:

````

.github/ISSUE_TEMPLATE/```

That path is required by GitHub’s native issue-form system, not by MkDocs.

## Purpose

The purpose of this adoption is to create a clean, browser-readable, Markdown-authored documentation layer that tells users how to use the tools this repository exposes.

The documentation should answer questions like:

- What tools are available?
- Which tool should I use?
- How do I install or run the tool?
- What commands, flags, options, arguments, and configuration does the tool expose?
- What inputs does the tool accept?
- What outputs does the tool produce?
- What are safe usage patterns?
- What should I do when something fails?
- How do I report a bug or request a behavior change from the exact section I was reading?

The documentation must not explain internal implementation details unless the information is directly necessary for correct user operation.

## Adopted stack

Use:

````
MkDocs
Material for MkDocs
Markdown source files
repo-local configuration
local browser preview
static site output
GitHub issue forms for feedback intake```

MkDocs is a static site generator for project documentation written in Markdown and configured through a YAML file. It supports configurable documentation source/output directories and a local development server. MkDocs also supports `-f` / `--config-file` for using a non-root config file, which is required for this standard layout.

Material for MkDocs is the browser-facing theme and UX layer. It supports adding small CSS and JavaScript customizations from the docs directory, which this standard uses for unobtrusive H2/H3 feedback links.

GitHub issue forms are used as the structured feedback intake mechanism. GitHub requires issue-form YAML files under `/.github/ISSUE_TEMPLATE/`.

## Hard scope boundary

### In scope

Only document information a user needs to operate the repository’s user-facing tools.

In-scope content includes:

| Content type | In-scope examples |
| --- | --- |
| Tool overview | What the tool does from the user’s perspective |
| Installation/setup | How to install, prepare, or invoke the tool |
| Quickstart | Shortest path to first successful use |
| Commands | Commands, subcommands, flags, options, arguments |
| Configuration | User-visible config files, environment variables, defaults |
| Inputs | Accepted files, directories, parameters, formats, encodings |
| Outputs | Generated files, console output, visible logs, exit codes |
| Workflows | Task-oriented usage guides |
| Examples | Copy-pasteable commands and expected results |
| Troubleshooting | User-visible failures and recovery steps |
| Safety notes | Destructive actions, dry-run behavior, overwrite behavior |
| Feedback links | H2/H3 links to GitHub issue forms |
| Glossary | Terms users must understand to operate the tools |

### Out of scope

Do not place the following under `docs/usage/`:

<table><tbody><tr><td><span>Content type</span></td><td><span>Out-of-scope examples</span></td></tr><tr><td><span>Developer documentation</span></td><td><span>Code architecture, package layout, module responsibilities</span></td></tr><tr><td><span>Implementation notes</span></td><td><span>Algorithms, internal design, private data flow</span></td></tr><tr><td><span>ADRs</span></td><td><span>Architecture decision records or design rationale</span></td></tr><tr><td><span>Agent handoff material</span></td><td><span>LLM session notes, coding-agent plans, scratchpads</span></td></tr><tr><td><span>Internal TODOs</span></td><td><span>Refactor plans, future implementation tasks</span></td></tr><tr><td><span>Test documentation</span></td><td><span>Test strategy, fixtures, mocks, coverage rationale</span></td></tr><tr><td><span>Build internals</span></td><td><span>CI implementation details unless users must run them</span></td></tr><tr><td><span>API internals</span></td><td><span>Function/class docs unless they are public user interfaces</span></td></tr><tr><td><span>Historical notes</span></td><td><span>Development history not needed for usage</span></td></tr><tr><td><span>Specs</span></td><td><span>Requirements/spec content not directly needed by users</span></td></tr></tbody></table>

Use this test:

> Would a user need this information to successfully use the tools this repository provides?

If the answer is no, keep it out of `docs/usage/`.

## Required repository layout

Create this structure:

````

repo/ docs/ usage/ mkdocs.yml content/ index.md start-here.md tools/ index.md workflows/ index.md reference/ index.md troubleshooting/ index.md glossary.md assets/ feedback-links.css feedback-links.js .site/ .github/ ISSUE_TEMPLATE/ tool-feedback.yml```

The generated site output goes under:

````
docs/usage/.site/```

That directory must be ignored by Git.

## Required `.gitignore` entry

Add:

````

docs/usage/.site/```

Do not commit generated MkDocs output.

## Required MkDocs config

Create:

````
docs/usage/mkdocs.yml```

Use this as the baseline:

````

site_name: '<REPO NAME> User Guide' site_description: 'User-facing usage documentation for the tools provided by this repository.'

docs_dir: content site_dir: .site

strict: true use_directory_urls: true

theme: name: material features: - navigation.sections - navigation.indexes - navigation.top - search.highlight - search.suggest - content.code.copy

plugins:

- search
- tags: tags_allowed: - cli - tui - gui - configuration - installation - quickstart - workflow - reference - examples - troubleshooting - output - safety

extra_css:

- assets/feedback-links.css

extra_javascript:

- assets/feedback-links.js

markdown_extensions:

- admonition
- attr_list
- md_in_html
- tables
- toc: permalink: true
- pymdownx.details
- pymdownx.superfences

validation: omitted_files: warn absolute_links: warn unrecognized_links: warn anchors: warn

nav:

- Home: index.md
- Start here: start-here.md
- Tools:
  - tools/index.md
- Workflows:
  - workflows/index.md
- Reference:
  - reference/index.md
- Troubleshooting:
  - troubleshooting/index.md
- Glossary: glossary.md```

Paths in `nav` are relative to `docs_dir`, so with `docs_dir: content`, `index.md` means `docs/usage/content/index.md`. MkDocs documents that navigation paths are relative to `docs_dir`.

If `plugins:` is declared, explicitly keep `search` in the plugin list. Do not assume MkDocs’ default plugin list still applies after declaring plugins.

## Required commands

From the repository root, preview the docs with:

````
uv run mkdocs serve -f docs/usage/mkdocs.yml```

Build and validate with:

````

uv run mkdocs build --strict -f docs/usage/mkdocs.yml```

MkDocs supports `--strict` to abort on warnings and `-f` / `--config-file` to use a specific config file.

## Dependency policy

MkDocs and Material for MkDocs are documentation tooling dependencies. They are not runtime dependencies of the repository’s tools.

If this is a Python repository using `uv`, prefer:

````
uv add --dev mkdocs mkdocs-material```

If the repository already uses a dedicated docs dependency group, use the repo convention instead, for example:

````

uv add --group docs mkdocs mkdocs-material```

Do not add MkDocs or Material for MkDocs to runtime dependencies unless the repository has an unusual reason that has been explicitly documented.

## Required content tree

Create:

````
docs/usage/content/
  index.md
  start-here.md
  tools/
    index.md
  workflows/
    index.md
  reference/
    index.md
  troubleshooting/
    index.md
  glossary.md
  assets/
    feedback-links.css
    feedback-links.js```

For each user-facing tool, create:

````

docs/usage/content/tools/<tool-name>/ index.md quickstart.md usage.md commands.md examples.md troubleshooting.md```

Use lowercase kebab-case file and directory names.

Do not create documentation directories for internal packages, modules, test helpers, private scripts, or implementation components unless they are directly exposed as user-facing tools.

## Required page purposes

### `docs/usage/content/index.md`

Purpose: user documentation landing page.

Must include:

- What repository/toolset this usage guide covers.
- A short statement that this documentation is user-facing usage documentation only.
- List of available user-facing tools.
- Link to `start-here.md`.
- Links to tool pages.

Must not include:

- Architecture.
- Developer setup.
- Contributor workflow.
- Agent instructions.
- Implementation summary.

### `docs/usage/content/start-here.md`

Purpose: orient a new user.

Must include:

- Prerequisites.
- How to choose the right tool if the repo exposes multiple tools.
- Fastest path to first useful result.
- Links to tool quickstarts.

### `docs/usage/content/tools/index.md`

Purpose: catalog user-facing tools.

For each tool, include:

- Tool name.
- One-sentence purpose.
- Link to quickstart.
- Link to command reference.

Only include tools that users can actually run or interact with.

### `docs/usage/content/tools/<tool-name>/index.md`

Purpose: overview for one tool.

Must include:

- What the tool does.
- When to use it.
- When not to use it.
- Inputs.
- Outputs.
- Link to quickstart.
- Link to command reference.
- Link to troubleshooting.

Do not explain implementation internals.

### `docs/usage/content/tools/<tool-name>/quickstart.md`

Purpose: shortest path to first successful use.

Must include:

- Minimal prerequisites.
- Minimal command or interaction.
- Expected output.
- Link to deeper usage.

Keep this page short.

### `docs/usage/content/tools/<tool-name>/usage.md`

Purpose: task-oriented usage guide.

Must include:

- Common usage patterns.
- Step-by-step workflows.
- Safe defaults.
- Destructive-operation warnings where relevant.
- Links to examples and command reference.

### `docs/usage/content/tools/<tool-name>/commands.md`

Purpose: factual command reference.

Must include, where applicable:

- Invocation syntax.
- Subcommands.
- Positional arguments.
- Flags/options.
- Defaults.
- Accepted values.
- Exit codes.
- Environment variables.
- Config files.
- Output files.
- Examples for common commands.

Do not include parser internals or implementation details.

### `docs/usage/content/tools/<tool-name>/examples.md`

Purpose: copy-pasteable usage examples.

Each example should include:

- Goal.
- Command/input.
- Expected result.
- Assumptions.

### `docs/usage/content/tools/<tool-name>/troubleshooting.md`

Purpose: user-visible recovery guidance.

Use this structure:

````
## <Symptom or error message>

### Symptom

What the user sees.

### Likely cause

The most likely user-relevant cause.

### Fix

Steps to resolve it.

### Prevention

How to avoid it next time.```

Do not document developer-only stack traces unless the user is likely to see them and needs a recovery action.

### `docs/usage/content/workflows/index.md`

Purpose: cross-tool task guides.

Use for tasks that involve more than one tool or multiple documentation pages.

### `docs/usage/content/reference/index.md`

Purpose: global reference shared by multiple tools.

Examples:

* Common config format.
* Shared environment variables.
* Shared exit codes.
* Shared output conventions.
* Supported file types.

### `docs/usage/content/troubleshooting/index.md`

Purpose: global troubleshooting.

Examples:

* Permission problems.
* Path problems.
* Missing dependency problems.
* Encoding problems.
* Output location confusion.

### `docs/usage/content/glossary.md`

Purpose: define terms users need to operate the tools.

Keep definitions usage-oriented.

## Page front matter policy

Use minimal YAML front matter on every page.

Example:

````

---

title: Quickstart description: First successful use of <tool-name>. tags:

- quickstart
- cli

---

# Quickstart```

Allowed tags must come from `tags_allowed` in `docs/usage/mkdocs.yml`.

Do not add developer workflow metadata, internal status metadata, agent metadata, implementation metadata, review metadata, or handoff metadata to usage pages.

## Link policy

Use normal Markdown links to Markdown files.

Good:

````
See [the command reference](commands.md).
See [global troubleshooting](../../troubleshooting/index.md).```

Bad:

````

[[Command reference]] [Command reference](commands.html) [Command reference](/site/tools/tool-name/commands.html)```

Do not use Obsidian-style wikilinks.

Do not link to generated HTML files from source Markdown.

## Feedback intake design

Usage docs remain read-only. Feedback intake uses GitHub issue forms.

The feedback flow is:

````
User reads docs in browser
  -> clicks small feedback icon beside an H2/H3 heading
  -> GitHub issue form opens
  -> issue fields are prefilled with page/section/anchor context
  -> user fills in the actual report
  -> coding agent later reviews GitHub issues```

This keeps usage docs clean while still giving implementation agents precise feedback.

## Required GitHub issue form

Create:

````

.github/ISSUE_TEMPLATE/tool-feedback.yml```

Use:

````
name: Tool feedback
description: Report a bug, confusing behavior, or requested behavior change while using the documented tools.
title: "[Tool feedback]: "
labels:
  - user-feedback
  - triage

body:
  - type: markdown
    attributes:
      value: |
        Use this form for feedback about using a tool in this repository.

        This form is for user-visible behavior: bugs, confusing behavior, requested behavior changes, and documentation issues encountered while using the tools.

  - type: input
    id: doc_page
    attributes:
      label: Documentation page
      description: The documentation page where this feedback started.
      placeholder: /tools/example-tool/commands/
    validations:
      required: false

  - type: input
    id: doc_section
    attributes:
      label: Documentation section
      description: The section heading where this feedback started.
      placeholder: Dry run
    validations:
      required: false

  - type: input
    id: doc_anchor
    attributes:
      label: Documentation anchor
      description: The page anchor for the section.
      placeholder: dry-run
    validations:
      required: false

  - type: input
    id: doc_url
    attributes:
      label: Documentation URL
      description: The local or published URL that opened this issue form.
    validations:
      required: false

  - type: input
    id: tool
    attributes:
      label: Tool
      description: Which tool does this concern?
      placeholder: example-tool
    validations:
      required: false

  - type: dropdown
    id: feedback_type
    attributes:
      label: Feedback type
      options:
        - Bug
        - Behavior change request
        - Documentation issue
        - Question
    validations:
      required: true

  - type: textarea
    id: observed
    attributes:
      label: What happened?
      description: Describe the behavior, bug, confusing output, or desired change.
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: What did you expect instead?
    validations:
      required: false

  - type: textarea
    id: steps
    attributes:
      label: Steps, command, or context
      description: Paste the command, input, output, or steps to reproduce.
      render: shell
    validations:
      required: false```

GitHub issue forms are YAML form definitions with structured body elements such as inputs, textareas, dropdowns, checkboxes, and markdown.

## Required H2/H3 feedback icon

Add a small unobtrusive feedback link to every H2 and H3 heading in the rendered Material site.

Do not manually hard-code links after every heading. Use a small JavaScript customization so the links are generated from the rendered page.

Create:

````

docs/usage/content/assets/feedback-links.js```

Use this as the baseline:

````
(function () {
  const owner = "OWNER";
  const repo = "REPO";
  const template = "tool-feedback.yml";

  function cleanHeadingText(heading) {
    const clone = heading.cloneNode(true);
    clone.querySelectorAll(".section-feedback-link").forEach((node) => node.remove());
    return clone.textContent.trim();
  }

  function inferTool(pagePath) {
    const match = pagePath.match(/\/tools\/([^/]+)\//);
    return match ? match[1] : "";
  }

  function buildIssueUrl(heading) {
    const sectionTitle = cleanHeadingText(heading);
    const anchor = heading.id || "";
    const pagePath = window.location.pathname;
    const fullUrl = anchor
      ? `${window.location.origin}${window.location.pathname}#${anchor}`
      : window.location.href;

    const params = new URLSearchParams({
      template,
      title: `[Tool feedback]: ${sectionTitle}`,
      doc_page: pagePath,
      doc_section: sectionTitle,
      doc_anchor: anchor,
      doc_url: fullUrl,
      tool: inferTool(pagePath),
    });

    return `https://github.com/${owner}/${repo}/issues/new?${params.toString()}`;
  }

  function addFeedbackLinks() {
    document.querySelectorAll(".md-typeset h2[id], .md-typeset h3[id]").forEach((heading) => {
      if (heading.querySelector(".section-feedback-link")) {
        return;
      }

      const link = document.createElement("a");
      link.className = "section-feedback-link";
      link.href = buildIssueUrl(heading);
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.title = "Report a problem or request a change for this section";
      link.setAttribute("aria-label", `Report feedback for section: ${cleanHeadingText(heading)}`);
      link.textContent = "□";

      heading.appendChild(link);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addFeedbackLinks);
  } else {
    addFeedbackLinks();
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(addFeedbackLinks);
  }
})();```

Before finalizing, replace:

````

const owner = "OWNER"; const repo = "REPO";```

with the actual GitHub owner and repository name.

The `document$.subscribe(addFeedbackLinks)` hook is included so the links are re-applied after Material’s client-side navigation updates page content.

## Required feedback icon CSS

Create:

````
docs/usage/content/assets/feedback-links.css```

Use:

````

.md-typeset h2, .md-typeset h3 { position: relative; }

.md-typeset .section-feedback-link { float: right; margin-left: 0.5rem; font-size: 0.7em; line-height: 1; opacity: 0.35; text-decoration: none; }

.md-typeset .section-feedback-link:hover, .md-typeset .section-feedback-link:focus { opacity: 1; text-decoration: none; }```

The icon must remain visually small and low-clutter. It must not consume an entire line.

## Feedback-link scope

Apply feedback icons to:

````
H2
H3```

Do not apply by default to:

````

H1 H4 H5 H6 paragraphs list items tables code blocks admonitions```

Rationale:

- H1 is page-level and already represented by page URL.
- H2/H3 gives useful position precision.
- H4+ creates visual noise and excessive issue-link density.

## GitHub feedback caveats

This feedback mechanism requires GitHub access.

For private repositories, the person clicking the feedback link must have permission to create issues.

The docs may be viewed locally at `localhost`, so the prefilled `doc_url` may be a local URL. That is acceptable because `doc_page`, `doc_section`, and `doc_anchor` are the stable metadata the agent should use.

## Agent instruction integration

The adopting agent must update the repository’s existing agent-instruction or handoff system so future agents understand the purpose, scope, location, and workflow for usage documentation.

Different repositories may use different systems. The agent must inspect the repository and apply the guidance to the repo’s actual convention.

Possible instruction locations include, but are not limited to:

````
AGENTS.md
CLAUDE.md
GEMINI.md
.github/copilot-instructions.md
.cursor/rules/
.windsurf/
docs/dev/
docs/agent/
.handoff/```

Do not create a new agent-instruction system if the repository already has a clear convention. Extend the existing convention.

If the repository has no agent-instruction system, create the smallest reasonable instruction file using the repo’s naming conventions. Prefer `AGENTS.md` only if no other convention is present.

## Required agent-instruction content

Wherever the repository keeps agent-facing instructions, add guidance equivalent to the following.

````

## Usage documentation system

This repository uses MkDocs + Material for repo-local user-facing usage documentation.

Location:

- MkDocs config: `docs/usage/mkdocs.yml`
- Markdown source: `docs/usage/content/`
- Static build output: `docs/usage/.site/`
- Feedback issue form: `.github/ISSUE_TEMPLATE/tool-feedback.yml`

Purpose:

The `docs/usage/` system is strictly for user-facing documentation about how to use the tools this repository provides.

In scope:

- Tool overviews
- Quickstarts
- Usage guides
- Command references
- Configuration visible to users
- Examples
- User-visible troubleshooting
- Safety notes for destructive or bulk operations
- H2/H3 feedback links to GitHub issue forms

Out of scope:

- Architecture notes
- Implementation details
- ADRs
- Developer handoff notes
- Coding-agent scratchpads
- Internal TODOs
- Test strategy
- Refactor plans
- Historical development notes

Rules for future agents:

- Do not put developer or implementation documentation under `docs/usage/content/`.
- Do not use `docs/usage/content/` as a scratchpad.
- Do not document internals unless users need that information to operate a tool correctly.
- Keep command references aligned with actual current CLI/help behavior.
- Use normal Markdown links to `.md` source files.
- Do not use Obsidian-style wikilinks.
- Keep every source page represented in `docs/usage/mkdocs.yml` navigation unless intentionally excluded.
- Preserve the H2/H3 feedback-link assets unless intentionally replacing the feedback mechanism.
- Validate changes with:

  ````bash
  uv run mkdocs build --strict -f docs/usage/mkdocs.yml```

  ````

- Preview locally with:

  ````
  uv run mkdocs serve -f docs/usage/mkdocs.yml```
  ````

When updating tool behavior, update the usage docs if the user-facing commands, options, defaults, inputs, outputs, safety behavior, or troubleshooting behavior changed.

````

The exact wording may be adapted to match the repository’s existing instruction style, but the substance must be preserved.

## Agent workflow for adopting this system

### Phase 1: Inspect repository conventions

Before modifying files:

1. Identify the repository type and tooling.
2. Identify package/dependency management.
3. Identify all existing documentation directories.
4. Identify existing agent-instruction or handoff files.
5. Identify GitHub repository owner/name if available.
6. Identify user-facing tools.
7. Identify how users invoke those tools.
8. Identify whether the repo already has issue templates.

Do not assume every script or module is user-facing.

### Phase 2: Install documentation tooling

If this is a Python/uv repo:

```bash
uv add --dev mkdocs mkdocs-material```

If the repo uses a docs dependency group, follow that convention instead.

If the repo is not Python/uv, use the repo’s existing dependency/tooling convention while preserving the same MkDocs file layout and commands as closely as possible.

### Phase 3: Create MkDocs usage system

Create:

````

docs/usage/mkdocs.yml docs/usage/content/ docs/usage/content/assets/feedback-links.css docs/usage/content/assets/feedback-links.js```

Add:

````
docs/usage/.site/```

### Phase 4: Create GitHub issue form

Create or update:

````

.github/ISSUE_TEMPLATE/tool-feedback.yml```

If issue templates already exist, integrate this form without deleting existing templates unless explicitly instructed.

### Phase 5: Create baseline content

Create the baseline Markdown pages:

````
docs/usage/content/index.md
docs/usage/content/start-here.md
docs/usage/content/tools/index.md
docs/usage/content/workflows/index.md
docs/usage/content/reference/index.md
docs/usage/content/troubleshooting/index.md
docs/usage/content/glossary.md```

For each confirmed user-facing tool, create:

````

docs/usage/content/tools/<tool-name>/index.md docs/usage/content/tools/<tool-name>/quickstart.md docs/usage/content/tools/<tool-name>/usage.md docs/usage/content/tools/<tool-name>/commands.md docs/usage/content/tools/<tool-name>/examples.md docs/usage/content/tools/<tool-name>/troubleshooting.md```

### Phase 6: Populate from actual behavior

For each CLI-style tool, inspect actual help output where possible:

````
<tool> --help
<tool> <subcommand> --help
python -m <module> --help
uv run <tool> --help
uv run python -m <module> --help```

Use whichever invocation matches the repo.

Do not invent options, flags, defaults, outputs, or environment variables.

If something cannot be verified, do not present it as fact in user docs. Note the uncertainty in the final implementation report.

### Phase 7: Update agent instructions

Update the repository’s existing agent-instruction system with the usage-documentation scope, location, and validation commands.

This is mandatory.

The agent must use judgment based on repository conventions. The goal is for future agents to know:

* Where usage docs live.
* What belongs there.
* What does not belong there.
* How to update them.
* How to validate them.
* How feedback issue links work.
* When user-facing changes require docs updates.

### Phase 8: Validate

Run:

````

uv run mkdocs build --strict -f docs/usage/mkdocs.yml```

Fix all warnings and errors.

Then run:

````
uv run mkdocs serve -f docs/usage/mkdocs.yml```

Verify:

* Site loads.
* Navigation works.
* Search works.
* H2/H3 feedback icons appear.
* Feedback icons open the GitHub issue form.
* Issue form fields are prefilled.
* Links are not visually noisy.
* All usage pages are in navigation.

### Phase 9: Final report

After adoption, report:

* Files created.
* Files modified.
* Dependencies added.
* User-facing tools documented.
* Agent-instruction files updated.
* Validation commands run.
* Any warnings/errors fixed.
* Any user-facing behavior that could not be verified.
* Any issue-form or GitHub metadata that needs repository-specific confirmation.

Do not place this final report under `docs/usage/content/`.

## Content style rules

Write for users.

Use:

````

Run this command. Set this option. The tool writes output to... Use this when...```

Avoid:

````
This module implements...
The parser internally...
The agent should...
We chose this design because...
Future work...
TODO...```

Prefer task headings:

````

## Convert a directory

## Preview changes before writing files

## Write output to a separate location```

Avoid implementation headings:

````
## Processing pipeline
## Internal architecture
## Parser behavior```

## Safety documentation requirement

If a tool can overwrite, delete, rename, move, encrypt, decrypt, archive, transform, or bulk-edit files, its docs must clearly state:

* Whether it modifies files in place.
* Whether it has dry-run mode.
* Whether it creates backups.
* How output paths are selected.
* What happens on conflicts.
* How to verify results before committing changes.
* How to recover or rerun safely.

Use admonitions for user-visible safety warnings:

````

!!! warning "This can overwrite files" This command writes changes in place. Run with `--dry-run` first.```

Do not overuse admonitions.

## Navigation policy

Use explicit navigation in `docs/usage/mkdocs.yml`.

Every Markdown page under `docs/usage/content/` should either appear in `nav:` or be intentionally excluded with a clear reason.

Orphan pages are usually a mistake.

When adding a tool, update navigation:

````
nav:
  - Home: index.md
  - Start here: start-here.md
  - Tools:
      - tools/index.md
      - Tool Name:
          - Overview: tools/tool-name/index.md
          - Quickstart: tools/tool-name/quickstart.md
          - Usage: tools/tool-name/usage.md
          - Commands: tools/tool-name/commands.md
          - Examples: tools/tool-name/examples.md
          - Troubleshooting: tools/tool-name/troubleshooting.md
  - Workflows:
      - workflows/index.md
  - Reference:
      - reference/index.md
  - Troubleshooting:
      - troubleshooting/index.md
  - Glossary: glossary.md```

## Example tool overview page

````

---

title: <Tool Name> description: User guide for <tool-name>. tags:

- cli

---

# <Tool Name>

<One-sentence description of what the tool does for the user.>

## When to use it

Use `<tool-name>` when you need to...

## When not to use it

Do not use `<tool-name>` when...

## Inputs

- ...

## Outputs

- ...

## Typical workflow

1. ...
2. ...
3. ...

## Next

- [Quickstart](quickstart.md)
- [Usage guide](usage.md)
- [Command reference](commands.md)
- [Examples](examples.md)
- [Troubleshooting](troubleshooting.md)```

## Example quickstart page

````
---
title: Quickstart
description: First successful use of <tool-name>.
tags:
  - quickstart
  - cli
---

# Quickstart

This page shows the shortest path to a successful `<tool-name>` run.

## Prerequisites

- ...

## Run the tool

```bash
<command>
````

## Expected result

The tool should...

## Next

See [usage](usage.md) for common workflows.```

## Example command reference page

````
---
title: Command reference
description: Commands and options for <tool-name>.
tags:
  - reference
  - cli
---

# Command reference

## Invocation

```bash
<tool-name> [OPTIONS] <ARGUMENTS>
````

## Commands

| Command     | Purpose |
| ----------- | ------- |
| `<command>` | ...     |

## Arguments

| Argument     | Required | Description |
| ------------ | -------: | ----------- |
| `<argument>` |      Yes | ...         |

## Options

| Option      | Default | Description |
| ----------- | ------- | ----------- |
| `--example` | `false` | ...         |

## Exit codes

| Code | Meaning                |
| ---: | ---------------------- |
|  `0` | Success                |
|  `1` | User-correctable error |

## Environment variables

| Variable | Description |
| -------- | ----------- |
| `<NAME>` | ...         |

## Examples

```bash
<example command>
```

## Example troubleshooting page

````
---
title: Troubleshooting
description: Common <tool-name> problems and fixes.
tags:
  - troubleshooting
---

# Troubleshooting

## `<error message or symptom>`

### Symptom

The user sees...

### Likely cause

This usually means...

### Fix

1. ...
2. ...
3. ...

### Prevention

...```

## Quality checklist

Adoption is complete only when all are true:

* `docs/usage/mkdocs.yml` exists.

* `docs/usage/content/` exists.

* `docs/usage/.site/` is gitignored.

* MkDocs and Material are dev/docs dependencies, not runtime dependencies.

* `.github/ISSUE_TEMPLATE/tool-feedback.yml` exists.

* `docs/usage/content/assets/feedback-links.css` exists.

* `docs/usage/content/assets/feedback-links.js` exists.

* Feedback JS has the correct GitHub owner/repo.

* H2/H3 feedback icons render without visual clutter.

* Feedback icons open the correct GitHub issue form.

* Issue form receives page, section, anchor, URL, and tool context.

* `docs/usage/content/index.md` states the docs are user-facing usage docs only.

* Every documented tool is actually user-facing.

* Every user-facing tool has overview, quickstart, usage, commands, examples, and troubleshooting pages.

* Command references match actual current behavior.

* Internal architecture and implementation notes are excluded.

* ADRs, specs, handoff notes, scratch notes, and TODOs are excluded.

* Navigation includes all intended pages.

* Cross-links use normal Markdown links to `.md` source files.

* Tags are from the allowed tag list.

* Repository agent instructions were updated to preserve this scope.

* `uv run mkdocs build --strict -f docs/usage/mkdocs.yml` succeeds.

* `uv run mkdocs serve -f docs/usage/mkdocs.yml` works.


## Final instruction to the adopting agent

Do not treat this as a general documentation cleanup.

Do not create a developer wiki.

Do not move internal notes into `docs/usage/`.

Do not place agent handoffs, implementation notes, ADRs, specs, test plans, or scratch material in `docs/usage/content/`.

Do not explain how the tools are built unless that information is directly necessary for a user to operate them.

Adopt a clean, repo-local, browser-readable, Markdown-authored **usage guide** for the tools this repository provides, and update the repo’s agent-instruction system so future agents preserve that boundary.

* * *

**You:**

I would like to add some additional strongly suggested or even mandatory guidelines to prevent drift between repositories and to prevent variations and how these instructions are consumed in interpreted. For example, do you think it would be a good idea to ship this with a pre-written a ADR that canalizes things like the tag sets and similar

* * *

**ChatGPT:**

Yes — I’d make the drift controls explicit and versioned. An ADR is useful, but it should not be the only control; pair it with a canonical config, a conformance checklist, and agent-instruction text that says what is allowed to vary.

Yes. I would ship this standard with a **pre-written ADR**, but the ADR should not be the only guardrail.

An ADR is good for **declaring the decision and non-negotiables**. To actually prevent drift, pair it with:

1. **A canonical ADR** explaining the adopted usage-docs system.
2. **A conformance checklist** that agents must run against each repo.
3. **A canonical tag set and issue-form field set** treated as controlled vocabulary.
4. **Agent-instruction text** that explicitly says what may vary per repo and what may not.
5. **A version identifier** for the usage-docs standard.

One important refinement: the “strictly user-facing” boundary should apply to:

````

docs/usage/content/

```

not necessarily the whole `docs/usage/` tree.

That lets you keep system/governance files beside the MkDocs setup without rendering them as user documentation:

```

repo/ docs/ usage/ mkdocs.yml content/ # rendered user-facing docs only governance/ # non-rendered adoption/control docs adr-0001-adopt-usage-docs-standard.md conformance-checklist.md controlled-vocabulary.md .site/ # generated, ignored

```

`docs/usage/governance/` should **not** appear in MkDocs `nav:` and should not be rendered as part of the user-facing site.

## What I would make mandatory

These should be treated as **standard invariants** across repos:

| Area | Mandatory rule |
| --- | --- |
| System path | MkDocs usage system lives under `docs/usage/`. |
| User-facing source | Rendered user docs live under `docs/usage/content/`. |
| Config path | MkDocs config lives at `docs/usage/mkdocs.yml`. |
| Build output | Generated output goes to `docs/usage/.site/`. |
| Scope | `docs/usage/content/` is only for user-facing usage documentation. |
| Governance | ADR/checklist/vocabulary may live under `docs/usage/governance/`, not under `content/`. |
| Tags | Use the canonical tag allowlist unless the standard is intentionally revised. |
| Front matter | Use minimal front matter: `title`, `description`, `tags`. |
| Links | Use normal Markdown links; no Obsidian wikilinks. |
| Feedback | H2/H3 feedback links use the standard GitHub issue form field IDs. |
| Validation | Build must pass with `uv run mkdocs build --strict -f docs/usage/mkdocs.yml`. |
| Agent awareness | Existing repo agent instructions must be updated to preserve the scope boundary. |

## What may vary by repo

These can vary without violating the standard:

| Area | Allowed variation |
| --- | --- |
| `site_name` | Repo-specific name. |
| `site_description` | Repo-specific description. |
| Tool pages | Depends on the repo’s actual user-facing tools. |
| Navigation entries | Tool-specific page structure may expand where justified. |
| Dependency group | `--dev` vs `--group docs`, depending on repo convention. |
| GitHub owner/repo | Must match the actual repository. |
| Extra tags | Only if added through an explicit local ADR or standard revision. |
| Additional pages | Allowed if they are user-facing usage docs. |

## I would add this ADR

# ADR-0001: Adopt Standard Repo-Local Usage Documentation System

Date: 2026-07-07

## Status

Accepted

## Context

This repository provides one or more tools that users run or interact with directly. The repository also contains developer-facing materials such as implementation notes, specifications, architecture decisions, coding-agent handoffs, scratch notes, tests, and internal project documentation.

Those internal materials are not suitable as user-facing usage documentation.

A separate, consistent, repo-local documentation layer is needed so users can understand how to install, configure, run, operate, and troubleshoot the tools this repository provides.

The documentation system must:

* Live inside the repository.
* Be consistent across repositories.
* Be readable as Markdown source.
* Be viewable as a local browser site.
* Avoid requiring a separate hosted wiki, CMS, or database-backed service.
* Avoid polluting the repository root.
* Preserve a strict boundary between user-facing usage documentation and developer/internal documentation.
* Provide a low-friction way for users to report bugs, confusing behavior, documentation problems, or behavior-change requests from the relevant section of the docs.

## Decision

Adopt **MkDocs + Material for MkDocs** as the standard repo-local usage documentation system.

The usage-documentation system must live under:

```

docs/usage/```

The rendered user-facing documentation source must live under:

````
docs/usage/content/```

The MkDocs configuration file must live at:

````

docs/usage/mkdocs.yml```

The generated MkDocs output must go to:

````
docs/usage/.site/```

The generated output directory must be ignored by Git.

The canonical local preview command is:

````

uv run mkdocs serve -f docs/usage/mkdocs.yml```

The canonical validation command is:

````
uv run mkdocs build --strict -f docs/usage/mkdocs.yml```

GitHub issue forms are used for structured feedback intake. The feedback form must live at:

````

.github/ISSUE_TEMPLATE/tool-feedback.yml```

This is the only required file outside `docs/usage/`, because GitHub issue forms must be located under `.github/ISSUE_TEMPLATE/`.

A small feedback icon must be automatically added beside rendered H2 and H3 headings. The icon opens the GitHub issue form with documentation page, section, anchor, URL, and inferred tool context prefilled.

## Scope boundary

The directory:

````
docs/usage/content/```

is strictly for user-facing usage documentation.

Content in this directory may describe:

* What tools are available.
* When to use a tool.
* When not to use a tool.
* How to install or prepare a tool.
* How to run a tool.
* Commands, subcommands, flags, options, and arguments.
* User-visible configuration.
* Inputs and outputs.
* Examples.
* Workflows.
* Troubleshooting.
* Safety warnings for destructive, bulk, or irreversible operations.
* Glossary terms needed to operate the tools.

Content in this directory must not include:

* Architecture notes.
* Implementation details.
* ADRs.
* Specs.
* Developer handoffs.
* Coding-agent scratchpads.
* Internal TODOs.
* Test strategy.
* Refactor plans.
* Historical development notes.
* Private design rationale.
* Internal module/package documentation unless it is part of the public user interface.

The test is:

> Would a user need this information to successfully use the tools this repository provides?

If no, the content does not belong in `docs/usage/content/`.

## Governance files

Usage-documentation governance files may live under:

````

docs/usage/governance/```

This directory is for non-rendered standard-control material such as:

- This ADR.
- Conformance checklist.
- Controlled vocabulary.
- Adoption notes.
- Local deviations approved by ADR.

Governance files must not be included in MkDocs navigation unless explicitly intended for users, which should normally be avoided.

## Controlled vocabulary

The MkDocs tag set is controlled vocabulary.

The canonical initial tag set is:

````
tags_allowed:
  - cli
  - tui
  - gui
  - configuration
  - installation
  - quickstart
  - workflow
  - reference
  - examples
  - troubleshooting
  - output
  - safety```

Do not add repo-specific tags casually.

Additional tags require one of:

1. A revision to the shared usage-docs standard.
2. A repo-local ADR documenting the reason for the deviation.

## Required issue-form field IDs

The GitHub issue form must preserve these field IDs:

````

doc_page doc_section doc_anchor doc_url tool feedback_type observed expected steps```

These IDs are part of the feedback-link contract. The feedback JavaScript depends on them.

Do not rename these fields unless the feedback JavaScript and this ADR are updated together.

## Required feedback-link behavior

The rendered docs must add feedback links to:

````
H2
H3```

The rendered docs must not add feedback links by default to:

````

H1 H4 H5 H6 paragraphs list items tables code blocks admonitions```

Rationale:

- H2/H3 headings provide useful location precision.
- H1 is already page-level.
- H4+ creates excessive visual clutter.
- Body-level links would pollute the reading experience.

## Required page structure

At minimum, create:

````
docs/usage/content/
  index.md
  start-here.md
  tools/
    index.md
  workflows/
    index.md
  reference/
    index.md
  troubleshooting/
    index.md
  glossary.md```

For each confirmed user-facing tool, create:

````

docs/usage/content/tools/<tool-name>/ index.md quickstart.md usage.md commands.md examples.md troubleshooting.md```

Do not create tool documentation for internal packages, modules, test helpers, private scripts, or implementation components unless they are directly exposed to users.

## Required front matter

Every rendered usage page should use minimal front matter:

````
---
title: <Page Title>
description: <Short user-facing description.>
tags:
  - <allowed-tag>
---```

Do not add developer metadata, implementation metadata, agent metadata, review metadata, status metadata, or handoff metadata to rendered usage pages.

## Required link style

Use normal Markdown links to Markdown source files.

Good:

````

See [the command reference](commands.md). See [global troubleshooting](../../troubleshooting/index.md).```

Do not use Obsidian-style wikilinks.

Do not link to generated HTML files from Markdown source.

## Agent-instruction requirement

Any repository adopting this system must update its existing agent-instruction or handoff system so future agents understand:

- Where usage docs live.
- What belongs in `docs/usage/content/`.
- What does not belong there.
- How to update the docs.
- How to validate the docs.
- How H2/H3 feedback links work.
- When user-facing behavior changes require usage-doc updates.

The adopting agent must follow the repository’s existing convention for agent instructions. Possible locations include:

````
AGENTS.md
CLAUDE.md
GEMINI.md
.github/copilot-instructions.md
.cursor/rules/
.windsurf/
docs/dev/
docs/agent/
.handoff/```

If no convention exists, create the smallest reasonable instruction file using the repository’s style. Prefer `AGENTS.md` only when no other convention is present.

## Consequences

Benefits:

* Consistent usage-documentation layout across repositories.
* Clear separation between user docs and developer/internal docs.
* Browser-readable local documentation without a separate hosted wiki.
* Markdown source remains easy for humans and agents to edit.
* Feedback links provide precise context for future implementation work.
* Agent instructions reduce drift across future maintenance sessions.

Costs:

* Each repo must carry MkDocs configuration and docs dependencies.
* GitHub issue forms require `.github/ISSUE_TEMPLATE/`.
* Feedback links require small JavaScript/CSS assets.
* Tags and page structure must be maintained intentionally.
* Docs must be updated when user-facing tool behavior changes.

## Non-goals

This system is not intended to replace:

* Developer documentation.
* Architecture documentation.
* ADRs outside the usage-docs governance decision.
* Test documentation.
* Coding-agent handoff systems.
* Project planning documents.
* Public hosted documentation platforms.
* A writable wiki.
* A full issue tracker.

## Enforcement

A repository conforms to this ADR only when:

* `docs/usage/mkdocs.yml` exists.
* `docs/usage/content/` exists.
* `docs/usage/.site/` is gitignored.
* `.github/ISSUE_TEMPLATE/tool-feedback.yml` exists.
* H2/H3 feedback assets exist.
* The canonical tag set is present unless an ADR-approved deviation exists.
* The repository’s agent instructions include usage-doc maintenance rules.
* `uv run mkdocs build --strict -f docs/usage/mkdocs.yml` succeeds.
* Rendered usage pages contain only user-facing usage documentation.

## I would also add a controlled vocabulary file

This is intentionally not user-facing content. Put it here:

````

docs/usage/governance/controlled-vocabulary.md

```

# Usage Documentation Controlled Vocabulary

Date: 2026-07-07

## Purpose

This file defines controlled vocabulary for the repository’s MkDocs + Material usage-documentation system.

These values exist to prevent drift across repositories and across coding-agent sessions.

## Canonical tag set

The canonical tag set is:

```

tags_allowed:

- cli
- tui
- gui
- configuration
- installation
- quickstart
- workflow
- reference
- examples
- troubleshooting
- output
- safety```

## Tag definitions

| Tag | Meaning |
| --- | --- |
| `cli` | Command-line interface usage. |
| `tui` | Terminal user interface usage. |
| `gui` | Graphical user interface usage. |
| `configuration` | User-visible settings, config files, environment variables, or defaults. |
| `installation` | Installation, setup, prerequisites, or preparation. |
| `quickstart` | Shortest path to first successful use. |
| `workflow` | Task-oriented usage involving one or more steps/tools. |
| `reference` | Factual lookup material such as commands, options, arguments, outputs, or exit codes. |
| `examples` | Copy-pasteable examples and expected results. |
| `troubleshooting` | User-visible failure recovery. |
| `output` | User-visible generated files, terminal output, reports, logs, or artifacts. |
| `safety` | Warnings about destructive, irreversible, bulk, or security-sensitive actions. |

## Tag rules

Use only the canonical tags unless a repo-local ADR approves an additional tag.

Do not create synonyms.

Examples:

<table><tbody><tr><td><span>Do not add</span></td><td><span>Use instead</span></td></tr><tr><td><code dir="ltr"><span>command-line</span></code></td><td><code dir="ltr"><span>cli</span></code></td></tr><tr><td><code dir="ltr"><span>terminal</span></code></td><td><code dir="ltr"><span>cli</span></code><span> or </span><code dir="ltr"><span>tui</span></code></td></tr><tr><td><code dir="ltr"><span>setup</span></code></td><td><code dir="ltr"><span>installation</span></code></td></tr><tr><td><code dir="ltr"><span>config</span></code></td><td><code dir="ltr"><span>configuration</span></code></td></tr><tr><td><code dir="ltr"><span>how-to</span></code></td><td><code dir="ltr"><span>workflow</span></code></td></tr><tr><td><code dir="ltr"><span>errors</span></code></td><td><code dir="ltr"><span>troubleshooting</span></code></td></tr><tr><td><code dir="ltr"><span>danger</span></code></td><td><code dir="ltr"><span>safety</span></code></td></tr></tbody></table>

## Front matter keys

Allowed front matter keys for rendered usage pages:

````
title:
description:
tags:```

Do not add:

````

status: owner: reviewer: agent: todo: implementation: created: updated: decision: adr:```

Rendered usage pages are not developer handoff documents.

## Feedback issue-form field IDs

The feedback form must preserve these field IDs:

````
doc_page
doc_section
doc_anchor
doc_url
tool
feedback_type
observed
expected
steps```

The H2/H3 feedback-link JavaScript depends on these names.

## Feedback type values

Allowed `feedback_type` values:

````

Bug Behavior change request Documentation issue Question```

Do not add additional values unless the feedback-processing workflow is also updated.

## Required validation command

Use:

````
uv run mkdocs build --strict -f docs/usage/mkdocs.yml```

The build must pass before usage-documentation changes are considered complete.

## I would update the adoption document with one stronger rule

Add a section like this:

```Markdown
## Standard drift control

This repository treats the usage-documentation system as a versioned local standard.

The following files are governance/control files and are not user-facing documentation:

- `docs/usage/governance/adr-0001-adopt-usage-docs-standard.md`
- `docs/usage/governance/controlled-vocabulary.md`
- `docs/usage/governance/conformance-checklist.md`

Future agents must not silently change:

- directory layout
- MkDocs config location
- `docs_dir`
- `site_dir`
- canonical tags
- issue-form field IDs
- feedback-link heading scope
- validation commands
- user-facing scope boundary

Any intentional deviation requires either:

1. updating the shared standard, or
2. adding a repo-local ADR explaining the deviation.
````

That gives the consuming agent less room to “interpret” the system differently in each repo.

---

**You:**

GitHub I already published an ADR standard. It should be under the org associated with my personal account and the repo name is project – standards

---

**ChatGPT:**

I’ll look up the repo and inspect the ADR standard rather than assuming the filename or structure. Then I’ll adjust the recommendation so this usage-docs system references your existing standard instead of duplicating governance unnecessarily.

Found it: `L3DigitalNet/project-standards`, public, default branch `main`, with admin/maintain/push access available through the connector. I’ll inspect the repository structure and locate the ADR standard so the usage-doc adoption spec can align to it instead of inventing a parallel convention.

Yes — and that should change the design.

I found the repo as **`L3DigitalNet/project-standards`**, public, default branch `main`.[](https://github.com/L3DigitalNet/project-standards)

[L3DigitalNet/project-standards](https://github.com/L3DigitalNet/project-standards)

It already has an ADR standard, and that standard says consuming repos put ADRs under **`docs/decisions/`**, not inside a docs subsystem like `docs/usage/governance/`.

## Updated recommendation

Do **not** ship a standalone local ADR standard inside every repo.

Instead:

1. Put the **canonical MkDocs/Material usage-docs standard** in `L3DigitalNet/project-standards` as a real standards bundle.
2. In each consuming repo, create only a **local adoption ADR** under `docs/decisions/`.
3. The local ADR should say: “This repo adopts the centralized usage-documentation standard from `project-standards`.”
4. The local repo should not redefine tag sets, issue-form fields, heading-feedback behavior, or directory layout unless it records a deviation ADR.

That keeps the standard centralized and prevents each repo from slowly inventing its own interpretation.

## Important correction to my earlier structure

Earlier I suggested:

```
docs/usage/governance/
```

I would drop that now.

Given your existing ADR standard, the better structure is:

```
repo/
  docs/
    usage/
      mkdocs.yml
      content/
      .site/
    decisions/
      README.md
      adr-000N-adopt-repo-local-usage-docs-standard.md
```

The ADR belongs in `docs/decisions/` because your ADR standard already defines that as the consuming-repo ADR location. It also defines the ID/filename convention: ADR IDs include the repo name for global uniqueness, while filenames omit the repo-name segment.

## One conflict to resolve

Your `project-standards` repo already has an active **CLI Documentation Standard**. It governs user-facing CLI usage docs and is registered as an adoptable standard. It also says the Packaged profile uses `docs/usage.md` as the canonical usage reference.

That conflicts with the new desired structure:

```
docs/usage/mkdocs.yml
docs/usage/content/
```

So I would **not** treat the existing `cli-documentation` standard as the complete answer. I would make the MkDocs/Material system a **sibling standard** or a **higher-level site standard** that can incorporate CLI documentation rules.

Best name:

```
standards/usage-documentation-site/
```

or:

```
standards/tool-usage-docs/
```

I prefer **`usage-documentation-site`** because it clearly governs the browser/site layer, not just CLI reference content.

## How the central standard should be arranged

Your standards repo already defines the bundle pattern: every standard gets a folder with required `README.md` and `adopt.md`, optional `templates/`, `examples/`, and `resources/`.

So the new standard should live as:

```
L3DigitalNet/project-standards/
  standards/
    usage-documentation-site/
      README.md
      adopt.md
      templates/
        mkdocs.yml
        tool-feedback.yml
        feedback-links.css
        feedback-links.js
        content/
          index.md
          start-here.md
          tools/
            index.md
          workflows/
            index.md
          reference/
            index.md
          troubleshooting/
            index.md
          glossary.md
      examples/
        example-mkdocs.yml
        example-tool-page.md
      resources/
        rationale.md
```

The central standard should own:

| Item                           | Central standard owns it?       |
| ------------------------------ | ------------------------------- |
| `docs/usage/` layout           | Yes                             |
| `docs/usage/mkdocs.yml` shape  | Yes                             |
| canonical tag set              | Yes                             |
| issue-form field IDs           | Yes                             |
| feedback-link H2/H3 behavior   | Yes                             |
| required page types            | Yes                             |
| user-facing scope boundary     | Yes                             |
| adoption checklist             | Yes                             |
| agent-instruction requirements | Yes                             |
| repo-specific tool pages       | No                              |
| repo-specific adoption ADR     | No, generated in consuming repo |

## Drop-in replacement for the adoption document

Use this to replace the earlier “governance” section.

## Central standard authority

This repository adopts the repo-local usage-documentation system from the centralized project standards repository:

````
L3DigitalNet/project-standards```

The authoritative standard is expected to live under:

````

standards/usage-documentation-site/```

The consuming repository must not redefine the usage-documentation system locally. Local files implement the standard; they do not become the standard.

The following items are controlled by the central standard:

- `docs/usage/` directory layout
- `docs/usage/mkdocs.yml` configuration shape
- `docs/usage/content/` scope boundary
- canonical tag set
- page front matter policy
- GitHub issue-form field IDs
- H2/H3 feedback-link behavior
- required page types
- validation command
- agent-instruction requirements

Repo-specific variation is allowed only for:

- repository name and site title
- actual tools documented
- tool-specific page content
- GitHub owner/repo values
- navigation entries required by actual tools
- dependency-group choice, where repo convention differs

Intentional deviations from the central standard require a local ADR.

## Local adoption ADR

A consuming repository must record adoption with a local ADR under:

````
docs/decisions/```

Do not place ADRs under `docs/usage/`.

The ADR should state that the repository adopts the centralized usage-documentation standard and should record any repo-specific deviations.

The local ADR should follow the repository’s adopted ADR standard, including:

* canonical front matter
* MADR body structure
* repo-scoped ADR numbering
* `docs/decisions/README.md` index entry

The ADR should not duplicate the full central standard. It should link to or reference the central standard and record only the local decision and any local deviations.

## Relationship to CLI documentation standard

The usage-documentation-site standard governs the browser-readable MkDocs/Material documentation system.

The CLI Documentation Standard continues to govern CLI usage-reference content, including command names, synopsis notation, options, exit codes, environment variables, examples, and drift checks.

When both standards apply:

* `docs/usage/` is the documentation site root.
* `docs/usage/content/` contains the rendered user-facing usage docs.
* CLI command-reference pages inside the site must follow the CLI Documentation Standard’s content rules.
* The site standard supersedes any older single-file `docs/usage.md` path convention for repositories that adopt the MkDocs/Material usage site.
* Any path conflict must be resolved explicitly in the adoption ADR or by revising the central standards.

## Local ADR template shape

Your ADR standard uses MADR required sections: `Context and Problem Statement`, `Considered Options`, and `Decision Outcome`. The existing ADR template also includes the canonical front matter and optional decision-driver/consequence sections.

For a consuming repo, the ADR should be short. It is not the standard; it is the local decision to follow the standard.

```Markdown
---
schema_version: '1.1'
id: 'adr-000N-<repo-name>-adopt-usage-documentation-site-standard'
title: 'ADR 000N: Adopt usage documentation site standard'
description: 'Adopt the centralized MkDocs/Material usage-documentation site standard for user-facing tool docs.'
doc_type: 'adr'
status: 'active'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
reviewed: null
owner: ''
consumer: 'agent'
tags:
  - 'adr'
  - 'documentation'
  - 'usage-docs'
related:
  - 'L3DigitalNet/project-standards:standards/usage-documentation-site/README.md'
  - 'L3DigitalNet/project-standards:standards/cli-documentation/README.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers: []
  consulted: []
  informed: []
---

# ADR 000N: Adopt usage documentation site standard

## Context and Problem Statement

This repository exposes user-facing tools that need usage documentation separate from developer documentation, implementation notes, specs, ADRs, and coding-agent handoff material.

The repository needs a consistent, repo-local, browser-readable documentation system that can be adopted across multiple repositories without layout drift.

## Considered Options

- Plain Markdown files only
- Repo-local MkDocs/Material usage documentation site
- Separate hosted wiki or documentation platform
- Per-repo custom documentation structure

## Decision Outcome

Chosen option: "Repo-local MkDocs/Material usage documentation site", because it provides Markdown-authored source files, local browser preview, static output, search/navigation, and a consistent cross-repository layout while keeping usage docs inside the repository.

This repository adopts the centralized usage-documentation-site standard from `L3DigitalNet/project-standards`.

### Consequences

- User-facing usage documentation lives under `docs/usage/content/`.
- MkDocs configuration lives at `docs/usage/mkdocs.yml`.
- Generated output lives under `docs/usage/.site/` and is not committed.
- Developer docs, implementation notes, specs, ADRs, and agent handoffs must not be placed under `docs/usage/content/`.
- Future agents must update usage docs when user-facing tool behavior changes.
- Local deviations from the central standard require a follow-up ADR.
````

## Bottom line

The right move is to make **`project-standards` the source of truth** and have each repo adopt it by ADR. The ADR should live in `docs/decisions/`, while the actual MkDocs usage system lives in `docs/usage/`.

Also, the existing **CLI Documentation Standard** should be treated as a sibling content standard, not replaced. The new MkDocs/Material standard should either explicitly extend it or revise it so the old `docs/usage.md` convention does not fight the new `docs/usage/` site layout.

---

**You:**

OK, now that you have access to my standards repository let’s change the scope a little bit to be that instead of creating an adoption document that I feed to an agent for repo let’s re-architect our system into a proper standard following the conventions that my project standards repo already follows

---

**ChatGPT:**

I’ll treat this as a standards-repo design task now, not a per-repo adoption doc. I’ll align the new standard to your bundle anatomy, ADR/frontmatter rules, existing CLI Documentation sibling standard, and adopt-engine expectations before proposing the shape.

There is one design issue worth locking now: the existing CLI Documentation Standard already materializes `docs/usage.md`, so the new site standard must explicitly override that path only when adopted. Otherwise two standards will fight over the same concept.

Yes. The right re-architecture is:

**Create a new first-class standard bundle in `project-standards`, not an adoption document copied into each repo.**

Call it:

```
usage-documentation-site
```

This standard should govern the **MkDocs + Material site layer** for repo-local, browser-readable, user-facing tool usage documentation. It should become a sibling to the existing **CLI Documentation Standard**, not a replacement for it.

Your repo already defines the bundle anatomy: each standard lives under `standards/<standard-id>/` with required `README.md` and `adopt.md`, optional `templates/`, `examples/`, and `resources/`.

## Core architectural decision

Use this separation:

| Standard | Owns |
| --- | --- |
| `cli-documentation` | CLI content rules: command names, synopsis, options, exit codes, examples, help/docs drift checks. |
| `usage-documentation-site` | Site rules: MkDocs/Material layout, `docs/usage/`, navigation, tags, feedback links, page taxonomy, issue-form integration, agent-instruction integration. |

That matters because the current CLI Documentation Standard says Packaged CLIs use `docs/usage.md` as the usage reference. The existing adopt bundle also materializes `docs/usage.md`. The new site standard should explicitly say: **when `usage-documentation-site` is adopted, the MkDocs site layout supersedes the single-file `docs/usage.md` path convention, but the CLI content rules still apply inside the site.**

# Design: Usage Documentation Site Standard

Date: 2026-07-07

## Recommendation

Add a new standards bundle to `L3DigitalNet/project-standards`:

````
standards/usage-documentation-site/```

This standard governs repo-local, browser-readable, user-facing usage documentation built with MkDocs + Material for MkDocs.

It replaces the prior idea of feeding each repo a standalone adoption document. The central standards repository becomes the source of truth, and each consuming repository adopts the standard through the existing project-standards adoption workflow plus a local ADR under `docs/decisions/`.

## Standard ID

Use:

````

usage-documentation-site```

Rationale:

- It describes the thing being standardized: a repo-local documentation site.
- It avoids overloading the existing `cli-documentation` standard.
- It is broader than CLI only; it can cover CLI, TUI, GUI, scripts, local services, and other user-facing tools.
- It preserves room for the CLI Documentation Standard to remain the content-contract standard for CLI surfaces.

## Contract version

Initial contract version:

````
1.0```

Registry key:

````

usage_documentation_site```

This follows the existing registry naming style used by `cli_documentation`, `markdown_tooling`, and `python_tooling`. The current registry already tracks contract versions for those standards, so this standard should be added as a new versioned label standard.

## Standard bundle layout

Add:

````
standards/
  usage-documentation-site/
    README.md
    adopt.md
    templates/
      mkdocs.yml
      tool-feedback.yml
      feedback-links.css
      feedback-links.js
      content/
        index.md
        start-here.md
        tools/
          index.md
        workflows/
          index.md
        reference/
          index.md
        troubleshooting/
          index.md
        glossary.md
      agent-instructions-fragment.md
      gitignore-fragment
      config.usage-documentation-site.yml
    examples/
      mkdocs.example.yml
      tool-overview.example.md
      command-reference.example.md
      troubleshooting.example.md
    resources/
      rationale.md```

The bundle follows the standards repo’s established anatomy: `README.md` is the governing standard, `adopt.md` is the runbook, `templates/` contains copy-adopt scaffolds, `examples/` contains worked examples, and `resources/` carries rationale/research material.

## Consuming repository layout

A consuming repo adopting this standard gets:

````

docs/ usage/ mkdocs.yml content/ index.md start-here.md tools/ index.md workflows/ index.md reference/ index.md troubleshooting/ index.md glossary.md assets/ feedback-links.css feedback-links.js .site/ .github/ ISSUE_TEMPLATE/ tool-feedback.yml docs/ decisions/ adr-000N-adopt-usage-documentation-site-standard.md```

Generated output:

````
docs/usage/.site/```

Git-ignored output:

````

docs/usage/.site/```

The ADR must live under `docs/decisions/`, not under `docs/usage/`, because the ADR standard already defines `docs/decisions/` as the consuming-repo ADR location.

## Relationship to existing ADR standard

Consuming repositories should record adoption with a local ADR.

The ADR standard already defines:

- ADR front matter.
- MADR body structure.
- `docs/decisions/` as the consuming-repo ADR directory.
- The ID convention where the ADR ID embeds the repo name but the filename omits it.

Therefore, the site standard should not invent a `docs/usage/governance/` directory. Governance belongs in the central standards repo and local decisions belong in `docs/decisions/`.

## Relationship to CLI Documentation Standard

The existing CLI Documentation Standard remains valid for CLI-specific content rules.

The new standard should add this rule:

> When a repository adopts `usage-documentation-site`, CLI usage-reference content may live inside the MkDocs site under `docs/usage/content/` instead of the legacy single-file `docs/usage.md` location. The CLI Documentation Standard still governs the substance of CLI command documentation.

This avoids a standards conflict.

Recommended mapping:

| Existing CLI standard concept | Site-standard location |
| --- | --- |
| `docs/usage.md` single usage reference | `docs/usage/content/tools/<tool-name>/commands.md` or `reference.md` |
| README points to usage reference | README points to `docs/usage/` and local `mkdocs serve` command |
| CLI examples | `docs/usage/content/tools/<tool-name>/examples.md` |
| CLI exit status | Tool command reference or shared `reference/index.md` |
| Environment/files | Tool command reference or shared `reference/index.md` |
| Drift checks | Existing CLI Documentation Standard still owns parser/help drift rules |

The CLI standard should receive a small compatibility amendment rather than being rewritten.

## Governing standard: `README.md`

The new standard’s `README.md` should be normative.

Recommended sections:

````
# Usage Documentation Site Standard

Evidence convention
Requirement language
Version assumptions

1. Purpose
2. Scope and sibling standards
3. Adopted stack
4. Repository layout
5. MkDocs configuration
6. User-facing content boundary
7. Required page taxonomy
8. Navigation and link rules
9. Front matter and tags
10. Feedback intake
11. GitHub issue form contract
12. H2/H3 feedback-link behavior
13. Agent-instruction integration
14. Relationship to CLI Documentation Standard
15. Adoption and validation
16. Exceptions process
17. Update process / review cadence
18. Source register```

Use the same evidence convention style already used by the CLI Documentation Standard: source-backed facts cite source IDs, and project policy decisions are labeled as local standards.

## Requirement language

Reuse the requirement-language block from the CLI Documentation Standard unless there is a reason to diverge. It already defines RFC 2119 semantics plus deterministic verb mapping for agents.

## Normative scope

The standard should define this hard boundary:

````

docs/usage/content/```

is strictly for user-facing usage documentation.

In scope:

- Tool overviews.
- Quickstarts.
- Usage guides.
- Command references.
- User-visible configuration.
- Inputs.
- Outputs.
- Examples.
- Workflows.
- Troubleshooting.
- Safety notes.
- Glossary terms needed to use the tools.
- H2/H3 feedback links into GitHub issue forms.

Out of scope:

- Architecture notes.
- Implementation details.
- ADRs.
- Specs.
- Developer handoff notes.
- Coding-agent scratchpads.
- Internal TODOs.
- Test strategy.
- Refactor plans.
- Historical implementation notes.
- Private design rationale.

Decision test:

````
Would a user need this information to successfully use the tools this repository provides?```

If no, it does not belong under `docs/usage/content/`.

## MkDocs configuration contract

The standard should require:

````

docs/usage/mkdocs.yml```

with:

````
site_name: '<REPO NAME> User Guide'
site_description: 'User-facing usage documentation for the tools provided by this repository.'

docs_dir: content
site_dir: .site

strict: true
use_directory_urls: true

theme:
  name: material
  features:
    - navigation.sections
    - navigation.indexes
    - navigation.top
    - search.highlight
    - search.suggest
    - content.code.copy

plugins:
  - search
  - tags:
      tags_allowed:
        - cli
        - tui
        - gui
        - configuration
        - installation
        - quickstart
        - workflow
        - reference
        - examples
        - troubleshooting
        - output
        - safety

extra_css:
  - assets/feedback-links.css

extra_javascript:
  - assets/feedback-links.js

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
  - pymdownx.details
  - pymdownx.superfences

validation:
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn

nav:
  - Home: index.md
  - Start here: start-here.md
  - Tools:
      - tools/index.md
  - Workflows:
      - workflows/index.md
  - Reference:
      - reference/index.md
  - Troubleshooting:
      - troubleshooting/index.md
  - Glossary: glossary.md```

MkDocs supports a non-root config file via `-f` / `--config-file`, so keeping `mkdocs.yml` under `docs/usage/` is compatible with MkDocs. Navigation paths in MkDocs are relative to `docs_dir`, which supports this `docs/usage/mkdocs.yml` plus `docs_dir: content` structure. MkDocs also supports validation settings that can warn on omitted files, broken links, unrecognized links, and anchors, with `warn` intended to work with strict builds.

## Canonical commands

Preview:

````

uv run mkdocs serve -f docs/usage/mkdocs.yml```

Validate:

````
uv run mkdocs build --strict -f docs/usage/mkdocs.yml```

These commands should be the standard’s canonical commands. If a repo does not use `uv`, the standard may allow equivalent invocation, but the file layout and MkDocs config path remain invariant.

## Canonical tag set

Treat tags as controlled vocabulary.

````

tags_allowed:

- cli
- tui
- gui
- configuration
- installation
- quickstart
- workflow
- reference
- examples
- troubleshooting
- output
- safety```

Do not add repo-local synonyms casually.

Examples:

<table><tbody><tr><td><span>Avoid</span></td><td><span>Use</span></td></tr><tr><td><code dir="ltr"><span>command-line</span></code></td><td><code dir="ltr"><span>cli</span></code></td></tr><tr><td><code dir="ltr"><span>terminal</span></code></td><td><code dir="ltr"><span>cli</span></code><span> or </span><code dir="ltr"><span>tui</span></code></td></tr><tr><td><code dir="ltr"><span>setup</span></code></td><td><code dir="ltr"><span>installation</span></code></td></tr><tr><td><code dir="ltr"><span>config</span></code></td><td><code dir="ltr"><span>configuration</span></code></td></tr><tr><td><code dir="ltr"><span>how-to</span></code></td><td><code dir="ltr"><span>workflow</span></code></td></tr><tr><td><code dir="ltr"><span>errors</span></code></td><td><code dir="ltr"><span>troubleshooting</span></code></td></tr><tr><td><code dir="ltr"><span>danger</span></code></td><td><code dir="ltr"><span>safety</span></code></td></tr></tbody></table>

Additional tags require either a central standard revision or a repo-local deviation ADR.

## Front matter policy

Usage pages should use only:

````
---
title: '<Page title>'
description: '<Short user-facing description.>'
tags:
  - '<allowed-tag>'
---```

Do not allow developer/process fields in rendered usage pages:

````

status: owner: reviewer: agent: todo: implementation: decision: adr:```

Those fields belong to managed internal documents, not user-facing usage pages.

## Feedback mechanism

The standard should require GitHub issue-form feedback links at rendered H2 and H3 headings.

GitHub issue forms support structured YAML form fields such as inputs, textareas, dropdowns, checkboxes, and uploads, and issue forms have top-level fields such as `name`, `description`, `body`, `labels`, and `title`. GitHub also supports creating issues from URL query parameters, including `title`, `body`, `labels`, `assignees`, `projects`, and `template`; it also supports URL query parameters for custom text fields in issue forms.

Required issue-form path:

````
.github/ISSUE_TEMPLATE/tool-feedback.yml```

Required field IDs:

````

doc_page doc_section doc_anchor doc_url tool feedback_type observed expected steps```

These are contract fields. The feedback-link JavaScript depends on them.

## Feedback-link implementation

Material for MkDocs supports additional CSS and JavaScript files through `extra_css` and `extra_javascript`, and it documents using the `document$` observable for JavaScript that must run after page loads or instant navigation updates.

Required files in consuming repos:

````
docs/usage/content/assets/feedback-links.css
docs/usage/content/assets/feedback-links.js```

Required heading scope:

````

H2 H3```

Do not apply feedback links by default to:

````
H1
H4
H5
H6
paragraphs
list items
tables
code blocks
admonitions```

Rationale:

* H2/H3 gives useful precision without heavy clutter.
* H1 is page-level.
* H4+ creates too much density.
* Body-level links pollute the reading experience.

## Agent-instruction integration

The site standard should require each adopting repo to update its existing agent-instruction system.

Possible locations include:

````

AGENTS.md CLAUDE.md GEMINI.md .github/copilot-instructions.md .cursor/rules/ .windsurf/ docs/dev/ docs/agent/ docs/handoff/```

The standard should not require one universal agent-instruction filename. Instead, it should require that the adopting agent update whatever agent-instruction system the repo already uses.

Required instruction substance:

- `docs/usage/content/` is only for user-facing usage docs.
- Developer docs, specs, ADRs, handoffs, and scratchpads do not belong there.
- User-facing tool behavior changes require docs updates.
- Command references must match actual CLI/help behavior.
- H2/H3 feedback assets and issue-form fields are part of the standard contract.
- Validate with `uv run mkdocs build --strict -f docs/usage/mkdocs.yml`.
- Preview with `uv run mkdocs serve -f docs/usage/mkdocs.yml`.

## Adopt bundle

Add packaged adopt artifacts under:

````
src/project_standards/bundles/usage-documentation-site/```

The adopt system discovers standards by checking bundle directories for `adopt.toml`. Manifest artifacts currently support `file`, `workflow-caller`, and `fragment`; file artifacts need `dest`, fragment artifacts need `target`, and exactly one of `source` or `shared` is set.

Recommended bundle layout:

````

src/project_standards/ bundles/ usage-documentation-site/ adopt.toml mkdocs.yml tool-feedback.yml feedback-links.css feedback-links.js content.index.md content.start-here.md content.tools.index.md content.workflows.index.md content.reference.index.md content.troubleshooting.index.md content.glossary.md config.usage-documentation-site.yml gitignore.usage-documentation-site agent-instructions.usage-documentation-site.md```

Recommended `adopt.toml`:

````
[standard]
id = "usage-documentation-site"

[[artifact]]
kind = "file"
owner = true
source = "mkdocs.yml"
dest = "docs/usage/mkdocs.yml"

[[artifact]]
kind = "file"
owner = true
source = "content.index.md"
dest = "docs/usage/content/index.md"

[[artifact]]
kind = "file"
owner = true
source = "content.start-here.md"
dest = "docs/usage/content/start-here.md"

[[artifact]]
kind = "file"
owner = true
source = "content.tools.index.md"
dest = "docs/usage/content/tools/index.md"

[[artifact]]
kind = "file"
owner = true
source = "content.workflows.index.md"
dest = "docs/usage/content/workflows/index.md"

[[artifact]]
kind = "file"
owner = true
source = "content.reference.index.md"
dest = "docs/usage/content/reference/index.md"

[[artifact]]
kind = "file"
owner = true
source = "content.troubleshooting.index.md"
dest = "docs/usage/content/troubleshooting/index.md"

[[artifact]]
kind = "file"
owner = true
source = "content.glossary.md"
dest = "docs/usage/content/glossary.md"

[[artifact]]
kind = "file"
owner = true
source = "feedback-links.css"
dest = "docs/usage/content/assets/feedback-links.css"

[[artifact]]
kind = "file"
owner = true
source = "feedback-links.js"
dest = "docs/usage/content/assets/feedback-links.js"

[[artifact]]
kind = "file"
owner = true
source = "tool-feedback.yml"
dest = ".github/ISSUE_TEMPLATE/tool-feedback.yml"

[[artifact]]
kind = "fragment"
owner = true
source = "config.usage-documentation-site.yml"
target = ".project-standards.yml"

[[artifact]]
kind = "fragment"
owner = true
source = "gitignore.usage-documentation-site"
target = ".gitignore"

[[artifact]]
kind = "fragment"
owner = true
source = "agent-instructions.usage-documentation-site.md"
target = "AGENTS.md or repo-local agent instruction system"```

Fragments are reported rather than written by the existing adopt engine, which is appropriate for `.project-standards.yml`, `.gitignore`, and agent-instruction text because those files are repo-specific. Existing file artifacts are skipped unless `--force` is used, so the adoption process remains safe and idempotent.

## Registry changes

Update:

````

src/project_standards/schemas/registry.json src/project_standards/registry.py```

Add:

````
"usage_documentation_site": { "default": "1.0", "versions": ["1.0"] }```

`registry.py` currently hardcodes the known versioned standards in its constructor and loader, including `cli_documentation` but not the proposed site standard. The loader currently requires `frontmatter`, `adr`, `python_tooling`, `markdown_tooling`, and `cli_documentation` objects. Add `usage_documentation_site` consistently to that path.

## Top-level standards index

Update:

````

standards/README.md```

Add a row:

````
| Usage Documentation Site | Repo-local MkDocs/Material site for user-facing tool usage docs, feedback links, and local browser preview | [usage-documentation-site/](usage-documentation-site/) | [adopt](usage-documentation-site/adopt.md) |```

The top-level standards index already lists each standard, what it governs, its bundle, and adoption runbook.

## CLI Documentation Standard compatibility amendment

Update:

````

standards/cli-documentation/README.md standards/cli-documentation/adopt.md src/project_standards/bundles/cli-documentation/adopt.toml```

Add a compatibility rule:

````
If a repository adopts usage-documentation-site, the canonical CLI usage reference may live under docs/usage/content/ instead of docs/usage.md. The CLI Documentation Standard still governs the content contract, but the Usage Documentation Site Standard governs the location, navigation, feedback links, and MkDocs site structure.```

Potential adopt-engine issue:

* Today `cli-documentation` materializes `docs/usage.md`.
* If a repo adopts both standards at once, the current manifests will not collide at the same destination, but they will produce two competing usage documentation surfaces.
* Do not rely on users to understand that conflict.

Preferred fix:

* Leave `cli-documentation` v1.0 behavior intact for legacy/simple repos.
* Add clear compatibility language in both standards.
* In a future `cli-documentation` v1.1, consider adding a site-aware profile or fragment-only guidance rather than always materializing `docs/usage.md`.

## Local adoption ADR

The new standard should require a consuming repo to create an ADR under:

````

docs/decisions/```

Suggested title:

````
ADR 000N: Adopt usage documentation site standard```

The ADR should be short. It records local adoption; it does not duplicate the central standard.

Template should follow the ADR standard’s MADR structure, whose required sections are:

````

Context and Problem Statement Considered Options Decision Outcome```

The ADR standard documents those required MADR body sections.

## Implementation plan for the standards repo

### Phase 1: Add the standard bundle

Create:

````
standards/usage-documentation-site/README.md
standards/usage-documentation-site/adopt.md
standards/usage-documentation-site/templates/
standards/usage-documentation-site/examples/
standards/usage-documentation-site/resources/```

### Phase 2: Add adopt artifacts

Create:

````

src/project_standards/bundles/usage-documentation-site/```

with `adopt.toml` and scaffold files.

### Phase 3: Register the standard

Update:

````
src/project_standards/schemas/registry.json
src/project_standards/registry.py```

Add tests wherever existing registry/adopt parity tests expect every versioned standard to have both registry metadata and an adopt bundle.

### Phase 4: Update standards index

Update:

````

standards/README.md```

Add the new standard row.

### Phase 5: Amend CLI Documentation Standard

Add compatibility text explaining how `cli-documentation` interacts with `usage-documentation-site`.

Do not silently let both standards imply separate canonical usage-doc locations.

### Phase 6: Add examples

Examples should include:

````
examples/
  mkdocs.example.yml
  tool-overview.example.md
  command-reference.example.md
  troubleshooting.example.md```

Examples should be valid managed Markdown where appropriate, using the frontmatter standard.

### Phase 7: Add rationale

Put research and rationale in:

````

standards/usage-documentation-site/resources/rationale.md```

The governing `README.md` should contain rules; the resources file should contain the reasoning, tradeoffs, and source discussion.

### Phase 8: Validate

Run the repo’s normal validation gate after implementation.

At minimum:

````
uv run project-standards validate
uv run project-standards list
uv run project-standards adopt usage-documentation-site --dry-run```

Also run the project’s existing tests if present.

## Non-goals

The new standard should explicitly say it is not:

* A developer documentation standard.
* A replacement for ADRs.
* A replacement for project specs.
* A replacement for coding-agent handoff docs.
* A public hosting/deployment standard.
* A writable wiki.
* A generated API reference standard.
* A replacement for the CLI Documentation Standard.

## Key invariants

These should be mandatory across repos:

<table><tbody><tr><td><span>Invariant</span></td><td><span>Required value</span></td></tr><tr><td><span>Standard ID</span></td><td><code dir="ltr"><span>usage-documentation-site</span></code></td></tr><tr><td><span>Contract version</span></td><td><code dir="ltr"><span>1.0</span></code></td></tr><tr><td><span>Site root</span></td><td><code dir="ltr"><span>docs/usage/</span></code></td></tr><tr><td><span>MkDocs config</span></td><td><code dir="ltr"><span>docs/usage/mkdocs.yml</span></code></td></tr><tr><td><span>Rendered source</span></td><td><code dir="ltr"><span>docs/usage/content/</span></code></td></tr><tr><td><span>Build output</span></td><td><code dir="ltr"><span>docs/usage/.site/</span></code></td></tr><tr><td><span>Feedback issue form</span></td><td><code dir="ltr"><span>.github/ISSUE_TEMPLATE/tool-feedback.yml</span></code></td></tr><tr><td><span>Feedback heading scope</span></td><td><span>H2 and H3 only</span></td></tr><tr><td><span>Tag vocabulary</span></td><td><span>Central allowlist</span></td></tr><tr><td><span>Validation command</span></td><td><code dir="ltr"><span>uv run mkdocs build --strict -f docs/usage/mkdocs.yml</span></code></td></tr><tr><td><span>Preview command</span></td><td><code dir="ltr"><span>uv run mkdocs serve -f docs/usage/mkdocs.yml</span></code></td></tr><tr><td><span>Local adoption decision</span></td><td><span>ADR under </span><code dir="ltr"><span>docs/decisions/</span></code></td></tr></tbody></table>

## Bottom line

The system should become a **new standards bundle** named `usage-documentation-site`.

The central standard owns the MkDocs/Material site structure and controlled vocabulary. Each consuming repo owns only its local tool content and a local ADR recording adoption. The existing `cli-documentation` standard remains the CLI content contract, but it needs a compatibility amendment so `docs/usage.md` does not conflict with the new `docs/usage/` site layout.

* * *

**You:**

Perform a comprehensive and thorough review of the other standards and compared against the requirements of this new usage docs site standard and verify there’s no potential conflict flag any conflicts that you see might be a problem and I’ll resolve those either within the standard or elsewhere if needed

* * *

**ChatGPT:**

I’ll do this as a standards compatibility audit: inspect each existing standard and the adopt/registry mechanics, then classify conflicts as hard blockers, soft conflicts, or design notes. I’ll focus on repo paths, frontmatter/schema rules, adoption artifacts, validation, and sibling-standard boundaries.

The first likely hard conflict is with the Markdown Frontmatter Standard: the usage-site draft’s “minimal front matter” may not be valid if those pages are covered by the frontmatter validator. I’m going to confirm the validator/profile behavior before calling that a blocker.

Confirmed: Project Specification already shows the right precedent for sibling-schema conflicts. It explicitly excludes spec files from canonical frontmatter validation because specs use their own schema; the usage-site standard needs an equally explicit decision on whether rendered user pages are managed canonical docs or not.

# Compatibility audit: proposed Usage Documentation Site Standard

**Date:** 2026-07-07
**Repository reviewed:** `L3DigitalNet/project-standards`

## Executive summary

I found **four real conflicts** that should be resolved before implementing the new `usage-documentation-site` standard:

| Severity | Conflict | Why it matters |
| --- | --- | --- |
| **Blocker** | Proposed “minimal MkDocs front matter” conflicts with the Markdown Frontmatter Standard. | If `docs/usage/content/**/*.md` is included in frontmatter validation, pages with only `title`, `description`, and `tags` will fail. |
| **Blocker** | New standard bundle must be added to registry/adopt parity code. | The adopt/list commands intentionally fail if a bundle exists without a registry entry, or vice versa. |
| **Blocker** | Existing CLI Documentation Standard owns `docs/usage.md`; new site standard owns `docs/usage/`. | Adopting both can create two competing “canonical usage docs” locations. |
| **High** | Proposed tag allowlist conflicts with existing CLI usage tags. | Existing CLI docs use `usage` and `example`; proposed site tags use `examples` and omit `usage`. |

My recommendation: make `usage-documentation-site` a new first-class standard, but revise it so rendered usage pages use **canonical Markdown Frontmatter**, not a separate minimal MkDocs-only front matter profile. Then explicitly amend `cli-documentation` so its content rules can be applied inside the MkDocs site without materializing `docs/usage.md`.

* * *

## Reviewed standards and systems

I reviewed these standards/systems against the proposed site standard:

| Area | Result |
| --- | --- |
| Markdown Frontmatter | **Conflict unless resolved.** |
| ADR | Compatible, with one correction: local ADRs belong under `docs/decisions/`. |
| CLI Documentation | **Conflict with path and canonical-reference model.** |
| Markdown Tooling | Mostly compatible. Watch Prettier/markdownlint expectations. |
| Python Tooling SSOT | Mostly compatible. Need clear docs-validation integration. |
| Project Specification | Compatible; gives a useful precedent for schema separation. |
| Python Coding | No conflict; currently draft/reference-only. |
| Versioning / registry / adopt engine | **Implementation blocker unless updated consistently.** |

* * *

## Conflict 1 — Markdown Frontmatter vs proposed MkDocs page front matter

### Finding

The earlier proposed usage-site pages used this kind of front matter:

```YAML
---
title: Quickstart
description: First successful use of the tool.
tags:
  - quickstart
  - cli
---
````

That does **not** satisfy the existing Markdown Frontmatter Standard if the pages are managed documents. The standard’s “minimal frontmatter” still requires eleven fields: `schema_version`, `id`, `title`, `description`, `doc_type`, `status`, `created`, `updated`, `tags`, `aliases`, and `related`.

The JSON schema also has `additionalProperties: false` and lists those required fields explicitly.

The default adoption config includes `README.md` and `docs/**/*.md`, so in normal consuming repos, `docs/usage/content/**/*.md` will likely be included unless explicitly excluded.

### Why this is a problem

If the new standard ships MkDocs-style minimal front matter while a repo has the Markdown Frontmatter Standard enabled over `docs/**/*.md`, usage-site pages will fail validation.

This is the largest design conflict.

### Resolution options

| Option | Result | Recommendation |
| --- | --- | --- |
| **A. Make usage pages canonical managed docs** | Pages use full Markdown Frontmatter Standard fields. MkDocs/Material consumes `title`, `description`, and `tags`; extra metadata remains hidden in the rendered site. | **Recommended.** |
| B. Exclude `docs/usage/content/**` from frontmatter validation | Allows MkDocs-native minimal front matter. | Not recommended; it weakens cross-repo governance. |
| C. Create a new frontmatter schema for usage pages | Possible, but adds validator/schema complexity. | Overkill for now. |

### Recommended rule

The new standard should say:

> Rendered usage pages under `docs/usage/content/` are managed Markdown documents and must use the canonical Markdown Frontmatter Standard unless a repo-local ADR explicitly excludes them.

Use canonical front matter like:

```YAML
---
schema_version: '1.1'
id: 'reference-xxxxxx-tool-name-command-reference'
title: 'Command reference'
description: 'Commands and options for tool-name.'
doc_type: 'reference'
status: 'active'
created: 'YYYY-MM-DD'
updated: 'YYYY-MM-DD'
reviewed: null
owner: ''
consumer: 'user'
tags:
  - 'cli'
  - 'reference'
aliases: []
related: []
source: []
confidence: 'high'
visibility: 'public'
license: null
---
```

That aligns with the existing standard and still works as MkDocs page metadata.

---

## Conflict 2 — Registry/adopt parity must be updated or `adopt` fails

### Finding

The standards repo intentionally enforces registry/bundle parity. The CLI’s `_REGISTRY_STANDARD_IDS` list currently includes:

```
markdown-frontmatter
adr
python-tooling
markdown-tooling
cli-documentation
```

and no `usage-documentation-site`.

The CLI then compares available adopt bundles with registry-tracked standards and fails if they do not match.

The registry currently contains `frontmatter`, `adr`, `python_tooling`, `markdown_tooling`, and `cli_documentation` only.

### Why this is a problem

If you add:

```
src/project_standards/bundles/usage-documentation-site/
```

but do not update the registry and CLI parity list, `project-standards list` and `project-standards adopt` will fail.

Likewise, adding a registry key without a bundle will fail.

### Required updates

Add `usage-documentation-site` / `usage_documentation_site` consistently to:

```
src/project_standards/schemas/registry.json
src/project_standards/registry.py
src/project_standards/cli.py
src/project_standards/bundles/usage-documentation-site/adopt.toml
.project-standards.yml
meta/versioning.md
standards/README.md
tests
```

Also update `validate_frontmatter.py`, because it currently parses and validates metadata-only version keys for `python_tooling`, `markdown_tooling`, and `cli_documentation`, but not `usage_documentation_site`.

---

## Conflict 3 — CLI Documentation owns `docs/usage.md`; site standard owns `docs/usage/`

### Finding

The existing CLI Documentation Standard says the Packaged profile requires:

```
docs/usage.md
```

as the usage reference.

Its adopt bundle also materializes:

```
docs/usage.md
```

directly.

The new site standard wants:

```
docs/usage/mkdocs.yml
docs/usage/content/
docs/usage/.site/
```

### Why this is a problem

There is no literal file-path collision, but there is a **semantic collision**:

```
docs/usage.md        # existing CLI standard canonical usage reference
docs/usage/          # proposed site standard root
```

A repo adopting both standards could end up with two authoritative usage documentation locations.

The CLI standard also describes `docs/usage.md` as the exhaustive user contract in its help-text boundary table.

### Recommended resolution

Do **not** break `cli-documentation` v1.0 by changing its existing bundle behavior immediately.

Instead:

1. Add compatibility language to `cli-documentation`.
2. Add compatibility language to `usage-documentation-site`.
3. In the new site standard, state that it governs the site location and navigation.
4. In the CLI standard, state that CLI content rules may be satisfied inside the site when `usage-documentation-site` is adopted.

Recommended wording:

```
If a repository adopts usage-documentation-site, the canonical CLI usage reference may live under docs/usage/content/ instead of docs/usage.md. The CLI Documentation Standard still governs CLI content: synopsis notation, option entries, exit codes, environment variables, examples, help boundary, and drift checks. The Usage Documentation Site Standard governs location, navigation, page taxonomy, feedback links, and MkDocs configuration.
```

### Longer-term option

In a future `cli-documentation` contract version, add a site-aware adoption mode. Do not silently change the v1.0 `docs/usage.md` scaffold without classifying the release impact.

---

## Conflict 4 — Proposed tag allowlist conflicts with existing CLI docs tags

### Finding

The proposed site tag allowlist was:

```YAML
tags_allowed:
  - cli
  - tui
  - gui
  - configuration
  - installation
  - quickstart
  - workflow
  - reference
  - examples
  - troubleshooting
  - output
  - safety
```

Existing real CLI usage docs use:

```YAML
tags:
  - 'cli'
  - 'usage'
  - 'reference'
```

The existing CLI usage example uses:

```YAML
tags:
  - 'cli'
  - 'usage'
  - 'example'
```

### Why this is a problem

If those files are migrated into the MkDocs site and Material’s tags plugin enforces `tags_allowed`, then `usage` and `example` would be invalid.

### Resolution options

| Option | Result | Recommendation |
| --- | --- | --- |
| Add `usage` and `example` to the site tag allowlist | Maximum compatibility with existing docs. | Acceptable but weaker vocabulary discipline. |
| Retag existing docs to `reference` and `examples` | Cleaner vocabulary. | **Recommended if migration is intentional.** |
| Keep `usage` but not `example` | Allows broad usage docs tag but fixes singular/plural drift. | Also reasonable. |

My recommendation: **do not add both `usage` and `example` unless you want to preserve existing tags without migration.**

Better canonical set:

```YAML
tags_allowed:
  - cli
  - tui
  - gui
  - configuration
  - installation
  - quickstart
  - usage
  - workflow
  - reference
  - examples
  - troubleshooting
  - output
  - safety
```

Then define:

```
usage = general use/operation page
workflow = task-oriented multi-step guide
examples = copy-pasteable example collection
reference = lookup contract
```

Do **not** allow both `example` and `examples`. Pick `examples`.

---

## Conflict 5 — Usage-site docs validation vs Python Tooling “one obvious gate”

### Finding

Python Tooling defines a single obvious verification gate for Python projects:

```Bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

The usage-site standard adds another required validation command:

```Bash
uv run mkdocs build --strict -f docs/usage/mkdocs.yml
```

### Why this matters

This is not a direct contradiction, but it is a standards-integration gap. If a Python repo adopts both standards, is the MkDocs build part of the one obvious verification gate, or a separate docs gate?

If left undefined, repos will drift.

### Recommended resolution

Add a cross-standard rule:

> For repos that already have an aggregate verification gate, adopting `usage-documentation-site` must add the MkDocs strict build to that aggregate gate or document why docs validation remains a separate gate.

This could be handled through:

```
scripts/check.py
.vscode/tasks.json
.github/workflows/docs-usage.yml
project-standards validate
```

Do not change Python Tooling’s base gate globally. Instead, define usage-site validation as a **sibling-standard extension**.

---

## Conflict 6 — Agent-instruction integration must be a fragment, not a file

### Finding

Python Tooling owns `AGENTS.md` and `CLAUDE.md` as adoptable files. Its bundle writes both directly.

It also says `AGENTS.md` and `CLAUDE.md` may be full instruction files or pointers, and alternate instruction systems must preserve the standard’s core rules.

The Markdown Frontmatter Standard says agent-instruction files must never carry frontmatter and should be excluded, not made into managed docs.

### Why this matters

If `usage-documentation-site` tried to ship a full `AGENTS.md`, it would collide with Python Tooling and with repo-specific handoff systems.

### Recommended resolution

The usage-site adopt bundle should ship only a **fragment** targeting `AGENTS.md`, not a file artifact.

Use:

```TOML
[[artifact]]
kind = "fragment"
owner = true
source = "agent-instructions.usage-documentation-site.md"
target = "AGENTS.md"
```

The fragment text should explicitly say it may be merged into the repo’s existing agent-instruction system instead of literal `AGENTS.md`.

This fits the adopt engine because fragments are reported, not written.

---

## Conflict 7 — Project Standards repo dogfooding path needs a deliberate migration

### Finding

The standards repo currently validates `docs/usage.md`, not `docs/usage/content/**/*.md`, in `.project-standards.yml`.

It also declares `cli_documentation.version: "1.0"`.

### Why this matters

If `project-standards` dogfoods the new site standard, it must choose what happens to the existing `docs/usage.md`.

Options:

1. Keep `docs/usage.md` as the CLI Documentation Standard dogfood artifact and add a separate `docs/usage/` site.
2. Move/duplicate the CLI usage reference into the MkDocs site.
3. Make the MkDocs site the new canonical usage surface and deprecate `docs/usage.md`.

Option 1 is least disruptive but leaves two usage surfaces. Option 3 is cleanest but requires updating CLI Documentation Standard compatibility language and examples.

### Recommended migration

For the standards repo itself:

```
docs/usage.md
```

should eventually become:

```
docs/usage/content/tools/project-standards/commands.md
```

or:

```
docs/usage/content/reference/project-standards-cli.md
```

But do this only after the new site standard is written and the CLI Documentation Standard has a compatibility amendment.

---

## Conflict 8 — Versioning standard must be updated

### Finding

The Versioning Standard currently describes six standards plus the Python Coding draft.

Its per-standard contract table includes Frontmatter, ADR, Python Tooling, Markdown Tooling, Project Specification, and CLI Documentation only.

### Required update

Add `Usage Documentation Site` to:

- purpose section
- per-standard contract table
- component-level markers if needed
- change-classification table if the standard is copy-adopted
- related front matter
- source/coverage references where applicable

Recommended classification:

```
Usage Documentation Site | 1.0 | usage_documentation_site.version | no — copy-adopted label, metadata only
```

This mirrors Python Tooling, Markdown Tooling, and CLI Documentation.

---

## Conflict 9 — Markdown Tooling mostly compatible, but the usage-site standard must respect its body model

### Finding

Markdown Tooling governs Markdown and adjacent structured text, with Prettier formatting supported file types and markdownlint linting Markdown only. It explicitly leaves frontmatter semantics to the Markdown Frontmatter Standard.

It also assumes the model:

```
frontmatter title + body # H1
```

and configures markdownlint around that.

### Compatibility result

No hard conflict.

The usage-site templates should follow:

```Markdown
---
canonical frontmatter here
---

# Page title
```

Do not rely on frontmatter title alone without a body H1.

Also ensure generated template Markdown uses ATX headings and ordinary Markdown links; that aligns with Markdown Tooling’s heading and lint rules.

---

## Conflict 10 — Project Specification is compatible, but gives a useful precedent

### Finding

Project Specification explicitly says specs use their own frontmatter schema and are not governed by the Markdown Frontmatter Standard; consumers adopting both must exclude spec files from the canonical frontmatter validator.

Its adoption runbook repeats that repositories adopting both standards must exclude spec directories from frontmatter validation.

### Relevance to usage-site

This gives a clean precedent: if usage-site pages are **not** canonical frontmatter documents, the standard must say so explicitly and require matching `.project-standards.yml` exclusions.

But I recommend the opposite: make usage-site pages canonical frontmatter documents. Unlike specs, they do not need a special schema.

---

## Conflict 11 — ADR standard is compatible if local adoption ADRs stay under `docs/decisions/`

### Finding

The ADR Standard says consuming repositories store ADRs under:

```
docs/decisions/
```

with a `README.md` index.

It also defines the special ADR ID/filename convention: ADR IDs include the repo name for global uniqueness, while filenames omit it.

### Compatibility result

No conflict if the usage-site standard says:

```
Do not put ADRs under docs/usage/.
Local adoption ADRs belong under docs/decisions/.
```

This is the right correction to the earlier `docs/usage/governance/` idea.

---

## Conflict 12 — Python Coding is currently not a blocking standard

### Finding

Python Coding is explicitly marked as draft, reference-only, not registered for adoption or validation.

### Compatibility result

No hard conflict.

The only relevant point is style: it uses the same deterministic requirement-language model as the other standards, including RFC 2119 semantics and verb mapping.

The new usage-site standard should reuse the same requirement-language block for consistency.

---

## Conflict 13 — Issue form lives under `.github/`, which is correctly excluded from frontmatter validation

### Finding

The Markdown Frontmatter adoption config excludes `.github/**`.

### Compatibility result

No conflict.

The required file:

```
.github/ISSUE_TEMPLATE/tool-feedback.yml
```

can live there without being treated as a managed Markdown document.

### Operational caveat

If the issue form declares labels like `user-feedback` or `triage`, consuming repos may need those labels to exist. I would either:

1. omit default labels from the template, or
2. document that adopters must create the labels.

This is not a standards conflict, but it is a practical adoption footgun.

---

## Required changes before implementation

### Must resolve before coding

| Item | Required decision |
| --- | --- |
| Frontmatter model | Use canonical Markdown Frontmatter for usage pages, or explicitly exclude them. I recommend canonical. |
| CLI docs interaction | Define site-aware compatibility with `cli-documentation`; avoid two canonical locations. |
| Tag vocabulary | Decide whether to include `usage` and whether to migrate `example` → `examples`. |
| Verification gate | Decide how MkDocs strict build integrates with repo-level checks. |
| Registry/adopt changes | Add `usage_documentation_site` everywhere registry/adopt parity requires. |

### Must update in standards repo

```
standards/usage-documentation-site/README.md
standards/usage-documentation-site/adopt.md
standards/usage-documentation-site/templates/
standards/usage-documentation-site/examples/
standards/usage-documentation-site/resources/
src/project_standards/bundles/usage-documentation-site/
src/project_standards/schemas/registry.json
src/project_standards/registry.py
src/project_standards/cli.py
src/project_standards/validate_frontmatter.py
standards/README.md
meta/versioning.md
.project-standards.yml
tests/
```

Also amend:

```
standards/cli-documentation/README.md
standards/cli-documentation/adopt.md
```

---

## Recommended final design decisions

### 1. Rendered usage pages are managed documents

Use canonical Markdown Frontmatter, not minimal MkDocs-only front matter.

### 2. Site standard owns location; CLI standard owns content

`usage-documentation-site` owns:

```
docs/usage/
docs/usage/mkdocs.yml
docs/usage/content/
docs/usage/.site/
feedback links
navigation
tags
page taxonomy
```

`cli-documentation` owns:

```
command synopsis
option contract
exit codes
environment variables
files
examples
help/docs drift checks
```

### 3. Do not create `docs/usage/governance/`

Central governance belongs in `project-standards`. Local adoption decisions belong in:

```
docs/decisions/
```

### 4. Use fragments for repo-specific integration

Use adopt fragments for:

```
.project-standards.yml
.gitignore
AGENTS.md
```

Do not overwrite existing agent-instruction files.

### 5. Treat the tag set as a real contract

Choose one of these:

```YAML
# Strict clean vocabulary
tags_allowed:
  - cli
  - tui
  - gui
  - configuration
  - installation
  - quickstart
  - workflow
  - reference
  - examples
  - troubleshooting
  - output
  - safety
```

or:

```YAML
# Compatibility vocabulary
tags_allowed:
  - cli
  - tui
  - gui
  - configuration
  - installation
  - quickstart
  - usage
  - workflow
  - reference
  - examples
  - troubleshooting
  - output
  - safety
```

I recommend the compatibility vocabulary with `usage`, but still normalize `example` → `examples`.

## Bottom line

The proposed `usage-documentation-site` standard is compatible with the standards ecosystem **if** you make three architectural corrections:

1. **Use canonical frontmatter for rendered usage pages.**
2. **Amend `cli-documentation` so `docs/usage/content/` can satisfy CLI usage-reference requirements when the site standard is adopted.**
3. **Register the new standard everywhere the adopt/registry/versioning machinery expects.**

Without those corrections, the implementation will either fail validation or create ambiguous documentation authority across repos.

---

**You:**

Should we develop a JSON schema that we can use to validate the Yamo files off of?

---

**ChatGPT:**

Yes — **but only for the YAML files whose shape the new standard owns.** Do not create a generic “all YAML in the repo” schema.

I’d add a small schema layer for the **Usage Documentation Site Standard’s controlled YAML artifacts**:

```
standards/usage-documentation-site/schemas/
  mkdocs-usage-site.schema.json
  tool-feedback-issue-form.schema.json
```

And possibly later:

```
  project-standards-usage-site-config.schema.json
```

## What should get a schema

| YAML file | Schema? | Why |
| --- | --- | --- |
| `docs/usage/mkdocs.yml` | **Yes** | The site standard owns this layout and needs to prevent drift: `docs_dir: content`, `site_dir: .site`, required plugins, allowed tags, feedback JS/CSS assets, validation rules. |
| `.github/ISSUE_TEMPLATE/tool-feedback.yml` | **Yes** | The standard depends on exact field IDs like `doc_page`, `doc_section`, `doc_anchor`, `doc_url`, `tool`, `feedback_type`, `observed`, `expected`, `steps`. |
| `.project-standards.yml` fragment | **Maybe later** | Existing validator already parses known config keys; adding full schema support is larger because this file is shared across many standards. |
| `.github/workflows/*.yml` | **No custom schema** | Use existing GitHub Actions schema/editor support. |
| arbitrary repo YAML | **No** | Out of scope and likely to cause noise. |

JSON Schema is appropriate here because it defines structure, required fields, allowed values, and object/array constraints for data documents. JSON Schema’s own docs describe it as a vocabulary for annotating and validating JSON documents, and validators can validate data against a schema after parsing. [![](https://www.google.com/s2/favicons?domain=https://json-schema.org&sz=128)json-schema.org](https://json-schema.org/learn/getting-started-step-by-step) YAML editor tooling also commonly applies JSON schemas to YAML files; YAML Language Server supports JSON Schema drafts including 2020-12 and lets schemas be associated with YAML glob patterns. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/redhat-developer/yaml-language-server)

## Important limitation

A JSON Schema validates the **parsed YAML data model**, not the exact source formatting.

It can enforce:

```
docs_dir must equal content
site_dir must equal .site
strict must be true
required plugin entries exist
required feedback field IDs exist
unknown top-level keys are rejected
```

It cannot reliably enforce:

```
quote style
comment text
key order
blank lines
whether a list used block style
whether a value was single-quoted
```

Those remain owned by Prettier / markdown tooling / repo formatting rules. Your existing Markdown Frontmatter Standard already makes a similar distinction: semantic validation and physical formatting are separate concerns, and the schema rejects unknown top-level frontmatter fields while formatting rules handle quote/list style.

## Recommended design

### 1. Add schemas to the new standard bundle

```
standards/usage-documentation-site/
  schemas/
    mkdocs-usage-site.schema.json
    tool-feedback-issue-form.schema.json
```

Also ship copies in the adopt bundle if the consuming repo should have local editor support:

```
src/project_standards/bundles/usage-documentation-site/
  schemas/
    mkdocs-usage-site.schema.json
    tool-feedback-issue-form.schema.json
```

Or keep the schema central and reference it via the installed package. Local copies are better for offline editor validation and version-pinned repo behavior.

### 2. Keep them narrow

Do **not** try to model every possible MkDocs setting.

The schema should validate the **standard’s required subset**, not the entire MkDocs configuration language. MkDocs itself can validate MkDocs-specific behavior during:

```Bash
uv run mkdocs build --strict -f docs/usage/mkdocs.yml
```

Your schema should catch standard drift earlier, such as:

```YAML
docs_dir: content
site_dir: .site
strict: true
plugins:
  - search
  - tags:
      tags_allowed:
        - cli
        - usage
        - reference
```

### 3. Add a validator command only if it stays small

A good future command would be:

```Bash
uv run project-standards validate usage-site
```

or, less ideal but simpler:

```Bash
uv run project-standards usage-site validate
```

It would check:

```
docs/usage/mkdocs.yml
.github/ISSUE_TEMPLATE/tool-feedback.yml
docs/usage/content/assets/feedback-links.css
docs/usage/content/assets/feedback-links.js
docs/usage/.site/ is ignored
```

But for v1, you could simply make this part of the adoption checklist and CI examples, not a full CLI surface.

## Editor support

Add an optional VS Code/YAML Language Server mapping fragment:

```JSON
{
  "yaml.schemas": {
    "./standards/usage-documentation-site/schemas/mkdocs-usage-site.schema.json": "docs/usage/mkdocs.yml",
    "./standards/usage-documentation-site/schemas/tool-feedback-issue-form.schema.json": ".github/ISSUE_TEMPLATE/tool-feedback.yml"
  }
}
```

YAML Language Server supports associating local or remote schemas with glob patterns through `yaml.schemas`; modelines are also supported. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/redhat-developer/yaml-language-server)

## My recommendation

Add JSON schemas for:

```
docs/usage/mkdocs.yml
.github/ISSUE_TEMPLATE/tool-feedback.yml
```

Do **not** schema every YAML file.

Do **not** replace MkDocs strict build with schema validation.

The validation stack should be:

```
JSON Schema        = standard contract shape
MkDocs strict build = actual site correctness
Markdown/frontmatter validators = page metadata and links
Prettier/markdownlint = physical formatting
```

That gives you drift control without turning the standard into a brittle reimplementation of every upstream YAML format.

---

**You:**

What about validation tools for the content pages themselves?

---

**ChatGPT:**

Yes. For the content pages, I would **not** rely only on MkDocs, markdownlint, or JSON Schema. I would define a layered validation model and eventually add a small `project-standards` validator for the site standard.

## Recommended validation stack

| Layer | Tool | Purpose | Mandatory? |
| --- | --- | --- | --- |
| Metadata | Existing Markdown Frontmatter validator | Ensures every usage page has canonical managed-document metadata. | **Yes** |
| Markdown structure | Markdown Tooling Standard / markdownlint / Prettier | Checks Markdown shape, headings, links, formatting, tables, code fences. | **Yes** |
| MkDocs site build | `mkdocs build --strict -f docs/usage/mkdocs.yml` | Validates nav, internal links, anchors, omitted files, Material plugins, and rendered site correctness. | **Yes** |
| Tag vocabulary | Material tags plugin `tags_allowed` | Fails build when pages use non-approved tags. | **Yes** |
| Site-standard structure | New `usage-documentation-site` validator | Checks required tree, required page set, tool-page taxonomy, page-role sections, forbidden drift patterns. | **Yes, eventually** |
| External links | `lychee` or similar | Checks external URLs and mail links. | Optional |
| Prose/style | Vale | Checks wording, terms, style guide, banned phrasing. | Optional/advisory |
| Semantic review | Agent checklist | Checks whether content is truly user-facing usage docs. | **Yes, but not deterministic** |

MkDocs already has useful validation controls: it can warn on omitted nav files, missing nav targets, broken links, anchors, absolute links, and unrecognized links, and those warnings become errors under `mkdocs build --strict`. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)MkDocs](https://www.mkdocs.org/user-guide/configuration/) Material’s tags plugin can enforce a predefined allowed tag list and stop the build if a page uses a tag outside it. [![](https://www.google.com/s2/favicons?domain=https://squidfunk.github.io&sz=128)GitHub Pages](https://squidfunk.github.io/mkdocs-material/plugins/tags/)

## Key point

A JSON Schema is good for `mkdocs.yml` and the GitHub issue-form YAML. It is **not enough** for Markdown content pages.

The body of a Markdown page is semi-structured prose. You can validate some structure, but not the actual intent. For example, a tool can check that `commands.md` has `## Invocation`, `## Options`, and `## Exit status`; it cannot reliably prove that the page excludes developer-only explanation or that the examples are genuinely useful.

So the right design is:

```
deterministic validation
  + advisory lint
  + semantic agent review
```

That matches the pattern already used by the Project Specification Standard, which distinguishes deterministic structural validation from a semantic review layer an agent performs after structure checks pass.

## What I would add to the new standard

Add a future command group:

```Bash
project-standards usage-site validate
project-standards usage-site lint
```

or, if you prefer shorter names:

```Bash
project-standards usage validate
project-standards usage lint
```

I would probably use **`usage-site`** to avoid ambiguity with generic “usage” output.

## `usage-site validate`: hard failures

This command should be deterministic and conservative. It should fail only on things that are clearly violations.

### 1. Required path layout

Validate that these exist:

```
docs/usage/mkdocs.yml
docs/usage/content/index.md
docs/usage/content/start-here.md
docs/usage/content/tools/index.md
docs/usage/content/workflows/index.md
docs/usage/content/reference/index.md
docs/usage/content/troubleshooting/index.md
docs/usage/content/glossary.md
docs/usage/content/assets/feedback-links.css
docs/usage/content/assets/feedback-links.js
.github/ISSUE_TEMPLATE/tool-feedback.yml
```

Validate that this is ignored:

```
docs/usage/.site/
```

### 2. MkDocs config contract

Validate `docs/usage/mkdocs.yml` against the usage-site schema:

```
docs_dir: content
site_dir: .site
strict: true
theme.name: material
plugins includes search
plugins includes tags
tags_allowed matches canonical vocabulary
extra_css includes assets/feedback-links.css
extra_javascript includes assets/feedback-links.js
validation is strict enough
```

MkDocs itself remains the final site-build validator, but a schema catches drift before build time.

### 3. Required page taxonomy

Validate each tool directory.

For every:

```
docs/usage/content/tools/<tool-name>/
```

require:

```
index.md
quickstart.md
usage.md
commands.md
examples.md
troubleshooting.md
```

That page set should be standard unless a repo-local ADR records a deviation.

### 4. Navigation coverage

Validate that every intended content page is represented in `mkdocs.yml` navigation.

MkDocs can warn about omitted files; the standard validator should turn the site standard’s policy into a clearer failure:

```
docs/usage/content/tools/foo/examples.md exists but is not in nav
```

### 5. Canonical frontmatter

Validate that every rendered usage page has canonical frontmatter, not minimal MkDocs-only front matter.

At minimum, require the existing frontmatter validator to pass. The standard-specific validator can add usage-site expectations:

```YAML
consumer: 'user'
doc_type: 'index' | 'reference' | 'runbook' | 'concept'
status: 'active' | 'stub' | 'review'
```

Do **not** invent a new page metadata schema unless the existing one proves insufficient.

### 6. Page-role section checks

Hard-check basic required sections by filename.

Example:

| Page | Required sections |
| --- | --- |
| `index.md` | `# <Tool Name>`, `## When to use it`, `## When not to use it`, `## Inputs`, `## Outputs`, `## Next` |
| `quickstart.md` | `## Prerequisites`, `## Run the tool`, `## Expected result`, `## Next` |
| `usage.md` | At least one task-oriented `##` section |
| `commands.md` | `## Invocation`, `## Options`, `## Exit status` |
| `examples.md` | At least one example section with command/input and expected result |
| `troubleshooting.md` | At least one symptom section with `### Symptom`, `### Likely cause`, `### Fix` |
| global `glossary.md` | A glossary structure, preferably `## Term` sections |

Keep this modest. Do not overfit every page into a rigid template.

### 7. Link-style rules

Fail on:

```
[[wikilinks]]
links to generated .html files
absolute local repo paths
links into docs/usage/.site/
```

Allow:

```
relative Markdown links to .md files
normal external URLs
mailto links
same-page anchors
```

MkDocs handles link correctness well under strict mode, but the custom validator can enforce house style.

### 8. Feedback contract

Validate that:

```
feedback-links.js exists
feedback-links.css exists
tool-feedback.yml exists
issue-form field IDs are unchanged
feedback JS targets h2/h3 only
```

This is important because the feedback links depend on exact issue-form field IDs.

## `usage-site lint`: advisory warnings

This should produce warnings, not hard failures by default.

Warn on patterns that usually indicate drift out of user-facing scope:

```
Implementation details
Architecture
Internal API
Parser internals
Agent notes
TODO
ADR
Refactor
Test fixture
Mock
Class diagram
Module layout
```

But do not hard-fail these words. A user-facing troubleshooting page might legitimately say “internal error” or “implementation-defined behavior.” Use warnings so an agent reviews the context.

Also warn on weak usage-doc patterns:

```
page has no examples
command page has options but no defaults
destructive command lacks safety warning
troubleshooting page has symptoms but no fixes
quickstart is longer than a practical quickstart
code block has no language
```

## Existing tools to reuse

### MkDocs strict build

Mandatory:

```Bash
uv run mkdocs build --strict -f docs/usage/mkdocs.yml
```

MkDocs validation already covers missing nav targets, omitted files, broken internal links, anchors, absolute links, and unrecognized links when configured strictly. [![](https://www.google.com/s2/favicons?domain=https://www.mkdocs.org&sz=128)MkDocs](https://www.mkdocs.org/user-guide/configuration/)

### Material tags plugin

Mandatory through `tags_allowed`.

Material’s tags plugin reads tags from page front matter and can stop the build if a page references a tag outside the allowed list. [![](https://www.google.com/s2/favicons?domain=https://squidfunk.github.io&sz=128)GitHub Pages](https://squidfunk.github.io/mkdocs-material/plugins/tags/)

### markdownlint-cli2

Keep it under the existing Markdown Tooling Standard. It is already a good fit for Markdown/CommonMark structural linting, supports config-driven use, globs, `--fix`, and config files such as `.markdownlint.json` / `.markdownlint-cli2.jsonc`. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/DavidAnson/markdownlint-cli2)

### Vale

Vale is useful but should be optional. It is a prose linter: it brings code-like linting to prose and can enforce a writing style guide. [![](https://www.google.com/s2/favicons?domain=https://vale.sh&sz=128)vale.sh](https://vale.sh/docs/)

I would not make Vale mandatory in v1. It is powerful, but style rules can become noisy and subjective. Add it later if you want controlled terminology like “use ‘tool’ not ‘utility’” or “avoid implementation-facing terms in user docs.”

### External link checker

Optional. `lychee` is a good candidate because it checks broken hyperlinks and email addresses in Markdown, HTML, websites, and more. [![](https://www.google.com/s2/favicons?domain=https://github.com&sz=128)GitHub](https://github.com/lycheeverse/lychee)

I would keep this optional because external link checks are flaky in CI unless you manage retries, timeouts, and ignored domains.

## Proposed validation command stack

For a repo adopting the site standard:

```Bash
uv run project-standards validate --config .project-standards.yml
uv run project-standards usage-site validate
uv run mkdocs build --strict -f docs/usage/mkdocs.yml
npx markdownlint-cli2 "docs/usage/content/**/*.md"
```

Optional:

```Bash
vale docs/usage/content
lychee docs/usage/content/**/*.md
```

## What should be in v1

For the first version of the standard, I would make these mandatory:

```
canonical frontmatter validation
markdownlint/Prettier via Markdown Tooling
mkdocs build --strict
Material tags_allowed
usage-site validate for path/layout/page taxonomy
agent semantic review checklist
```

I would make these optional:

```
Vale
external link checker
spell checker
readability scoring
custom prose style gates
```

## Bottom line

Add a **standard-specific content validator**, but keep it deterministic and narrow.

The content-page validation model should be:

```
Markdown Frontmatter validator
  validates page metadata

Markdown Tooling
  validates Markdown structure and formatting

MkDocs strict build
  validates site, nav, links, anchors, tags, rendering

usage-site validate
  validates this standard’s page taxonomy and repo layout

usage-site lint + agent review
  catches user-facing scope drift
```

That gives you strong drift prevention without pretending a parser can fully understand whether prose is appropriately user-facing.

---

**You:**

I’ll take everything that we have decided as well as any open items that need to be addressed in the future and combine them into a comprehensive spec file for this new standard. You may use a separate files for different sections or domains of the spec with a master spec page for coordination between them so that no one file gets too long to be manageable

---

**ChatGPT:**

I’ll package this as an implementer-ready spec bundle, not another narrative answer: a master coordination spec plus focused companion specs for standard text, adoption artifacts, validation, and compatibility changes.

Created the spec bundle as Markdown files plus a ZIP.

Main download:

Individual files:

The bundle is structured so an implementation agent can start with the master spec, then work through standard text, adoption artifacts, validation, compatibility/migration, and open decisions without any one file becoming too large.

---

**You:**

GitHub I just moved this conversation into the project standards project. Also, please see the GitHub repository under my organization called project standards. Then revisit the specification from above using the lens of creating this as a distributor project standard.

---

**ChatGPT:**

I’ll reframe this as a standards-repo integration review: turning the drafted usage-docs spec into a distributable `project-standards` bundle with registry, adopt, validation, versioning, and compatibility behavior.

Updated the spec bundle to treat `usage-documentation-site` as a **distributable `project-standards` standard**, not just a per-repo adoption document.

The key repo-specific framing change is that this now follows the existing standards-bundle model: `standards/<standard-id>/README.md`, `adopt.md`, optional `templates/`, `examples/`, and `resources/`. That convention is already explicit in `project-standards`. I also tightened the implementation requirements around registry/adopt parity, because the CLI currently treats the registry’s version-tracked standards as the source for drift checks and fails if bundles and registry IDs disagree.

## Updated artifacts

New distributor-focused addendum:

Updated coordination files:

## What changed

I added a new file, `06-distributor-standard-addendum.md`, that reframes the implementation as a **standards-repo distribution task**. It now distinguishes:

| Layer | Meaning |
| --- | --- |
| Distributor repository | `L3DigitalNet/project-standards` |
| Consuming repository | Any repo adopting the standard |
| Standards bundle | `standards/usage-documentation-site/` |
| Adopt bundle | `src/project_standards/bundles/usage-documentation-site/` |
| Copy-adopt artifacts | Files seeded into consuming repos |
| Fragment artifacts | Repo-specific snippets for `.project-standards.yml`, `.gitignore`, agent instructions, etc. |

I also updated the master spec to reference the new addendum and added acceptance criteria for distributor behavior: `project-standards list`, `project-standards adopt usage-documentation-site --dry-run`, registry integration, versioning integration, and compatibility amendments.

The open-items file now includes additional distributor-specific items:

- whether to convert the planning bundle into a conformant Project Specification artifact;
- distributor release classification;
- whether to ship a copy-adopt usage-docs workflow;
- whether to dogfood by migrating the existing `docs/usage.md`;
- where local schema copies should live.

## Main architectural correction

The new standard should be implemented as a **copy-adopted standard with a contract-version marker**, similar in distribution posture to Python Tooling, Markdown Tooling, and CLI Documentation. If a dedicated validator ships, it should be explicit through `project-standards usage-site validate`, not silently inherited by unrelated repos.

The spec now emphasizes that adding the standard requires coordinated changes to:

```
standards/usage-documentation-site/
src/project_standards/bundles/usage-documentation-site/
src/project_standards/schemas/registry.json
src/project_standards/registry.py
src/project_standards/cli.py
src/project_standards/validate_frontmatter.py
standards/README.md
meta/versioning.md
.project-standards.yml
tests/
```

## Conflicts preserved as implementation requirements

The addendum keeps the important compatibility warnings from the review.

First, rendered usage pages should use canonical Markdown Frontmatter, because managed documents require the full minimal field set, not MkDocs-only `title` / `description` / `tags`. The schema also rejects unknown top-level properties and requires the canonical core fields.

Second, `cli-documentation` still currently defines `docs/usage.md` as the Packaged-profile usage reference, while the new site standard wants `docs/usage/`. The revised spec now treats this as a required compatibility amendment: the site standard owns **location/navigation/site behavior**, while `cli-documentation` continues to own **CLI command-reference substance**.

Third, local adoption ADRs stay under `docs/decisions/`; the usage-site standard must not introduce `docs/usage/governance/`.

## Bottom line

The spec is now positioned for implementation as a real `project-standards` distributable standard: registered, adoptable, versioned, tested, and compatible with the existing standards ecosystem rather than just a standalone instruction packet.

---

**You:**

Yes, make all the documents conformant to the specification standard. Also the project standards repository must dog food every standard that it governs as demonstration and proof of interoperability without conflict also as an example. So yes, the project standards will adopt this standard.

---

**ChatGPT:**

I’ll revise the spec bundle into a Project Specification Standard-conformant package, regenerate the ZIP, and make project-standards dogfooding a first-class acceptance requirement.

I confirmed the current bundle needs Project Specification frontmatter and structure, so I’m making the master spec coordinate conformant child spec slices.

Done. I converted the bundle into a **Project Specification Standard–conformant spec set** and regenerated the ZIP.

The bundle now uses the Project Spec frontmatter shape (`spec_id`, `status`, `profile`, `owner`, `implementer`, `related`, etc.) required by the templates. The Standard profile’s required structure, numbered sections, appendices, omission notes, ID prefixes, and traceability model are reflected across the child specs; the index is now a Light-profile spec. The Project Spec templates define that frontmatter shape and profile structure. The Light profile used for the bundle index follows the Project Spec Light template pattern.

I also made the dogfood requirement explicit: **`L3DigitalNet/project-standards` must adopt `usage-documentation-site` itself before the new standard is considered complete.** That is now represented in the master spec, the distributor/dogfood spec, and the bundle index.

I also treated the existing standards as constraints: Python Tooling’s verification-gate model, Markdown Frontmatter’s managed-document model, and Markdown Tooling’s formatter/linter model remain compatibility boundaries.

Download:

Individual files:

I ran a local structural sanity check over the bundle for frontmatter key order, valid `SPEC-` IDs, profile sections, omitted-section notes, required appendices, allowed ID prefixes, ID widths, and Markdown table shape. I did **not** run the repository’s packaged `project-standards spec validate` command inside this sandbox.
