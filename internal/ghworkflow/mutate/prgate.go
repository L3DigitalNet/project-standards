package mutate

// The pull-request plumbing shared by `check --pr`, `ready`, `merge`, and `close --pr`:
// the loaded-gate alias over internal/ghworkflow/topology, the DR-004 envelope those
// routes emit, and the ordered-step record ERR-014 requires a partially applied paired
// operation to leave behind.
//
// The reads themselves live in internal/ghworkflow/topology, which `summary` and
// `receipt` also load from — one snapshot assembly for every surface (FR-022). Nothing
// in this file may reintroduce a second one.

import (
	"context"
	"fmt"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/topology"
)

// domainError is a completed evaluation that found something, which IR-005 classifies as
// `domain-finding` and exit 1.
//
// It is a distinct type rather than a bare fmt.Errorf only so the intent is greppable:
// cli.Classify already maps any unmarked error to the domain class, and the danger this
// names is the opposite direction — an operational failure that reaches Classify without
// its marker would be reported as a verdict the tool never actually reached.
type domainError struct{ message string }

func (e *domainError) Error() string { return e.message }

func domainf(format string, args ...any) error {
	return &domainError{message: fmt.Sprintf(format, args...)}
}

// prGate is the loaded pull request every PR route works from. The assembly itself
// moved to internal/ghworkflow/topology when `summary` and `receipt` became adapters
// over the same snapshot (FR-022); the alias keeps the routes in this package reading in
// their own vocabulary while there is exactly one implementation.
type prGate = topology.Gate

// loadPRGate performs the phase-bounded read set and evaluates the gate.
func loadPRGate(ctx context.Context, client *ghapi.Client, repo render.Repository,
	schema *orgschema.Schema, number int, through relation.Phase,
) (*prGate, error) {
	return topology.Load(ctx, client, repo.Owner, repo.Name, schema, number, through)
}

// recognizedIssueType returns name when the baseline schema declares it an ordinary work
// type, and "" otherwise. `check --issue` reads it against the same authority the PR
// routes do, so the two routes cannot disagree about which types are ordinary work.
func recognizedIssueType(name string, schema *orgschema.Schema) string {
	return topology.RecognizedIssueType(name, schema)
}

// prTarget builds the envelope target for a pull-request route.
func prTarget(repo render.Repository, number int, url string) cli.Target {
	return cli.Target{Kind: cli.TargetPullRequest, Number: number, Repository: repo.String(), URL: url}
}

// steps records the ordered mutation boundaries of a paired command.
//
// The plan is declared up front and every unreached step stays `pending`, which is what
// makes a partially applied operation reportable rather than merely failed (ERR-014): the
// envelope states which writes provably landed and which provably did not, and the rerun
// that resumes reads the same statuses. A step recorded only when it runs would leave the
// steps after a failure absent, and absent reads as "not part of this operation".
type steps struct {
	order  []string
	status map[string]cli.Step
}

func newSteps(names ...string) *steps {
	s := &steps{order: names, status: make(map[string]cli.Step, len(names))}
	for _, name := range names {
		s.status[name] = cli.Step{Name: name, Status: cli.StepPending}
	}
	return s
}

// mark sets one declared step's outcome. Marking an undeclared step panics, because the
// step plan is the operation's contract with its own envelope and a typo would silently
// drop a boundary from the record.
//
// A nil recorder is a no-op, so a shared write path can be called both from a paired
// command that reports steps and from a 1.6 subcommand that does not.
func (s *steps) mark(name string, status cli.StepStatus, message string) {
	if s == nil {
		return
	}
	if _, declared := s.status[name]; !declared {
		panic("mutate: undeclared step " + name)
	}
	s.status[name] = cli.Step{Name: name, Status: status, Message: message}
}

func (s *steps) complete(name, message string) { s.mark(name, cli.StepCompleted, message) }
func (s *steps) skip(name, message string)     { s.mark(name, cli.StepSkipped, message) }
func (s *steps) fail(name, message string)     { s.mark(name, cli.StepFailed, message) }

// list returns the steps in declared order.
func (s *steps) list() []cli.Step {
	out := make([]cli.Step, 0, len(s.order))
	for _, name := range s.order {
		out = append(out, s.status[name])
	}
	return out
}
