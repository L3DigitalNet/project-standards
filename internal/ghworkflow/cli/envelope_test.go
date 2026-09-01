package cli_test

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// operationalError is the shape ghapi and ghauth present to the classifier: any error
// whose chain answers Operational() true, with no shared type between the packages.
type operationalError struct{ err error }

func (e operationalError) Error() string     { return e.err.Error() }
func (e operationalError) Unwrap() error     { return e.err }
func (e operationalError) Operational() bool { return true }

func init() {
	cli.Register(&cli.Command{
		Name:    "test-operational",
		Summary: "test double that fails operationally",
		Run: func(context.Context, *cli.Env, []string) error {
			return fmt.Errorf("reading the pull request: %w", operationalError{err: errors.New("502 Bad Gateway")})
		},
	})
	cli.Register(&cli.Command{
		Name:    "test-operational-usage",
		Summary: "test double whose usage error wraps an operational cause",
		Run: func(context.Context, *cli.Env, []string) error {
			return &cli.UsageError{Err: operationalError{err: errors.New("502 Bad Gateway")}}
		},
	})
}

// An environmental failure must be distinguishable from a domain verdict: exit 3 says
// no verdict exists, exit 1 says the verdict is "there are findings".
func TestRunClassifiesOperationalFailures(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name     string
		args     []string
		wantExit int
	}{
		{name: "operational cause", args: []string{"test-operational"}, wantExit: cli.ExitOperational},
		{name: "plain failure", args: []string{"test-fail"}, wantExit: cli.ExitFailure},
		{name: "usage error", args: []string{"test-usage"}, wantExit: cli.ExitUsage},
		{
			name:     "usage wins over an operational cause it wraps",
			args:     []string{"test-operational-usage"},
			wantExit: cli.ExitUsage,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			env, _, _ := testEnv()
			if got := cli.Run(context.Background(), env, tc.args); got != tc.wantExit {
				t.Errorf("exit = %d, want %d", got, tc.wantExit)
			}
		})
	}
}

func TestResultExitCodes(t *testing.T) {
	t.Parallel()

	cases := []struct {
		result cli.Result
		want   int
	}{
		{cli.ResultClear, cli.ExitOK},
		{cli.ResultDomainFinding, cli.ExitFailure},
		{cli.ResultUsage, cli.ExitUsage},
		{cli.ResultOperationalFailure, cli.ExitOperational},
		// An unclassified result must never read as a clear gate.
		{cli.Result("something-new"), cli.ExitOperational},
	}

	for _, tc := range cases {
		if got := tc.result.ExitCode(); got != tc.want {
			t.Errorf("%q.ExitCode() = %d, want %d", tc.result, got, tc.want)
		}
	}
}

func TestClassify(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		err  error
		want cli.Result
	}{
		{name: "nil", err: nil, want: cli.ResultClear},
		{name: "usage", err: cli.Usagef("bad"), want: cli.ResultUsage},
		{name: "operational", err: operationalError{err: errors.New("boom")}, want: cli.ResultOperationalFailure},
		{name: "other", err: errors.New("boom"), want: cli.ResultDomainFinding},
	}

	for _, tc := range cases {
		if got := cli.Classify(tc.err); got != tc.want {
			t.Errorf("%s: Classify = %q, want %q", tc.name, got, tc.want)
		}
	}
}

// NFR-005: the unstamped fallback advances with the payload it ships alongside.
func TestDefaultVersion(t *testing.T) {
	t.Parallel()

	if cli.DefaultVersion != "1.10" {
		t.Errorf("DefaultVersion = %q, want %q", cli.DefaultVersion, "1.10")
	}
}

