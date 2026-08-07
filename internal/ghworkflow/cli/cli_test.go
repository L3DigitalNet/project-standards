package cli_test

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
)

func init() {
	cli.Register(&cli.Command{
		Name:    "test-ok",
		Summary: "test double that succeeds",
		Run: func(_ context.Context, env *cli.Env, args []string) error {
			_, err := env.Stdout.Write([]byte("ok " + strings.Join(args, ",") + "\n"))
			return err
		},
	})
	cli.Register(&cli.Command{
		Name:    "test-fail",
		Summary: "test double that fails",
		Run: func(context.Context, *cli.Env, []string) error {
			return errors.New("boom")
		},
	})
	cli.Register(&cli.Command{
		Name:    "test-usage",
		Summary: "test double that reports a usage error",
		Run: func(context.Context, *cli.Env, []string) error {
			return cli.Usagef("bad flag %q", "--nope")
		},
	})
}

func testEnv() (*cli.Env, *bytes.Buffer, *bytes.Buffer) {
	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}
	return &cli.Env{Stdout: stdout, Stderr: stderr, WorkDir: "."}, stdout, stderr
}

func TestRunExitCodes(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name     string
		args     []string
		wantExit int
		wantOut  string
		wantErr  string
	}{
		{name: "no arguments", args: nil, wantExit: cli.ExitUsage, wantErr: "Usage"},
		{name: "help", args: []string{"help"}, wantExit: cli.ExitOK, wantOut: "Usage"},
		{name: "long help flag", args: []string{"--help"}, wantExit: cli.ExitOK, wantOut: "Usage"},
		{name: "unknown subcommand", args: []string{"nope"}, wantExit: cli.ExitUsage, wantErr: "unknown subcommand"},
		{name: "success", args: []string{"test-ok", "a", "b"}, wantExit: cli.ExitOK, wantOut: "ok a,b"},
		{name: "failure", args: []string{"test-fail"}, wantExit: cli.ExitFailure, wantErr: "boom"},
		{name: "usage error", args: []string{"test-usage"}, wantExit: cli.ExitUsage, wantErr: "bad flag"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			env, stdout, stderr := testEnv()

			got := cli.Run(context.Background(), env, tc.args)
			if got != tc.wantExit {
				t.Errorf("Run(%v) = %d, want %d (stderr: %s)", tc.args, got, tc.wantExit, stderr)
			}
			if tc.wantOut != "" && !strings.Contains(stdout.String(), tc.wantOut) {
				t.Errorf("stdout = %q, want it to contain %q", stdout, tc.wantOut)
			}
			if tc.wantErr != "" && !strings.Contains(stderr.String(), tc.wantErr) {
				t.Errorf("stderr = %q, want it to contain %q", stderr, tc.wantErr)
			}
		})
	}
}

func TestUsageListsRegisteredCommands(t *testing.T) {
	t.Parallel()

	env, stdout, _ := testEnv()
	if got := cli.Run(context.Background(), env, []string{"help"}); got != cli.ExitOK {
		t.Fatalf("Run(help) = %d, want %d", got, cli.ExitOK)
	}
	if !strings.Contains(stdout.String(), "test-ok") {
		t.Errorf("usage = %q, want it to list every registered subcommand", stdout)
	}
}

func TestRegisterRejectsDuplicates(t *testing.T) {
	t.Parallel()

	defer func() {
		if recover() == nil {
			t.Error("Register() with a duplicate name did not panic")
		}
	}()
	cli.Register(&cli.Command{Name: "test-ok", Run: func(context.Context, *cli.Env, []string) error { return nil }})
}

// IR-004 zero-argument default resolution: the tool is invoked from anywhere inside a
// consumer checkout and must find the delivered artifacts without flags.
func TestResolveRepoFileAscends(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	target := filepath.Join(root, cli.DefaultSchemaPath)
	if err := os.MkdirAll(filepath.Dir(target), 0o750); err != nil {
		t.Fatalf("MkdirAll() error = %v", err)
	}
	if err := os.WriteFile(target, []byte("issue_types:\n"), 0o600); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}
	nested := filepath.Join(root, "a", "b", "c")
	if err := os.MkdirAll(nested, 0o750); err != nil {
		t.Fatalf("MkdirAll() error = %v", err)
	}

	got, err := cli.ResolveRepoFile(nested, cli.DefaultSchemaPath)
	if err != nil {
		t.Fatalf("ResolveRepoFile() error = %v, want nil", err)
	}
	if got != target {
		t.Errorf("ResolveRepoFile() = %q, want %q", got, target)
	}
}

func TestResolveRepoFileNotFound(t *testing.T) {
	t.Parallel()

	_, err := cli.ResolveRepoFile(t.TempDir(), cli.DefaultPolicyPath)
	if err == nil {
		t.Fatal("ResolveRepoFile() error = nil, want a not-found failure")
	}
	if !strings.Contains(err.Error(), cli.DefaultPolicyPath) {
		t.Errorf("error = %q, want it to name the path it looked for", err)
	}
}

func TestParseOutputMode(t *testing.T) {
	t.Parallel()

	if got, err := cli.ParseOutputMode("human"); err != nil || got != cli.OutputHuman {
		t.Errorf("ParseOutputMode(human) = %q, %v", got, err)
	}
	if got, err := cli.ParseOutputMode("json"); err != nil || got != cli.OutputJSON {
		t.Errorf("ParseOutputMode(json) = %q, %v", got, err)
	}
	if _, err := cli.ParseOutputMode("yaml"); err == nil {
		t.Error("ParseOutputMode(yaml) error = nil, want a failure")
	}
}
