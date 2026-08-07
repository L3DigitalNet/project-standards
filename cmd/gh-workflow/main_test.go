package main

import (
	"strings"
	"testing"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
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
		"new":     false,
		"set":     false,
		"close":   false,
		"reopen":  false,
		"check":   false,
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

// The reproducible build stamps the version with `-ldflags "-X main.version=..."`, which
// can only name a symbol in this package — and naming one that nothing reads links
// cleanly and changes nothing. This test is the link between the flag's target and the
// header every generated file carries.
func TestVersionStampReachesTheLedgerHeader(t *testing.T) {
	// Package state, so this one cannot be parallel.
	originalVersion, originalStamp := version, render.Version
	t.Cleanup(func() { version, render.Version = originalVersion, originalStamp })

	version = "9.9.9-stamped"
	stampVersion()

	if render.Version != version {
		t.Fatalf("render.Version = %q after stamping, want %q", render.Version, version)
	}
	ledger := render.Ledger(render.NewSnapshot("L3DigitalNet/example-repo", time.Now().UTC(), nil, nil))
	if !strings.Contains(ledger, version) {
		t.Errorf("the ledger header does not carry the stamped version %q:\n%s", version, ledger)
	}
}
