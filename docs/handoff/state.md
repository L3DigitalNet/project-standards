# Handoff State

## Current focus

- v5.17.0 is the ADR train: #127 as `adr` 1.5 (non-breaking), then #128's 21 items; bug 006 decision owed before #128 item 1.
- `github-workflow@1.0` is unpublished (`testing` at `6a6aaee3`), so its payload is amendable until it ships; plan §13 close-out.
- `gh-workflow set` cannot retype an existing issue; #131 needed `gh issue edit --type`. The fix rides the 1.0 amendment above; unfiled.
- #133 follow-ups #134–#137 are delivered and closed; run `scripts/family_preflight.py <id>` before adopting a family (conventions #19).
- Tail: T24–T29 (#62, #55; T24 ready), deferred #116, SPEC-GSF3 T1, Usage Doc Site V2 specs; owner: 1.12 legacy-digest residual.

## Active incidents

- `test_slow_provider_..._is_reaped` fails in the ordinary lane on a clean gate run; two neighbours fail only under load. Not a regression.
