package mutate

import (
	"context"
	"flag"
	"fmt"
	"strings"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// dateLayout is the format GitHub stores and returns date Issue Field values in.
const dateLayout = "2006-01-02"

// terminalWorkflow is the pair of Workflow values that must stay synchronized with the
// native closed state. They are named here because three subcommands need the same
// answer: `set` refuses them, `close` applies them, and `reopen` refuses them.
var terminalWorkflow = map[string]string{
	"Done":    "completed",
	"Dropped": "not_planned",
}

// assignment is one `--field Name=Value` pair as the operator wrote it.
type assignment struct {
	Name  string
	Value string
}

// assignments collects repeated --field flags. Field names carry spaces ("Change risk")
// and values carry em dashes ("P0 — Immediate") but neither contains `=`, so splitting on
// the first one is unambiguous.
type assignments struct {
	items []assignment
}

func (a *assignments) String() string {
	names := make([]string, 0, len(a.items))
	for _, item := range a.items {
		names = append(names, item.Name+"="+item.Value)
	}
	return strings.Join(names, ", ")
}

func (a *assignments) Set(raw string) error {
	name, value, ok := strings.Cut(raw, "=")
	if !ok {
		return fmt.Errorf("expected Name=Value, got %q", raw)
	}
	name, value = strings.TrimSpace(name), strings.TrimSpace(value)
	if name == "" || value == "" {
		return fmt.Errorf("expected Name=Value with both parts present, got %q", raw)
	}
	a.items = append(a.items, assignment{Name: name, Value: value})
	return nil
}

func addFieldFlag(fs *flag.FlagSet, usage string) *assignments {
	values := &assignments{}
	fs.Var(values, "field", usage)
	return values
}

// validate checks every requested field and value against the baseline schema.
//
// This runs before a client is built, which is what makes spec EC-008 structural: an
// invalid value cannot reach GitHub because nothing has been sent when the refusal
// happens. Refusals are usage errors — a value outside the vocabulary is a mistyped
// invocation, not an unmet environmental precondition — and each one names the valid set
// so the caller can correct it without opening the reference.
func (a *assignments) validate(schema *orgschema.Schema, allowTerminalWorkflow bool) error {
	if len(a.items) == 0 {
		return nil
	}
	seen := map[string]bool{}
	for _, item := range a.items {
		if seen[item.Name] {
			return cli.Usagef("field %q was given twice; each field takes one value", item.Name)
		}
		seen[item.Name] = true

		field, ok := schema.Field(item.Name)
		if !ok {
			return cli.Usagef("unknown Issue Field %q; the organization schema defines: %s",
				item.Name, strings.Join(fieldNames(schema), ", "))
		}
		if err := validateValue(field, item.Value); err != nil {
			return err
		}
		if !allowTerminalWorkflow && item.Name == render.FieldWorkflow {
			if _, terminal := terminalWorkflow[item.Value]; terminal {
				return cli.Usagef("Workflow %q is a terminal value and must stay paired with the "+
					"native closed state; apply it with `gh-workflow close` instead", item.Value)
			}
		}
	}
	return nil
}

func validateValue(field orgschema.Field, value string) error {
	switch field.Type {
	case orgschema.TypeSingleSelect:
		for _, candidate := range field.Values {
			if candidate == value {
				return nil
			}
		}
		return cli.Usagef("%q is not a valid %s value; valid values are: %s",
			value, field.Name, strings.Join(field.Values, ", "))

	case "date":
		if _, err := time.Parse(dateLayout, value); err != nil {
			return cli.Usagef("%q is not a valid %s value; dates are YYYY-MM-DD", value, field.Name)
		}
		return nil

	default:
		// Text and number fields have no enumerated vocabulary to check against. The
		// value is still required to be non-empty, which Set already guarantees.
		return nil
	}
}

func fieldNames(schema *orgschema.Schema) []string {
	names := make([]string, 0, len(schema.IssueFields))
	for _, field := range schema.IssueFields {
		names = append(names, field.Name)
	}
	return names
}

// validateIssueType refuses a Type outside the baseline vocabulary, which has no local
// extensions.
func validateIssueType(schema *orgschema.Schema, issueType string) error {
	for _, candidate := range schema.IssueTypes {
		if candidate == issueType {
			return nil
		}
	}
	return cli.Usagef("unknown Issue Type %q; the organization schema defines: %s",
		issueType, strings.Join(schema.IssueTypes, ", "))
}

// resolveFieldIDs maps validated name/value pairs onto the numeric field ids GitHub
// addresses writes by.
//
// A name the organization does not define here is drift between the baseline and live
// schema, not operator error, so it fails as a precondition and points at the audit that
// explains it rather than at the flag.
func resolveFieldIDs(ctx context.Context, client *ghapi.Client, org string,
	items []assignment,
) ([]ghapi.IssueFieldAssignment, error) {
	if len(items) == 0 {
		return nil, nil
	}
	live, err := client.ListIssueFieldIdentities(ctx, org)
	if err != nil {
		return nil, err
	}
	byName := make(map[string]int64, len(live))
	for _, field := range live {
		byName[field.Name] = field.ID
	}

	resolved := make([]ghapi.IssueFieldAssignment, 0, len(items))
	for _, item := range items {
		id, ok := byName[item.Name]
		if !ok {
			return nil, fmt.Errorf("the %s organization defines no Issue Field named %q, "+
				"though the baseline schema does; run `gh-workflow audit` to see the drift", org, item.Name)
		}
		resolved = append(resolved, ghapi.IssueFieldAssignment{FieldID: id, Value: item.Value})
	}
	return resolved, nil
}

// describe renders applied assignments the way the confirmation lines read them out.
func describe(items []assignment) string {
	parts := make([]string, 0, len(items))
	for _, item := range items {
		parts = append(parts, item.Name+" = "+item.Value)
	}
	return strings.Join(parts, ", ")
}
