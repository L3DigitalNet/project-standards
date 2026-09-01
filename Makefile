GO_FILES := $(shell find . -type f -name '*.go' -not -path './vendor/*' -not -path './.tools/*')
GO_PACKAGES := $(shell go list ./... 2>/dev/null)
GOLANGCI_LINT := .tools/bin/golangci-lint
GOLANGCI_LINT_VERSION := v2.12.2

.PHONY: go-tools go-format go-format-check go-vet go-lint go-test go-build go-audit go-mod-check go-binary go-verify-binary go-verify-binary-stamped go-check handoff-validate handoff-drift-check githooks release-reconcile release-golden

# Installed with `go install` rather than the upstream install.sh: the module path and
# version go through Go's checksum database, so the bytes we execute are verified against
# a transparency log. Piping install.sh from a mutable Git tag to `sh` verified nothing —
# a retagged or compromised raw.githubusercontent response executed as root-capable shell.
# The trade-off is upstream's documented one: a `go install` build is slower and may lack
# embedded version metadata. Output path stays .tools/bin so go-lint and CI are unchanged.
go-tools:
	mkdir -p .tools/bin
	GOBIN=$(CURDIR)/.tools/bin go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@$(GOLANGCI_LINT_VERSION)

go-format:
	@if [ -n "$(GO_FILES)" ]; then gofmt -w $(GO_FILES); fi

go-format-check:
	@if [ -n "$(GO_FILES)" ]; then \
		files="$$(gofmt -l $(GO_FILES))"; \
		if [ -n "$$files" ]; then printf '%s\n' "$$files"; exit 1; fi; \
	fi

go-vet:
	@if [ -n "$(GO_PACKAGES)" ]; then go vet ./...; else echo "No Go packages yet; vet skipped."; fi

go-lint: $(GOLANGCI_LINT)
	@if [ -n "$(GO_PACKAGES)" ]; then $(GOLANGCI_LINT) run ./...; else echo "No Go packages yet; lint skipped."; fi

$(GOLANGCI_LINT):
	$(MAKE) go-tools

go-test:
	@if [ -n "$(GO_PACKAGES)" ]; then go test -race -cover ./...; else echo "No Go packages yet; tests skipped."; fi

go-build:
	@if [ -n "$(GO_PACKAGES)" ]; then go build ./...; else echo "No Go packages yet; build skipped."; fi

go-audit:
	@if [ -n "$(GO_PACKAGES)" ]; then go tool govulncheck ./...; else echo "No Go packages yet; vulnerability scan skipped."; fi

go-mod-check:
	go mod tidy -diff
	go mod verify

# Payloads ship these binaries as committed bytes, so the source in this commit and the
# committed binaries must never diverge (spec NFR-005). The rebuild-compare runs here in
# the Go gate rather than in reconcile (plan decision D-004): consumers get bytes only,
# and this repository owns the proof that they match reviewed source.
#
# Every committed Go artifact belongs in both lists. A binary built but not verified
# would let the payload drift from its source with a green gate.
go-binary:
	scripts/build-gh-workflow.sh
	scripts/build-agent-handoff-session-start.sh
	scripts/build-command-provider-fixture.sh

go-verify-binary:
	scripts/build-gh-workflow.sh --verify
	scripts/build-agent-handoff-session-start.sh --verify
	scripts/build-command-provider-fixture.sh --verify

# What `go-check` actually depends on: the same proof, skipped when the content key in
# scripts/go-verify-stamp.sh says nothing it depends on has moved since it last passed
# (#227 E3 item 8 — three cold `go build` runs on every gate, almost always over
# unchanged bytes). `go-verify-binary` stays available as the unconditional target.
#
# Fail-closed by construction: only a clean `check` (exit 0) skips. A missing stamp, a
# stale stamp, and an indeterminate key (exit 2) all run the proof, so a fresh checkout,
# CI, and a newly synced remote workspace verify rather than trust. The stamp is written
# only after the proof passes, and never when it fails, so a red gate cannot license a
# skip on the next run.
#
# GO_VERIFY_FORCE=1 runs it regardless of the stamp — the release runbook's post-publish
# reproducibility proof (R11) must be an unconditional rebuild-and-compare, not a cache hit.
go-verify-binary-stamped:
	@if [ "$${GO_VERIFY_FORCE:-}" = "1" ]; then \
		echo "go-verify-binary: GO_VERIFY_FORCE=1 — running the reproducibility proof unconditionally"; \
		$(MAKE) --no-print-directory go-verify-binary && scripts/go-verify-stamp.sh write; \
	elif scripts/go-verify-stamp.sh check; then \
		echo "go-verify-binary: skipped — Go source, build scripts, and committed artifacts are unchanged since the last passing proof (GO_VERIFY_FORCE=1 to force)"; \
	else \
		$(MAKE) --no-print-directory go-verify-binary && scripts/go-verify-stamp.sh write; \
	fi

go-check: go-format-check go-mod-check go-vet go-lint go-test go-build go-audit go-verify-binary-stamped

# `make handoff-validate` and `make handoff-drift-check` are read-only grants in
# .agents/command-guard-allow.txt, and the guard matches a grant as a token PREFIX
# (agentguard command.go grantMatches). Without this refusal, `make handoff-validate
# go-tools` is admitted by the read-only grant while actually running an arbitrary
# second goal — go-tools reaches the network, go-format rewrites files, githooks
# rewrites .git/hooks. Refusing any co-invoked goal is what keeps the grant honest;
# it must stay in place for as long as those grants exist.
HANDOFF_TARGETS := handoff-validate handoff-drift-check
HANDOFF_EXTRA_GOALS = $(filter-out $(HANDOFF_TARGETS),$(MAKECMDGOALS))
handoff-goal-guard = $(if $(HANDOFF_EXTRA_GOALS),$(error handoff targets must be invoked alone; refusing co-invoked goal(s): $(HANDOFF_EXTRA_GOALS)))

