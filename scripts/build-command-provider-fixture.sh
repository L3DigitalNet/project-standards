#!/usr/bin/env bash
# Canonical reproducible build for the synthetic command-provider ABI fixture.
#
# The fixture is committed as payload bytes so end-to-end tests execute the same reviewed
# linux/amd64 artifact that package validation authenticates. The shared build library
# owns the pinned toolchain and byte-comparison contract; this script owns only the
# fixture source package and committed destination.
#
# Usage:
#   scripts/build-command-provider-fixture.sh            # rebuild in place
#   scripts/build-command-provider-fixture.sh --verify   # rebuild and byte-compare

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUILD_SCRIPT_NAME="scripts/build-command-provider-fixture.sh"

# This path is named by the synthetic payload manifest and both Makefile binary targets.
# Moving one endpoint without the others would leave a green source build disconnected
# from the bytes exercised by the command-provider acceptance tests.
ARTIFACT_OUTPUT_PATH="tests/fixtures/command-provider/standards/command-provider-fixture/versions/1.0/bin/command-provider-fixture"
ARTIFACT_PACKAGE="./cmd/command-provider-fixture"
ARTIFACT_LDFLAGS="-buildid="

# shellcheck source=scripts/lib/go-reproducible-build.sh
source "$REPO_ROOT/scripts/lib/go-reproducible-build.sh"

go_artifact_main "$@"
