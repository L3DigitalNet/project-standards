---
bug_id: '002'
date: '2026-06-12'
title: 'markdownlint cannot see malformed GFM tables — green CI masks broken rendering'
services: '[ci, markdownlint, docs]'
status: 'fixed'
---

# 002 — markdownlint is blind to malformed GFM tables

**Status:** fixed (python-tooling §8 table repaired in `79daeae`; an earlier instance fixed in round 3, `67a315d`).

## Symptom

A Markdown table renders as raw pipe-text on GitHub while the full lint gate (markdownlint-cli2 with MD055/MD056 enabled, Prettier `--check`) stays green. Found twice in `standards/python-tooling/README.md`.

## Root cause

Per GFM, a delimiter row whose cell count differs from the header row means the block is **never recognized as a table**. markdownlint's table rules (MD055 row style, MD056 column count) only fire on blocks the parser already accepted as tables — a malformed delimiter row makes the defect invisible to the exact rules meant to catch it. An unescaped `|` inside inline code (`` `T | None` ``) silently changes a row's cell count the same way. Prettier doesn't flag it either: it only reformats well-formed tables.

## Fix

Match the delimiter row's cell count to the header and escape pipes inside cells (`\|`). Verify by cell-counting the raw pipes, not by linting.

## Lesson (reusable gotcha)

- **Green markdownlint says nothing about table well-formedness.** When authoring or reviewing GFM tables, count cells in header vs delimiter rows manually (or render-preview); the linter cannot do it.
- Inline code containing `|` inside a table cell must use `\|` — backticks do not protect the pipe from the table parser.