# SINCE reaches the recipe through the environment and is never interpolated into the
# command line, so a value like `abc;id` cannot become a second shell command; the hex
# check below then rejects anything that is not a plausible Git OID before `uv run` sees
# it. Both halves are deliberate: the export removes the injection, the check keeps a
# typo from reaching the CLI as a silent no-op argument. Bounds are Git's own abbreviated
# (7) and full SHA-1 (40) lengths.
export SINCE

# The installed skill's agent-handoff CLI commands cannot resolve the catalog
# projection from the source checkout (exits 3, "installed catalog projection
# is unavailable") without the extracted candidate wheel on PYTHONPATH — see
# README "Developing this repository". These targets wrap that requirement so
# a fresh session doesn't have to rediscover it.
handoff-validate:
	@$(handoff-goal-guard)
	@if [ -n "$${SINCE:-}" ] && ! printf '%s' "$${SINCE}" | grep -Eq '^[0-9a-fA-F]{7,40}$$'; then \
		echo "SINCE must be a 7-40 character hex object id; refusing: $${SINCE}" >&2; exit 2; \
	fi
	@test -d build/wheel-runtime || { echo "build/wheel-runtime missing: see README 'Developing this repository'"; exit 1; }
	PYTHONPATH=$(CURDIR)/build/wheel-runtime uv run project-standards agent-handoff validate --repo . $${SINCE:+--since "$${SINCE}"}

handoff-drift-check:
	@$(handoff-goal-guard)
	@test -d build/wheel-runtime || { echo "build/wheel-runtime missing: see README 'Developing this repository'"; exit 1; }
	PYTHONPATH=$(CURDIR)/build/wheel-runtime uv run project-standards agent-handoff drift-check --repo .

# Release-train steps R4 and R5 from the release runbook, which was their only
# sequencer (#227 E3 item 7). Both are release-time mutations of the dogfooded control
# plane and the synthetic golden fixture; nothing else invokes them.
#
# RELEASE reaches the recipe through the environment and is never interpolated into the
# command line — the same rule as SINCE above, for the same reason — and the semver check
# below rejects anything that is not a canonical X.Y.Z before `uv run` sees it.
export RELEASE

# Two `reconcile --apply` passes are required by design, not defensive repetition: when
# the installed catalog is stale, pass 1 plans only the catalog refresh and pass 2 moves
# the packages (lesson 2026-08-26-reconcile-cp-verify-hides-missing-locked-target). Pass 2
# must report no mutations; if it does not, stop and diagnose rather than running a third.
#
# The closing grep is the observable: both files must read the new release. When reconcile
# instead refuses with PC-RELEASE-PAYLOAD-MUTATED, PC-CATALOG-DIGEST-REPLACED,
# CP-CONTROL-STATE, or CP-MODIFIED-MANAGED, the cause is usually a `.standards/catalog.toml`
# rendered mid-train, not a payload defect; the runbook's three-step restore is the recovery
# and is deliberately not automated here, because each step is a judgment call.
release-reconcile:
	@test -d build/wheel-runtime || { echo "build/wheel-runtime missing: see README 'Developing this repository'"; exit 1; }
	PYTHONPATH=$(CURDIR)/build/wheel-runtime uv run project-standards reconcile --apply
	PYTHONPATH=$(CURDIR)/build/wheel-runtime uv run project-standards reconcile --apply
	PYTHONPATH=$(CURDIR)/build/wheel-runtime uv run project-standards validate
	grep -n '^release' .standards/catalog.toml .standards/lock.toml

# `--output` is resolved relative to `--root`, not to the working directory
# (`_resolved_output`, src/project_standards/package_contract/cli.py, which refuses any
# path escaping the root). Passing the repo-relative path is the recurring trap: it either
# fails or, worse in an earlier form, renders the REAL repository catalog over the
# synthetic fixture. That is why `expected/catalog.toml` is spelled relative here.
#
# The diff is the proof the render came from the synthetic fixture: exactly two lines move,
# `release` and the derived `digest`. Any package stanza moving means `--root` was wrong.
release-golden:
	@printf '%s' "$${RELEASE:-}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$$' || { echo "release-golden requires RELEASE=X.Y.Z" >&2; exit 2; }
	@test -d build/wheel-runtime || { echo "build/wheel-runtime missing: see README 'Developing this repository'"; exit 1; }
	PYTHONPATH=$(CURDIR)/build/wheel-runtime uv run project-standards standards render-consumer-catalog --root tests/fixtures/package_contract/valid/full --catalog-major "$${RELEASE%%.*}" --output expected/catalog.toml --tool-release "$${RELEASE}"
	git diff -- tests/fixtures/package_contract/valid/full/expected/catalog.toml

# The tracked `main` commit guard, installed into the common .git/hooks. Also run
# by scripts/bootstrap-worktree.sh; this target exists for a checkout that was
# never bootstrapped. Deliberately not a scripts/verify.sh dependency: a gate that
# rewrites the developer's hooks as a side effect of running tests is a surprise,
# and verify.sh must stay runnable on the rexec worker, which has no hooks to own.
githooks:
	scripts/install-githooks.sh
