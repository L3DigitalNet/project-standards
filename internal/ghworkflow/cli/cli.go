// Package cli is the gh-workflow command shell: the subcommand registry, the process
// environment every subcommand receives, exit-code classification, and the shared
// output-mode and path-resolution helpers.
//
// The registry is deliberately write-only from the outside. Each subcommand package
// registers itself from an init function, and cmd/gh-workflow pulls it in with a blank
// import, so adding a subcommand adds a file and one import line and never edits shared
// registration code. The nine subcommands of spec IR-004 land across several tasks;
// this shape is what keeps them from serializing behind one dispatch table.
package cli

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghauth"
)

// Process exit codes. Everything the operator can mistype is ExitUsage; everything the
// environment can get wrong — authentication, reachability, malformed inputs — is
// ExitFailure, which is the nonzero exit spec FR-016 requires for unmet preconditions.
const (
	ExitOK      = 0
	ExitFailure = 1
	ExitUsage   = 2
)

// Delivered locations of the package artifacts the tool reads. IR-004 requires the tool
// to find these with no arguments, so they are constants here rather than flag defaults.
const (
	DefaultSchemaPath = ".agents/skills/github-workflow/references/org-schema.yaml"
	DefaultPolicyPath = ".standards/packages/github-workflow/policy.toml"
)

// Command is one registered subcommand.
type Command struct {
	Name    string
	Summary string
	Run     func(ctx context.Context, env *Env, args []string) error
}

// Env is everything a subcommand may touch outside its own arguments. Streams,
// authentication, and the HTTP transport are all injected so the whole CLI is testable
// in-process, offline, and without a real `gh` login.
type Env struct {
	Stdout    io.Writer
	Stderr    io.Writer
	WorkDir   string
	Tokens    ghauth.TokenSource
	Transport http.RoundTripper
	BaseURL   string
}

// DefaultEnv returns the environment for a real process invocation.
func DefaultEnv() *Env {
	workDir, err := os.Getwd()
	if err != nil {
		// A working directory the process cannot name still resolves relative paths, so
		// this degrades to "." rather than aborting before any subcommand can report.
		workDir = "."
	}
	return &Env{
		Stdout:  os.Stdout,
		Stderr:  os.Stderr,
		WorkDir: workDir,
		Tokens:  ghauth.NewCLITokenSource(),
		BaseURL: ghapi.DefaultBaseURL,
	}
}

// Client builds a GitHub client for the environment, acquiring the operator's token
// first. Both failures it can return — no authentication and no client — are
// preconditions, so callers must abort rather than emit a partial report.
func (e *Env) Client(ctx context.Context) (*ghapi.Client, error) {
	if e.Tokens == nil {
		return nil, errors.New("no token source is configured")
	}
	token, err := e.Tokens.Token(ctx)
	if err != nil {
		return nil, err
	}
	return ghapi.NewClient(e.BaseURL, token, e.Transport)
}

var registry = map[string]*Command{}

// Register adds a subcommand. It panics on a malformed or duplicate registration:
// registration happens during package initialization, where a mistake is a programming
// error that must surface at startup rather than as a missing subcommand at runtime.
func Register(cmd *Command) {
	switch {
	case cmd == nil:
		panic("cli: Register(nil)")
	case cmd.Name == "":
		panic("cli: Register with an empty command name")
	case cmd.Run == nil:
		panic("cli: Register(" + cmd.Name + ") with no Run function")
	}
	if _, exists := registry[cmd.Name]; exists {
		panic("cli: duplicate registration of subcommand " + cmd.Name)
	}
	registry[cmd.Name] = cmd
}

// Commands returns every registered subcommand, sorted by name.
func Commands() []*Command {
	commands := make([]*Command, 0, len(registry))
	for _, cmd := range registry {
		commands = append(commands, cmd)
	}
	sort.Slice(commands, func(i, j int) bool { return commands[i].Name < commands[j].Name })
	return commands
}

// UsageError marks an operator input mistake, which exits ExitUsage rather than
// ExitFailure so scripts can tell a typo from an unmet precondition.
type UsageError struct{ Err error }

func (e *UsageError) Error() string { return e.Err.Error() }
func (e *UsageError) Unwrap() error { return e.Err }

// Usagef builds a UsageError.
func Usagef(format string, args ...any) error {
	return &UsageError{Err: fmt.Errorf(format, args...)}
}

// Run dispatches args to a registered subcommand and returns the process exit code.
func Run(ctx context.Context, env *Env, args []string) int {
	if len(args) == 0 {
		writeUsage(env.Stderr)
		return ExitUsage
	}

	switch args[0] {
	case "help", "-h", "--help":
		writeUsage(env.Stdout)
		return ExitOK
	}

	cmd, ok := registry[args[0]]
	if !ok {
		_, _ = fmt.Fprintf(env.Stderr, "gh-workflow: unknown subcommand %q\n\n", args[0])
		writeUsage(env.Stderr)
		return ExitUsage
	}

	err := cmd.Run(ctx, env, args[1:])
	switch {
	case err == nil:
		return ExitOK
	case errors.Is(err, flag.ErrHelp):
		// The flag package already printed the subcommand's usage.
		return ExitOK
	}

	_, _ = fmt.Fprintf(env.Stderr, "gh-workflow %s: %v\n", cmd.Name, err)
	var usageErr *UsageError
	if errors.As(err, &usageErr) {
		return ExitUsage
	}
	return ExitFailure
}

func writeUsage(w io.Writer) {
	var b strings.Builder
	b.WriteString("Usage: gh-workflow <subcommand> [flags]\n\nSubcommands:\n")
	for _, cmd := range Commands() {
		fmt.Fprintf(&b, "  %-10s %s\n", cmd.Name, cmd.Summary)
	}
	b.WriteString("\nRun `gh-workflow <subcommand> -h` for a subcommand's flags.\n")
	_, _ = io.WriteString(w, b.String())
}

// OutputMode selects a read-only subcommand's rendering (IR-004).
type OutputMode string

// Supported output modes.
const (
	OutputHuman OutputMode = "human"
	OutputJSON  OutputMode = "json"
)

// ParseOutputMode validates an --output value.
func ParseOutputMode(s string) (OutputMode, error) {
	switch OutputMode(s) {
	case OutputHuman:
		return OutputHuman, nil
	case OutputJSON:
		return OutputJSON, nil
	default:
		return "", fmt.Errorf("unknown output mode %q; want %q or %q", s, OutputHuman, OutputJSON)
	}
}

// MarshalJSON renders v as the tool's JSON output: indented, with a trailing newline.
// It returns bytes rather than writing them so callers can finish every fallible step
// before the first byte reaches stdout.
func MarshalJSON(v any) ([]byte, error) {
	encoded, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("encoding JSON output: %w", err)
	}
	return append(encoded, '\n'), nil
}

// ResolveRepoFile finds rel by walking up from start, which is how the tool locates its
// delivered artifacts with no arguments (IR-004) regardless of where in a consumer
// checkout the agent happened to invoke it.
func ResolveRepoFile(start, rel string) (string, error) {
	dir, err := filepath.Abs(start)
	if err != nil {
		return "", fmt.Errorf("resolving the working directory %s: %w", start, err)
	}
	for {
		candidate := filepath.Join(dir, rel)
		if info, err := os.Stat(candidate); err == nil && info.Mode().IsRegular() {
			return candidate, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("could not find %s in %s or any parent directory", rel, start)
		}
		dir = parent
	}
}
