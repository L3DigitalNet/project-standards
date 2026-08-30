package cli

import (
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"strings"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// EnvelopeSchemaVersion is the DR-004 envelope version. It is the JSON contract's own
// version, independent of the package and tool versions: a consumer keys parsing off
// this, so it changes only when the envelope's shape changes incompatibly.
const EnvelopeSchemaVersion = "1"

// Result is the outcome class of a command (IR-005). The four classes are what maps a
// run to an exit code, and the mapping is one-way: ExitCode is derived from the class,
// never the other way round, so a command that reports `clear` can never exit nonzero.
type Result string

// The four result classes.
const (
	// ResultClear means the read completed or the gate passed.
	ResultClear Result = "clear"
	// ResultDomainFinding means validation completed and found real findings. This is
	// not an error: the command did its job, and the findings are the answer.
	ResultDomainFinding Result = "domain-finding"
	// ResultUsage means the invocation itself was malformed or locally refused.
	ResultUsage Result = "usage"
	// ResultOperationalFailure means authentication, the API, transport, or another
	// environmental failure prevented completion, so no verdict exists at all.
	ResultOperationalFailure Result = "operational-failure"
)

// ExitCode returns the process exit code for the class.
func (r Result) ExitCode() int {
	switch r {
	case ResultClear:
		return ExitOK
	case ResultDomainFinding:
		return ExitFailure
	case ResultUsage:
		return ExitUsage
	case ResultOperationalFailure:
		return ExitOperational
	default:
		// An unset or unknown class must not read as success. Reporting it as an
		// operational failure is the honest answer: the command produced no classified
		// verdict, which is exactly what exit 3 means.
		return ExitOperational
	}
}

// TargetKind identifies what a command acted on.
type TargetKind string

// The four target kinds.
const (
	TargetIssue        TargetKind = "issue"
	TargetPullRequest  TargetKind = "pull_request"
	TargetRepository   TargetKind = "repository"
	TargetOrganization TargetKind = "organization"
)

// Target identifies the object a command reported on. Number is omitted for
// repository- and organization-scoped commands, which have no work-item number.
type Target struct {
	Kind       TargetKind `json:"kind"`
	Number     int        `json:"number,omitempty"`
	Repository string     `json:"repository,omitempty"`
	URL        string     `json:"url,omitempty"`
}

// Gate is the evaluated FR-030 phase, empty when the command is not a gate. It marshals
// to JSON null rather than "" because DR-004 fixes `gate` as "null or a FR-030 phase",
// and an empty string would be an out-of-vocabulary phase value to a strict consumer.
type Gate string

// MarshalJSON renders the empty gate as null.
func (g Gate) MarshalJSON() ([]byte, error) {
	if g == "" {
		return []byte("null"), nil
	}
	return json.Marshal(string(g))
}

// UnmarshalJSON accepts null as the empty gate, so a round trip through the envelope is
// lossless for fixture tests.
func (g *Gate) UnmarshalJSON(data []byte) error {
	if string(data) == "null" {
		*g = ""
		return nil
	}
	var value string
	if err := json.Unmarshal(data, &value); err != nil {
		return err
	}
	*g = Gate(value)
	return nil
}

// Finding is the DR-004 finding, which is the engine's own finding type rather than a
// parallel copy. The alias is deliberate: a second struct here would drift from the
// engine's, and FR-022 requires one authoritative finding shape that every renderer
// consumes. The dependency runs one way — relation imports nothing from this package.
type Finding = relation.Finding

// StepStatus is a mutation step's outcome.
type StepStatus string

// The four step statuses. `pending` and `failed` are what make a partially applied
// paired operation reportable (ERR-014): the command states which steps it proved
// completed rather than claiming a rollback it never performed.
const (
	StepCompleted StepStatus = "completed"
	StepSkipped   StepStatus = "skipped"
	StepPending   StepStatus = "pending"
	StepFailed    StepStatus = "failed"
)

// Step is one ordered mutation boundary of a paired command.
type Step struct {
	Name    string     `json:"name"`
	Status  StepStatus `json:"status"`
	Message string     `json:"message,omitempty"`
}

// Envelope is the single JSON output shape of version 1.7 (DR-004). Findings and Steps
// are always present as arrays — never null — because a consumer iterating them must not
// have to special-case an absent member.
type Envelope struct {
	SchemaVersion string    `json:"schema_version"`
	Command       string    `json:"command"`
	Result        Result    `json:"result"`
	Target        Target    `json:"target"`
	Gate          Gate      `json:"gate"`
	Findings      []Finding `json:"findings"`
	Steps         []Step    `json:"steps"`
}

// NewEnvelope returns an envelope with the schema version set and both collections
// non-nil.
func NewEnvelope(command string, result Result, target Target) Envelope {
	return Envelope{
		SchemaVersion: EnvelopeSchemaVersion,
		Command:       command,
		Result:        result,
		Target:        target,
		Findings:      []Finding{},
		Steps:         []Step{},
	}
}

// WriteEnvelope renders env to the environment's stdout in the requested mode.
//
// In JSON mode the whole document is marshaled before a single byte is written, so a
// marshal failure blocks the write entirely (FR-016) instead of leaving a truncated
// object on stdout that a consumer would parse as a different result. The caller must
// treat a returned error as a failure of the command, not of formatting.
func WriteEnvelope(env Envelope, mode OutputMode, e *Env) error {
	if env.Findings == nil {
		env.Findings = []Finding{}
	}
	if env.Steps == nil {
		env.Steps = []Step{}
	}
	if mode == OutputJSON {
		encoded, err := MarshalJSON(env)
		if err != nil {
			return err
		}
		_, err = e.Stdout.Write(encoded)
		return err
	}
	return writeHumanEnvelope(env, e.Stdout)
}

// writeHumanEnvelope renders the compressed human view: one line per work item per
// category, in FR-030 display order. The compression is the contract, not a formatting
// preference — JSON retains every finding, and the human view exists so an operator sees
// each affected work item once per required action.
func writeHumanEnvelope(env Envelope, w io.Writer) error {
	var b strings.Builder
	header := env.Command
	if env.Target.Repository != "" {
		header += " " + env.Target.Repository
	}
	if env.Target.Number > 0 {
		header += fmt.Sprintf("#%d", env.Target.Number)
	}
	if env.Gate != "" {
		header += fmt.Sprintf(" [%s gate]", env.Gate)
	}
	fmt.Fprintf(&b, "%s: %s\n", header, env.Result)

	for _, line := range compressFindings(env.Findings) {
		b.WriteString("  " + line + "\n")
	}
	for _, step := range env.Steps {
		fmt.Fprintf(&b, "  step %s: %s", step.Name, step.Status)
		if step.Message != "" {
			b.WriteString(" — " + step.Message)
		}
		b.WriteString("\n")
	}
	_, err := io.WriteString(w, b.String())
	return err
}

// compressFindings groups findings by category in display order, then by work item, and
// joins each group's messages onto one line.
func compressFindings(findings []Finding) []string {
	type key struct {
		category relation.Category
		kind     relation.Kind
		number   int
	}
	messages := map[key][]string{}
	for _, finding := range findings {
		k := key{finding.Category, finding.Kind, finding.Number}
		messages[k] = append(messages[k], finding.Message)
	}

	keys := make([]key, 0, len(messages))
	for k := range messages {
		keys = append(keys, k)
	}
	categoryRank := map[relation.Category]int{}
	for i, category := range relation.CategoryOrder {
		categoryRank[category] = i
	}
	// A category outside the FR-030 vocabulary sorts after every known one instead of
	// silently sharing rank 0 with "Blocked", which would make ordering depend on map
	// iteration and break the "two identical reads render identically" property.
	rank := func(c relation.Category) int {
		if r, ok := categoryRank[c]; ok {
			return r
		}
		return len(relation.CategoryOrder)
	}
	sort.Slice(keys, func(i, j int) bool {
		switch {
		case rank(keys[i].category) != rank(keys[j].category):
			return rank(keys[i].category) < rank(keys[j].category)
		case keys[i].kind != keys[j].kind:
			return keys[i].kind < keys[j].kind
		default:
			return keys[i].number < keys[j].number
		}
	})

	lines := make([]string, 0, len(keys))
	for _, k := range keys {
		item := fmt.Sprintf("%s #%d", k.kind, k.number)
		if k.number == 0 {
			item = string(k.kind)
		}
		lines = append(lines, fmt.Sprintf("%s — %s: %s", k.category, item, strings.Join(messages[k], "; ")))
	}
	return lines
}
