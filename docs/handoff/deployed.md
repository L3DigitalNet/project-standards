# Deployed

**Last updated:** 2026-06-05

This repo is consumed as a versioned standard: downstream repos pin a `standards-ref` to a git tag and call the reusable workflow under `.github/workflows/`. "Deployed" here means published git refs on `main`.

| Ref | What it is | Status |
| --- | --- | --- |
| `v1.0.0`–`v1.0.2` | Initial standards + validator + reusable workflow | published on `main` |
| `v1.1.0` | optional `consumer` field; `schema_version` accepts `1.1` | published on `main` |
| `v1.2.0` | `standards/adoption.md`; pinning hardened; validator crash-safety | published on `main` |
| `v1` (moving) | tracks the newest release — currently `v1.2.0` (`2abea67`) | published on `main` |
| `1.3.0` | lint/format stack + MADR-4 ADR conventions + ADR section check | **pending on `testing`, unreleased** |
