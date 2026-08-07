package main

import (
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
)

// The binary's subcommands arrive through blank imports, which nothing else exercises:
// a dropped import would still compile and still pass every package test, and only show
// up as a missing subcommand at runtime. This test is that missing link.
func TestSubcommandsAreWired(t *testing.T) {
	t.Parallel()

	want := map[string]bool{
		"audit":   false,
		"ledger":  false,
		"summary": false,
		"receipt": false,
	}
	for _, cmd := range cli.Commands() {
		if _, expected := want[cmd.Name]; expected {
			want[cmd.Name] = true
		}
		if cmd.Summary == "" {
			t.Errorf("subcommand %q has no summary; `gh-workflow help` would list it blank", cmd.Name)
		}
	}
	for name, wired := range want {
		if !wired {
			t.Errorf("subcommand %q is not registered in the binary", name)
		}
	}
}
