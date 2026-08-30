// Package cli is the gh-workflow command shell: the subcommand registry, the process
// environment every subcommand receives, exit-code classification, and the shared
// output-mode and path-resolution helpers.
//
// The registry is deliberately write-only from the outside. Each subcommand package
// registers itself from an init function, and cmd/gh-workflow pulls it in with a blank
// import, so adding a subcommand adds a file and one import line and never edits shared
// registration code. The ten subcommands of spec IR-005 land across several tasks;
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
	"sync"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghauth"
)

// Process exit codes, which are the machine-readable half of the IR-005 result classes:
// ExitOK for a completed read or a clear gate, ExitFailure for validation that completed
// with domain findings, ExitUsage for an invalid invocation or local refusal, and
// ExitOperational for authentication, API, transport, or another environmental failure
// that prevented completion.
//
// The distinction ExitOperational draws is the point of the code: exit 1 means the tool
// reached a verdict the caller must act on, while exit 3 means no verdict exists and
// retrying may succeed. Automation that conflates them either retries real findings
// forever or treats an outage as a clean gate.
const (
	ExitOK          = 0
	ExitFailure     = 1
	ExitUsage       = 2
	ExitOperational = 3
)

// DefaultVersion is the version an unstamped build reports. It must stay a constant
// expression: `-ldflags "-X main.version=..."` only survives package initialization when
// the variable it names is initialized from one, and cmd/gh-workflow initializes
// main.version from this. Initializing main.version from Version below instead would let
// package initialization overwrite the linker's write and leave every stamped build
// silently reporting this default.
//
// The value tracks the payload version it ships with (NFR-005): stamp, unstamped
// fallback, and build output path advance together, so an unstamped build never claims a
// version the payload no longer is.
const DefaultVersion = "1.7"

// Version is the tool version `help` prints, and the only surface that reports it. It is
// a variable so the reproducible build can stamp it (spec NFR-005); cmd/gh-workflow owns
// the stamping. Payload 1.5 moved it here from internal/ghworkflow/render, whose removed
// generated-document subcommand used to be the thing that printed it.
var Version = DefaultVersion

// Delivered locations of the package artifacts the tool reads. IR-005 requires the tool
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

// The registry is guarded because Register is exported: package initialization is
// single-threaded, but nothing stops a caller — a test spinning up a fixture subcommand,
// most plausibly — from registering or listing concurrently, and an unsynchronized map
// answers that with a fatal runtime throw rather than an error.
var (
	registryMu sync.RWMutex
	registry   = map[string]*Command{}
)

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
	registryMu.Lock()
	defer registryMu.Unlock()
	if _, exists := registry[cmd.Name]; exists {
		panic("cli: duplicate registration of subcommand " + cmd.Name)
	}
	registry[cmd.Name] = cmd
}

// lookup returns the registered subcommand with the given name.
func lookup(name string) (*Command, bool) {
	registryMu.RLock()
	defer registryMu.RUnlock()
	cmd, ok := registry[name]
	return cmd, ok
}

// Commands returns every registered subcommand, sorted by name.
func Commands() []*Command {
	registryMu.RLock()
	commands := make([]*Command, 0, len(registry))
	for _, cmd := range registry {
		commands = append(commands, cmd)
	}
	registryMu.RUnlock()
	sort.Slice(commands, func(i, j int) bool { return commands[i].Name < commands[j].Name })
	return commands
}

// UsageError marks an operator input mistake, which exits ExitUsage rather than
// ExitFailure so scripts can tell a typo from an unmet precondition.
type UsageError struct{ Err error }

// Error returns the underlying message; the usage classification is carried by the type.
func (e *UsageError) Error() string { return e.Err.Error() }

// Unwrap exposes the wrapped cause to errors.Is and errors.As.
func (e *UsageError) Unwrap() error { return e.Err }

// Usagef builds a UsageError.
func Usagef(format string, args ...any) error {
	return &UsageError{Err: fmt.Errorf(format, args...)}
}

// operational is the marker an error anywhere in a chain implements to select
// ExitOperational. It is an interface rather than a shared error type on purpose: the
// packages that produce operational failures — ghapi and ghauth — must not import this
// one, because this package already imports them, and a shared sentinel would close the
// cycle. Any package can satisfy an interface it never names.
type operational interface{ Operational() bool }

// IsOperational reports whether err's chain marks it as an environmental failure —
// authentication, transport, a non-2xx API response, an undecodable body, or pagination
// that truncated without explanation (NFR-007). Callers building an envelope classify
// with this so the JSON result and the exit code cannot disagree.
func IsOperational(err error) bool {
	var marked operational
	return errors.As(err, &marked) && marked.Operational()
}

// Classify maps an error to its IR-005 result class. A nil error is `clear`; note that a
// command reporting domain findings must set ResultDomainFinding itself, because domain
// findings are a successful outcome and never travel as an error.
func Classify(err error) Result {
	switch {
	case err == nil:
		return ResultClear
	case errors.As(err, new(*UsageError)):
		return ResultUsage
	case IsOperational(err):
		return ResultOperationalFailure
	default:
		return ResultDomainFinding
	}
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

	cmd, ok := lookup(args[0])
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
	// Classification order matters: a UsageError that wraps an operational cause is
	// still the operator's mistake, so the usage check runs first.
	return Classify(err).ExitCode()
}

func writeUsage(w io.Writer) {
	var b strings.Builder
	fmt.Fprintf(&b, "gh-workflow %s\n\nUsage: gh-workflow <subcommand> [flags]\n\nSubcommands:\n", Version)
	for _, cmd := range Commands() {
		_, _ = fmt.Fprintf(&b, "  %-10s %s\n", cmd.Name, cmd.Summary)
	}
	b.WriteString("\nRun `gh-workflow <subcommand> -h` for a subcommand's flags.\n")
	_, _ = io.WriteString(w, b.String())
}

// OutputMode selects a read-only subcommand's rendering (IR-005).
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
// delivered artifacts with no arguments (IR-005) regardless of where in a consumer
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
