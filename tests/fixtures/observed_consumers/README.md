# Observed-consumer fixtures

This namespace holds byte-exact `.`-config files **recovered from real
consumer working trees**, not artifacts any release ever shipped. It is
deliberately separate from `tests/fixtures/legacy_releases/`, whose files are
the exact bytes a published project-standards release wrote. A file lives here
only when a consumer produced or hand-edited it locally and no release digest
matches it — the case the legacy-acceptance signatures must still recognize.

## `markdownlint-literal-cjk.json`

- **Digest:** `sha256:4c1c089d0552a6118f6a8b7d85bae1bd762da41d601d1c489bdb9143f6a2d548`
- **Recovered:** 2026-07-22 (5.8.0 FR-005 / issue #27).
- **Written by the consumer:** 2026-06-07, before the `adopt` CLI existed, so the
  bytes were produced by a hand-run editor/formatter rather than a payload write.
- **Byte form:** parsed-JSON-equal to the shipped `markdownlint.json` artifact
  (digest `sha256:51204b5170e47da3716d3870d36ef1eb4b28a27d7289c65f7f1457943c499793`)
  but serialized with **literal UTF-8 CJK punctuation** in string values instead
  of the shipped `\uXXXX` ASCII escapes. Same JSON, different encoding on disk —
  hence a distinct content digest that migration must accept as known legacy
  content rather than treat as a modified file.

No repository name, path, owner, or other identifying detail is recorded here or
in the fixture: only the digest, the two dates, and the byte-form description
needed to reproduce the acceptance behavior.
