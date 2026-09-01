GO_FILES := $(shell find . -type f -name '*.go' -not -path './vendor/*' -not -path './.tools/*')
GO_PACKAGES := $(shell go list ./... 2>/dev/null)
GOLANGCI_LINT := .tools/bin/golangci-lint
GOLANGCI_LINT_VERSION := v2.12.2

.PHONY: go-tools go-format go-format-check go-vet go-lint go-test go-build go-audit go-mod-check go-binary go-verify-binary go-check handoff-validate handoff-drift-check githooks

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

go-check: go-format-check go-mod-check go-vet go-lint go-test go-build go-audit go-verify-binary

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

# The tracked `main` commit guard, installed into the common .git/hooks. Also run
# by scripts/bootstrap-worktree.sh; this target exists for a checkout that was
# never bootstrapped. Deliberately not a scripts/verify.sh dependency: a gate that
# rewrites the developer's hooks as a side effect of running tests is a surprise,
# and verify.sh must stay runnable on the rexec worker, which has no hooks to own.
githooks:
	scripts/install-githooks.sh
