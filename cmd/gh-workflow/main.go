// Command gh-workflow is the packaged GitHub work-state tool the github-workflow skill
// invokes under the operator's existing `gh` authentication (spec FR-015, IR-002).
//
// This file is deliberately the whole main package: it owns process concerns only —
// context, exit code, and the blank imports that pull each self-registering subcommand
// into the binary. Adding a subcommand adds one import line here and one file in its own
// package; no dispatch table is edited.
package main

import (
	"context"
	"os"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"

	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/audit"
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/mutate"
)

// version is the tool version, overridable at link time with
// `-ldflags "-X main.version=..."`. It is declared here because that is the only symbol
// the flag can name, and it defaults to the package version rather than "dev" so an
// unstamped build still labels its output honestly.
var version = "1.0"

// stampVersion carries the linked version into the generated surfaces.
//
// Without this the ldflag would link cleanly and change nothing: render.Version is what
// the ledger header actually prints, and a stamp that never reaches it would make every
// generated file claim the default version regardless of which binary wrote it.
func stampVersion() {
	render.Version = version
}

func main() {
	stampVersion()
	os.Exit(cli.Run(context.Background(), cli.DefaultEnv(), os.Args[1:]))
}
