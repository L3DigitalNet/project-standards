// Command session-start is the Agent Handoff SessionStart hook that managed harness
// registrations invoke directly.
//
// It ships to consumers as committed bytes inside the agent-handoff payload and is
// installed at <repo>/.agents/hooks/agent-handoff/session-start. The installed path is
// load-bearing — the hook derives its repository authority from it — so the artifact
// target in payload.toml, the build script's output path, and
// sessionstart.repositoryRoot's ancestor depth are one cross-file contract.
//
// This file owns process concerns only: argv, exit code, and the version stamp.
package main

import (
	"os"

	"github.com/L3DigitalNet/project-standards/internal/agenthandoff/sessionstart"
)

// version is the tool version, overridable at link time with
// `-ldflags "-X main.version=..."`. `-X` can only name a symbol in the main package, so
// the value is received here and copied into the package that reports it.
//
// The initializer must stay a constant. A non-constant initializer — sessionstart.Version
// itself, most temptingly — makes package initialization run after the linker's write and
// silently restore the default in every stamped build.
var version = sessionstart.DefaultVersion

func main() {
	sessionstart.Version = version
	os.Exit(sessionstart.Run(sessionstart.DefaultEnv(), os.Args[1:]))
}
