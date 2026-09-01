---
bug_id: '010'
date: '2026-09-01'
title: 'agent-handoff 1.15 and 1.16 shipped the byte-identical 1.14 session-start binary, so --version answered 1.14'
services: '[agent-handoff, go, packaging, release]'
status: 'fixed'
---

# 010 — agent-handoff 1.15/1.16 carry forward the 1.14 launcher

**Status:** fixed for 1.17 and later. The 1.14, 1.15, and 1.16 payload bytes are published and immutable, so those three versions permanently answer `agent-handoff session-start 1.14`; that is a recorded exception, not drift.

## Symptom

The committed `session-start` binaries for agent-handoff payloads 1.14, 1.15, and 1.16 are byte-identical — SHA-256 group `8b90…`, 3,906,258 bytes each — and all three report `agent-handoff session-start 1.14` from `--version`.

`--version` is documented, in both the build script and the family README, as the stale-launcher diagnostic: it exists so an operator can tell which package version installed the launcher sitting in a consumer repository. On 1.15 and 1.16 it answered a different question — which build produced the bytes — and answered it with a version the consumer never selected.

## Cause

`scripts/build-agent-handoff-session-start.sh` carries the artifact path and the version stamp as two literals. Both still named 1.14 while 1.15 and 1.16 were cut, because neither cut changed Go source: the payload directory was copied from its predecessor, the binary came along inside the copy, and nothing in the cut procedure required re-linking it.

Nothing detected this. Reproducibility is verified by `make go-verify-binary`, which rebuilds only the one path the script names, and the per-version contract tests asserted the payload's declared digest — which matched, because the carried-forward bytes were exactly the bytes the manifest declared.

## Consequence

No consumer behavior was wrong: the 1.14 launcher is functionally correct in 1.15 and 1.16, both of which changed nothing the launcher does. The cost is diagnostic. An investigator reading `1.14` from a launcher installed by a 1.16 selection sees what a genuinely stale installation looks like, and either chases a packaging defect that does not exist or — worse — dismisses a future real staleness report as this known artifact.

## Fix

Agent Handoff 1.17 (issues #229 and #235) re-links the launcher from the 1.17 path with `-X main.version=1.17`, and the build script now states the cut-time rule directly: every new payload version re-links the binary with its own stamp even when the Go source is unchanged, so two consecutive versions' bytes may differ by the stamp alone.

`tests/package_contract/test_agent_handoff_1_17.py` pins the rule against the catalog's **default** agent-handoff version rather than a literal, so a future cut that byte-copies its predecessor's launcher fails the contract instead of shipping a misleading stamp. Retained versions are deliberately unasserted — their bytes cannot change.

## Lesson

- **A carried-forward binary carries its stamp with it.** Copying a payload directory copies every build-time literal baked into the artifacts inside it; only re-linking updates them.
- **Assert a diagnostic against what it claims to answer.** The digest assertions were all green because they compared the artifact with its own manifest. Only executing the binary and comparing `--version` to the payload version tests the claim the diagnostic makes.
- **Pin such an invariant to the role, not the version.** Asserting "the default version's launcher reports the default version" survives every future cut; a test naming 1.17 would have to be remembered at the next one — which is precisely the step that failed here.
