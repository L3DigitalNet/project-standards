package mutate

import (
	"context"
	"flag"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/orgschema"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// terminalReason returns the native close reason paired with a terminal Workflow value,
// and reports whether the value is terminal at all.
//
// Three subcommands need the same answer — `set` refuses these values, `close` applies
// them, `reopen` refuses them — and it is a function rather than a package map because a
// map is writable by anything in the package, while this pairing is the vocabulary
// contract the whole terminal sequence rests on.
func terminalReason(workflow string) (reason string, terminal bool) {
	switch workflow {
	case "Done":
		return "completed", true
	case "Dropped":
		return "not_planned", true
	default:
		return "", false
	}
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
	pairs := make([]string, 0, len(a.items))
	for _, item := range a.items {
		pairs = append(pairs, item.Name+"="+item.Value)
	}
	return strings.Join(pairs, ", ")
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
			if _, terminal := terminalReason(item.Value); terminal {
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

	case orgschema.TypeDate:
		if _, err := time.Parse(render.DateLayout, value); err != nil {
			return cli.Usagef("%q is not a valid %s value; dates are YYYY-MM-DD", value, field.Name)
		}
		return nil

	case orgschema.TypeNumber:
		// Checked here, offline, so a value GitHub would reject as the wrong JSON type is
		// refused before anything is sent rather than surfacing as an API error (EC-008).
		if _, err := strconv.ParseFloat(value, 64); err != nil {
			return cli.Usagef("%q is not a valid %s value; %s takes a number", value, field.Name, field.Name)
		}
		return nil

	default:
		// Text fields have no vocabulary to check against. The value is still required to
		// be non-empty, which Set already guarantees.
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
	byName := make(map[string]ghapi.IssueFieldIdentity, len(live))
	for _, field := range live {
		byName[field.Name] = field
	}

	resolved := make([]ghapi.IssueFieldAssignment, 0, len(items))
	for _, item := range items {
		field, ok := byName[item.Name]
		if !ok {
			return nil, fmt.Errorf("the %s organization defines no Issue Field named %q, "+
				"though the baseline schema does; run `gh-workflow audit` to see the drift", org, item.Name)
		}
		value, err := fieldValue(field, item.Value)
		if err != nil {
			return nil, err
		}
		resolved = append(resolved, ghapi.IssueFieldAssignment{FieldID: field.ID, Value: value})
	}
	return resolved, nil
}

// fieldValue converts the operator's text into the JSON type the field's data type
// requires.
//
// Every flag value arrives as a string, and encoding one for a number field would send
// `"3"` where GitHub expects `3` — a type error the API reports as a rejected write rather
// than as the mistyped conversion it is. The live data type decides, because it is what
// the write is addressed against; the baseline schema has already refused anything the
// conversion could fail on.
func fieldValue(field ghapi.IssueFieldIdentity, raw string) (any, error) {
	if field.DataType != orgschema.TypeNumber {
		return raw, nil
	}
	number, err := strconv.ParseFloat(raw, 64)
	if err != nil {
		return nil, cli.Usagef("%q is not a valid %s value; %s takes a number", raw, field.Name, field.Name)
	}
	return number, nil
}

// describe renders applied assignments the way the confirmation lines read them out.
func describe(items []assignment) string {
	parts := make([]string, 0, len(items))
	for _, item := range items {
		parts = append(parts, item.Name+" = "+item.Value)
	}
	return strings.Join(parts, ", ")
}
