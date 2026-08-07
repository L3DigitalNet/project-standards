package ghauth

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestCLITokenSourceSuccess(t *testing.T) {
	t.Parallel()

	src := &CLITokenSource{run: func(context.Context) (string, string, error) {
		return "gho_exampletoken\n", "", nil
	}}

	got, err := src.Token(context.Background())
	if err != nil {
		t.Fatalf("Token() error = %v, want nil", err)
	}
	if got != "gho_exampletoken" {
		t.Errorf("Token() = %q, want the trimmed token", got)
	}
}

func TestCLITokenSourceUnauthenticated(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name   string
		stdout string
		stderr string
		err    error
	}{
		{
			name:   "gh reports no authentication",
			stderr: "gh: To use GitHub CLI in a GitHub Actions workflow, set the GH_TOKEN environment variable.\n",
			err:    errors.New("exit status 1"),
		},
		{
			name:   "gh succeeds but prints nothing",
			stdout: "\n",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			src := &CLITokenSource{run: func(context.Context) (string, string, error) {
				return tc.stdout, tc.stderr, tc.err
			}}

			got, err := src.Token(context.Background())
			if err == nil {
				t.Fatalf("Token() = %q, want an unauthenticated error", got)
			}
			if !errors.Is(err, ErrUnauthenticated) {
				t.Errorf("Token() error = %v, want it to wrap ErrUnauthenticated", err)
			}
		})
	}
}

// IR-002: no credential material may leak into diagnostics. `gh auth token` writes the
// token to stdout, so stdout must never reach an error message.
func TestCLITokenSourceNeverEchoesStdout(t *testing.T) {
	t.Parallel()

	const secret = "gho_supersecretvalue"
	src := &CLITokenSource{run: func(context.Context) (string, string, error) {
		return secret, "credential store unavailable\n", errors.New("exit status 1")
	}}

	_, err := src.Token(context.Background())
	if err == nil {
		t.Fatal("Token() error = nil, want a failure")
	}
	if strings.Contains(err.Error(), secret) {
		t.Errorf("Token() error = %q, must not contain the token value", err)
	}
	if !strings.Contains(err.Error(), "credential store unavailable") {
		t.Errorf("Token() error = %q, want the gh stderr diagnostic", err)
	}
}