func TestWriteEnvelopeJSON(t *testing.T) {
	t.Parallel()

	env, stdout, _ := testEnv()
	envelope := cli.NewEnvelope("check", cli.ResultDomainFinding, cli.Target{
		Kind: cli.TargetPullRequest, Number: 40, Repository: "L3DigitalNet/example",
	})
	envelope.Gate = cli.Gate(relation.PhaseMerge)
	envelope.Findings = []cli.Finding{{
		Code: "GHW-PR-MERGE-CONFLICT", Phase: relation.PhaseMerge,
		Category: relation.CategoryAdmissionBlocked, Effect: relation.EffectBlocksMerge,
		Kind: relation.KindPullRequest, Number: 40,
		Message: "does not merge cleanly", Remediation: "update the branch",
	}}
	envelope.Steps = []cli.Step{{Name: "revalidate", Status: cli.StepCompleted}}

	if err := cli.WriteEnvelope(envelope, cli.OutputJSON, env); err != nil {
		t.Fatalf("WriteEnvelope: %v", err)
	}

	var decoded map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &decoded); err != nil {
		t.Fatalf("decoding %q: %v", stdout.String(), err)
	}
	for _, member := range []string{"schema_version", "command", "result", "target", "gate", "findings", "steps"} {
		if _, ok := decoded[member]; !ok {
			t.Errorf("envelope has no %q member", member)
		}
	}
	if decoded["schema_version"] != "1" {
		t.Errorf("schema_version = %v, want \"1\"", decoded["schema_version"])
	}
	finding := decoded["findings"].([]any)[0].(map[string]any)
	for _, member := range []string{"code", "phase", "category", "effect", "kind", "number", "message", "remediation"} {
		if _, ok := finding[member]; !ok {
			t.Errorf("finding has no %q member", member)
		}
	}
}

// DR-004 fixes `gate` as null or a phase, and both collections as arrays: a consumer
// iterating findings must never meet null.
func TestWriteEnvelopeEmptyGateAndCollections(t *testing.T) {
	t.Parallel()

	env, stdout, _ := testEnv()
	envelope := cli.NewEnvelope("summary", cli.ResultClear, cli.Target{Kind: cli.TargetRepository, Repository: "L3DigitalNet/example"})
	envelope.Findings = nil
	envelope.Steps = nil
	if err := cli.WriteEnvelope(envelope, cli.OutputJSON, env); err != nil {
		t.Fatalf("WriteEnvelope: %v", err)
	}
	if !strings.Contains(stdout.String(), `"gate": null`) {
		t.Errorf("output does not render an empty gate as null:\n%s", stdout)
	}
	if !strings.Contains(stdout.String(), `"findings": []`) || !strings.Contains(stdout.String(), `"steps": []`) {
		t.Errorf("output does not render empty collections as arrays:\n%s", stdout)
	}

	var round cli.Envelope
	if err := json.Unmarshal(stdout.Bytes(), &round); err != nil {
		t.Fatalf("round trip: %v", err)
	}
	if round.Gate != "" {
		t.Errorf("round-tripped gate = %q, want empty", round.Gate)
	}
}

// The human view compresses to one line per work item per category, in FR-030 display
// order, while JSON keeps every finding.
func TestWriteEnvelopeHumanCompression(t *testing.T) {
	t.Parallel()

	finding := func(code string, category relation.Category, kind relation.Kind, number int, message string) cli.Finding {
		return cli.Finding{
			Code: code, Phase: relation.PhaseReady, Category: category, Effect: relation.EffectBlocksReady,
			Kind: kind, Number: number, Message: message, Remediation: "fix it",
		}
	}
	env, stdout, _ := testEnv()
	envelope := cli.NewEnvelope("check", cli.ResultDomainFinding, cli.Target{Kind: cli.TargetPullRequest, Number: 40})
	envelope.Findings = []cli.Finding{
		finding("GHW-ISSUE-STRUCTURAL-TARGET-DATE-PASSED", relation.CategoryTargetDatePassed, relation.KindIssue, 12, "date passed"),
		finding("GHW-PR-READY-SECTION-MISSING", relation.CategoryNeedsDefinition, relation.KindPullRequest, 40, "no Summary"),
		finding("GHW-PR-READY-RISK-MISSING", relation.CategoryNeedsDefinition, relation.KindPullRequest, 40, "no risk"),
	}

	if err := cli.WriteEnvelope(envelope, cli.OutputHuman, env); err != nil {
		t.Fatalf("WriteEnvelope: %v", err)
	}
	lines := strings.Split(strings.TrimRight(stdout.String(), "\n"), "\n")
	if len(lines) != 3 {
		t.Fatalf("output has %d lines, want 3 (header plus two compressed lines):\n%s", len(lines), stdout)
	}
	if !strings.Contains(lines[1], string(relation.CategoryNeedsDefinition)) {
		t.Errorf("first finding line is %q, want the Needs definition group first", lines[1])
	}
	if !strings.Contains(lines[1], "no Summary; no risk") {
		t.Errorf("first finding line is %q, want both messages compressed onto it", lines[1])
	}
	if !strings.Contains(lines[2], string(relation.CategoryTargetDatePassed)) {
		t.Errorf("second finding line is %q, want the Target date passed group last", lines[2])
	}
}

