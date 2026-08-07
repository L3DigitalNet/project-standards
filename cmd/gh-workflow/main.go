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

	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/audit"
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

func main() {
	os.Exit(cli.Run(context.Background(), cli.DefaultEnv(), os.Args[1:]))
}
