GO_FILES := $(shell find . -type f -name '*.go' -not -path './vendor/*' -not -path './.tools/*')
GO_PACKAGES := $(shell go list ./... 2>/dev/null)
GOLANGCI_LINT := .tools/bin/golangci-lint
GOLANGCI_LINT_VERSION := v2.12.2

.PHONY: go-tools go-format go-format-check go-vet go-lint go-test go-build go-audit go-mod-check go-check

go-tools:
	mkdir -p .tools/bin
	curl --fail --location --silent --show-error \
		https://raw.githubusercontent.com/golangci/golangci-lint/$(GOLANGCI_LINT_VERSION)/install.sh \
		| sh -s -- -b .tools/bin $(GOLANGCI_LINT_VERSION)

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

go-check: go-format-check go-mod-check go-vet go-lint go-test go-build go-audit
