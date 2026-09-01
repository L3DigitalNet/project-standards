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

	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/admission"
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/audit"
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/mutate"
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// version is the tool version, overridable at link time with
// `-ldflags "-X main.version=..."`. It is declared here because that is the only symbol
// the flag can name, and it takes render's default rather than a literal of its own so an
// unstamped build labels its output honestly and there is one place to change when the
// package version moves.
//
// The initializer must stay a constant. `-X` writes the linker's value into this
// variable's initial data either way, but a non-constant initializer — cli.Version
// itself, most temptingly — makes package initialization run afterwards and overwrite it,
// which links cleanly, passes every in-process test, and leaves each stamped build
// reporting the default.
var version = cli.DefaultVersion

// stampVersion carries the linked version into the surface that reports it.
//
// Without this the ldflag would link cleanly and change nothing: cli.Version is what
// `gh-workflow help` actually prints, and a stamp that never reaches it would make every
// build report the default version regardless of which binary is running.
func stampVersion() {
	cli.Version = version
}

func main() {
	stampVersion()
	os.Exit(cli.Run(context.Background(), cli.DefaultEnv(), os.Args[1:]))
}
