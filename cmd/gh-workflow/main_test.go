package main

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
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
		"summary": false,
		"receipt": false,
		"new":     false,
		"set":     false,
		"close":   false,
		"reopen":  false,
		"check":   false,
		"ready":   false,
		"merge":   false,
	}
	if len(want) != 10 {
		t.Fatalf("the IR-005 surface is ten subcommands; this test names %d", len(want))
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
// one surface that reports the version.
//
// It proves the second half of the chain only: that whatever `version` holds reaches
// `help`. Whether the linker's write survives package initialization is unobservable
// from inside a process that was never stamped, and is proven by the build below.
func TestVersionStampReachesTheHelpOutput(t *testing.T) {
	// Package state, so this one cannot be parallel.
	originalVersion, originalStamp := version, cli.Version
	t.Cleanup(func() { version, cli.Version = originalVersion, originalStamp })

	version = "9.9.9-stamped"
	stampVersion()

	if cli.Version != version {
		t.Fatalf("cli.Version = %q after stamping, want %q", cli.Version, version)
	}
	out := &strings.Builder{}
	env := cli.DefaultEnv()
	env.Stdout = out
	if got := cli.Run(context.Background(), env, []string{"help"}); got != cli.ExitOK {
		t.Fatalf("Run(help) = %d, want %d", got, cli.ExitOK)
	}
	if !strings.Contains(out.String(), version) {
		t.Errorf("`help` does not carry the stamped version %q:\n%s", version, out)
	}
}

// ldflagsProbe is the version the linker is asked to write into a stamped build of this
// package. No source file contains it, so a process that reports it can only have been
// given it by the linker.
const ldflagsProbe = "0.0.0-ldflags-probe-4d1f0c8a"

// TestLdflagsVersionStampIsLinkerEffective runs the exact command the reproducible build
// runs — `go build -ldflags "-X main.version=..."` — and then asks the stamped binary
// what version it reports.
//
// The distinction that makes this test necessary: `-X` writes its value into the
// variable's initial data whether or not the declaration qualifies, so the string lands
// in every stamped binary and proves nothing on its own. What decides the outcome is
// whether package initialization then overwrites it. Initialized from a constant the
// linker wins; initialized from another package's variable, initialization wins —
// silently, with the build, the flag, and every in-process test still green while every
// stamped build reports the default. Only a stamped process can tell the two apart.
//
// Before payload 1.5 this needed a second link into this package's own test binary,
// because no offline subcommand printed the version — the surface that read a live
// repository was the removed generated-document subcommand. `help` now prints it, so
// one link and one offline invocation cover the whole claim.
func TestLdflagsVersionStampIsLinkerEffective(t *testing.T) {
	t.Parallel()

	if testing.Short() {
		t.Skip("linking two binaries is too slow for a -short run")
	}
	goTool, err := exec.LookPath("go")
	if err != nil {
		t.Skipf("no go toolchain on PATH to link with: %v", err)
	}

	// GOPROXY=off keeps a cache miss a build failure rather than a module download: the
	// suite is offline by contract and the module has no dependencies to fetch.
	runGo := func(args ...string) string {
		t.Helper()

		cmd := exec.Command(goTool, args...) //nolint:gosec // G204: the resolved toolchain path with this test's own arguments.
		cmd.Env = append(os.Environ(), "GOPROXY=off")
		out, runErr := cmd.CombinedOutput()
		if runErr != nil {
			t.Fatalf("go %s error = %v\n%s", strings.Join(args, " "), runErr, out)
		}
		return string(out)
	}

	dir := t.TempDir()
	binary := filepath.Join(dir, "gh-workflow")
	runGo("build", "-o", binary, "-ldflags", "-X main.version="+ldflagsProbe, ".")
	helpOut, err := exec.Command(binary, "help").CombinedOutput() //nolint:gosec // G204: a binary this test just built into its own temp directory.
	if err != nil {
		t.Fatalf("the stamped binary failed to run `help`: %v\n%s", err, helpOut)
	}
	if !strings.Contains(string(helpOut), "summary") {
		t.Errorf("the stamped binary's `help` does not list its subcommands:\n%s", helpOut)
	}
	if !strings.Contains(string(helpOut), ldflagsProbe) {
		t.Errorf("the stamped binary reports a version other than the linked %q; the `-X` value "+
			"was overwritten, so `-ldflags \"-X main.version=...\"` cannot stamp this build:\n%s",
			ldflagsProbe, helpOut)
	}
}