// failingWriter models a closed pipe: the caller must learn that the report never
// reached the operator rather than exiting 0 on an unwritten envelope.
type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) { return 0, errors.New("broken pipe") }

func TestWriteEnvelopeReportsWriteFailure(t *testing.T) {
	t.Parallel()

	for _, mode := range []cli.OutputMode{cli.OutputJSON, cli.OutputHuman} {
		env := &cli.Env{Stdout: failingWriter{}, Stderr: &bytes.Buffer{}, WorkDir: "."}
		envelope := cli.NewEnvelope("check", cli.ResultClear, cli.Target{Kind: cli.TargetPullRequest, Number: 1})
		if err := cli.WriteEnvelope(envelope, mode, env); err == nil {
			t.Errorf("%s: WriteEnvelope returned no error for a failing writer", mode)
		}
	}
}

// FR-016: an unencodable document must block the write entirely rather than emit a
// truncated object a consumer would parse as a different result.
func TestMarshalJSONFailureYieldsNoBytes(t *testing.T) {
	t.Parallel()

	encoded, err := cli.MarshalJSON(map[string]any{"steps": make(chan int)})
	if err == nil {
		t.Fatal("MarshalJSON accepted an unencodable value")
	}
	if encoded != nil {
		t.Errorf("MarshalJSON returned %q alongside the error, want no bytes", encoded)
	}
}

// Hostile GitHub text reaching the envelope is encoded at the envelope's own boundary,
// in both output modes and whether it arrived in a finding, a step message, or the target
// (#234 item 2). The payload here is the realistic one: an ANSI erase sequence that
// repaints the operator's terminal, a bare carriage return that overwrites the line
// already printed, and a bidi override that reorders what is displayed.
func TestWriteEnvelopeSanitizesUntrustedText(t *testing.T) {
	t.Parallel()

	const hostile = "title\x1b[2J\rrewritten\u202e"
	build := func() cli.Envelope {
		envelope := cli.NewEnvelope("close", cli.ResultDomainFinding, cli.Target{
			Kind: cli.TargetPullRequest, Number: 40, Repository: "L3DigitalNet/example",
			URL: "https://github.test/x" + hostile,
		})
		envelope.Findings = []cli.Finding{{
			Code: "GHW-PR-POSTMERGE-DISPOSITION-CONFLICT", Kind: relation.KindPullRequest, Number: 40,
			Message: "the API answered: " + hostile, Remediation: "resolve " + hostile,
		}}
		envelope.Steps = []cli.Step{{Name: "record-disposition", Status: cli.StepFailed, Message: hostile}}
		return envelope
	}

	for _, mode := range []cli.OutputMode{cli.OutputJSON, cli.OutputHuman} {
		env, stdout, _ := testEnv()
		if err := cli.WriteEnvelope(build(), mode, env); err != nil {
			t.Fatalf("WriteEnvelope(%s): %v", mode, err)
		}
		for _, forbidden := range []string{"\x1b", "\r", "\u202e"} {
			if strings.Contains(stdout.String(), forbidden) {
				t.Errorf("%s output carries %q unencoded:\n%s", mode, forbidden, stdout.String())
			}
		}
		if !strings.Contains(stdout.String(), "title") {
			t.Errorf("%s output lost the surrounding text:\n%s", mode, stdout.String())
		}
	}

	// The caller's own findings are left alone: a command may re-render or test them after
	// writing, and silently rewriting a slice the caller still holds is a different bug.
	envelope := build()
	env, _, _ := testEnv()
	if err := cli.WriteEnvelope(envelope, cli.OutputJSON, env); err != nil {
		t.Fatalf("WriteEnvelope: %v", err)
	}
	if !strings.Contains(envelope.Findings[0].Message, "\x1b") {
		t.Error("WriteEnvelope mutated the caller's findings in place")
	}
}
