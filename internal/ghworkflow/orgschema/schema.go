// Package orgschema loads the baseline GitHub organization schema — the five Issue
// Types and seven Issue Fields recorded in the payload's `org-schema.yaml` — that
// `gh-workflow audit` compares live organization state against (spec FR-016).
//
// The file is a payload-managed artifact with a fixed, tiny shape, so this package
// carries its own bounded YAML reader instead of a general decoder: the Go standard
// library has no YAML decoder, and the tool takes no module dependencies (plan A-002).
// The accepted subset is exactly two top-level mapping keys, a string sequence under
// `issue_types`, and a per-field mapping under `issue_fields` holding `type` and an
// optional `values` string sequence.
//
// Everything outside that subset is a parse error rather than an ignored line. A
// baseline this parser silently misread would produce a confidently wrong audit — the
// one failure mode an audit oracle cannot have — so the parser fails closed instead.
package orgschema

import (
	"fmt"
	"os"
	"strings"
)

// Issue Field data types, named as GitHub names them. TypeSingleSelect is the only one
// carrying an enumerated value list; the rest are compared on their type alone, but the
// write path validates values against the type, so the names belong here rather than as
// literals at each use.
const (
	TypeSingleSelect = "single_select"
	TypeDate         = "date"
	TypeNumber       = "number"
)

const (
	keyIssueTypes  = "issue_types"
	keyIssueFields = "issue_fields"
	keyType        = "type"
	keyValues      = "values"
)

// Field is one baseline Issue Field. Values is populated only for single_select.
type Field struct {
	Name   string
	Type   string
	Values []string
}

// Schema is the parsed baseline. Both slices preserve file order, which the audit uses
// as its report order so repeated runs against unchanged state are byte-identical.
type Schema struct {
	IssueTypes  []string
	IssueFields []Field
}

// Field returns the baseline field with the given name, matched exactly. Matching is
// case-sensitive on purpose: GitHub field names are operator-visible strings, so a case
// difference is real drift the audit should report rather than quietly absorb.
func (s *Schema) Field(name string) (Field, bool) {
	for _, f := range s.IssueFields {
		if f.Name == name {
			return f, true
		}
	}
	return Field{}, false
}

// Load reads and parses the baseline at path.
func Load(path string) (*Schema, error) {
	// #nosec G304 -- the path is the operator's --schema flag or the payload's fixed
	// delivered location; the tool reads whatever checkout it was invoked in.
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("reading org schema %s: %w", path, err)
	}
	schema, err := Parse(data)
	if err != nil {
		return nil, fmt.Errorf("parsing org schema %s: %w", path, err)
	}
	return schema, nil
}

// Parse reads the bounded YAML subset described in the package documentation.
func Parse(data []byte) (*Schema, error) {
	p := &parser{currentField: -1}
	for i, raw := range strings.Split(string(data), "\n") {
		if err := p.line(i+1, raw); err != nil {
			return nil, err
		}
	}
	if err := p.finish(); err != nil {
		return nil, err
	}
	return &p.schema, nil
}

type parser struct {
	schema       Schema
	section      string
	currentField int
	inValues     bool
	seenTop      map[string]bool
}

func (p *parser) line(n int, raw string) error {
	// A CRLF checkout — which a payload-managed artifact gets on any platform normalizing
	// line endings — delivers every line with a trailing carriage return. This parser
	// measures indentation and trims trailing whitespace by hand, and the trim covers
	// spaces only, so an untrimmed \r would ride into every scalar: a baseline of "Bug\r"
	// matches nothing live, and the audit reports the whole organization as both missing
	// and extra while looking like it succeeded.
	raw = strings.TrimRight(raw, "\r")
	if strings.ContainsRune(raw, '\t') {
		return fmt.Errorf("line %d: tab characters are not permitted in the org schema", n)
	}
	if strings.TrimSpace(raw) == "" {
		return nil
	}
	indent := len(raw) - len(strings.TrimLeft(raw, " "))
	body := strings.TrimRight(raw[indent:], " ")
	if strings.HasPrefix(body, "#") {
		return nil
	}
	if indent%2 != 0 {
		return fmt.Errorf("line %d: indentation of %d spaces is not a multiple of two", n, indent)
	}
	switch indent {
	case 0:
		return p.topLevel(n, body)
	case 2:
		return p.section2(n, body)
	case 4:
		return p.section4(n, body)
	case 6:
		return p.section6(n, body)
	default:
		return fmt.Errorf("line %d: unexpected indentation of %d spaces", n, indent)
	}
}

func (p *parser) topLevel(n int, body string) error {
	if body == "---" || body == "..." {
		return fmt.Errorf("line %d: multi-document YAML is not supported in the org schema", n)
	}
	key, rest, ok := splitKey(body)
	if !ok {
		return fmt.Errorf("line %d: expected a top-level mapping key, got %q", n, body)
	}
	if rest != "" {
		return fmt.Errorf("line %d: top-level key %q must introduce an indented block, not an inline value", n, key)
	}
	if key != keyIssueTypes && key != keyIssueFields {
		return fmt.Errorf("line %d: unknown top-level key %q; only %q and %q are permitted", n, key, keyIssueTypes, keyIssueFields)
	}
	if p.seenTop[key] {
		return fmt.Errorf("line %d: duplicate top-level key %q", n, key)
	}
	if p.seenTop == nil {
		p.seenTop = map[string]bool{}
	}
	p.seenTop[key] = true
	p.section = key
	p.currentField = -1
	p.inValues = false
	return nil
}

func (p *parser) section2(n int, body string) error {
	switch p.section {
	case keyIssueTypes:
		if body == "-" {
			return fmt.Errorf("line %d: empty value in the %q sequence", n, keyIssueTypes)
		}
		item, ok := strings.CutPrefix(body, "- ")
		if !ok {
			return fmt.Errorf("line %d: expected a sequence item under %q, got %q", n, keyIssueTypes, body)
		}
		value, err := scalar(n, item)
		if err != nil {
			return err
		}
		for _, existing := range p.schema.IssueTypes {
			if existing == value {
				return fmt.Errorf("line %d: duplicate issue type %q", n, value)
			}
		}
		p.schema.IssueTypes = append(p.schema.IssueTypes, value)
		return nil

	case keyIssueFields:
		name, rest, ok := splitKey(body)
		if !ok {
			return fmt.Errorf("line %d: expected an issue field name under %q, got %q", n, keyIssueFields, body)
		}
		if rest != "" {
			return fmt.Errorf("line %d: issue field %q must introduce an indented block, not an inline value", n, name)
		}
		if _, exists := p.schema.Field(name); exists {
			return fmt.Errorf("line %d: duplicate issue field %q", n, name)
		}
		p.schema.IssueFields = append(p.schema.IssueFields, Field{Name: name})
		p.currentField = len(p.schema.IssueFields) - 1
		p.inValues = false
		return nil

	default:
		return fmt.Errorf("line %d: indented content appears before any top-level key", n)
	}
}

func (p *parser) section4(n int, body string) error {
	if p.section != keyIssueFields || p.currentField < 0 {
		return fmt.Errorf("line %d: unexpected content at this indentation", n)
	}
	field := &p.schema.IssueFields[p.currentField]

	if item, ok := strings.CutPrefix(body, "- "); ok {
		return fmt.Errorf("line %d: unexpected sequence item %q under issue field %q", n, item, field.Name)
	}
	key, rest, ok := splitKey(body)
	if !ok {
		return fmt.Errorf("line %d: expected %q or %q under issue field %q, got %q", n, keyType, keyValues, field.Name, body)
	}
	switch key {
	case keyType:
		if field.Type != "" {
			return fmt.Errorf("line %d: duplicate %q for issue field %q", n, keyType, field.Name)
		}
		value, err := scalar(n, rest)
		if err != nil {
			return err
		}
		field.Type = value
		p.inValues = false
		return nil

	case keyValues:
		if rest != "" {
			return fmt.Errorf("line %d: %q for issue field %q must introduce an indented sequence", n, keyValues, field.Name)
		}
		if p.inValues {
			return fmt.Errorf("line %d: duplicate %q for issue field %q", n, keyValues, field.Name)
		}
		p.inValues = true
		return nil

	default:
		return fmt.Errorf("line %d: unknown key %q under issue field %q; only %q and %q are permitted", n, key, field.Name, keyType, keyValues)
	}
}

func (p *parser) section6(n int, body string) error {
	if !p.inValues || p.currentField < 0 {
		return fmt.Errorf("line %d: unexpected content at this indentation", n)
	}
	field := &p.schema.IssueFields[p.currentField]
	if body == "-" {
		return fmt.Errorf("line %d: empty value in the %q sequence for issue field %q", n, keyValues, field.Name)
	}
	item, ok := strings.CutPrefix(body, "- ")
	if !ok {
		return fmt.Errorf("line %d: expected a sequence item under %q for issue field %q, got %q", n, keyValues, field.Name, body)
	}
	value, err := scalar(n, item)
	if err != nil {
		return err
	}
	for _, existing := range field.Values {
		if existing == value {
			return fmt.Errorf("line %d: duplicate value %q for issue field %q", n, value, field.Name)
		}
	}
	field.Values = append(field.Values, value)
	return nil
}

func (p *parser) finish() error {
	if !p.seenTop[keyIssueTypes] {
		return fmt.Errorf("org schema is missing the required top-level key %q", keyIssueTypes)
	}
	if !p.seenTop[keyIssueFields] {
		return fmt.Errorf("org schema is missing the required top-level key %q", keyIssueFields)
	}
	if len(p.schema.IssueTypes) == 0 {
		return fmt.Errorf("org schema declares %q with no entries", keyIssueTypes)
	}
	if len(p.schema.IssueFields) == 0 {
		return fmt.Errorf("org schema declares %q with no entries", keyIssueFields)
	}
	for _, field := range p.schema.IssueFields {
		switch {
		case field.Type == "":
			return fmt.Errorf("issue field %q is missing its %q", field.Name, keyType)
		case field.Type == TypeSingleSelect && len(field.Values) == 0:
			return fmt.Errorf("issue field %q is %s but declares no %q", field.Name, TypeSingleSelect, keyValues)
		case field.Type != TypeSingleSelect && len(field.Values) > 0:
			return fmt.Errorf("issue field %q is %s, which cannot carry %q", field.Name, field.Type, keyValues)
		}
	}
	return nil
}

// splitKey splits "key: rest" on the first colon. Field names may contain spaces
// ("Change risk", "Target date") but never colons, so the first colon is unambiguous.
func splitKey(body string) (key, rest string, ok bool) {
	key, rest, ok = strings.Cut(body, ":")
	if !ok {
		return "", "", false
	}
	key = strings.TrimSpace(key)
	if key == "" {
		return "", "", false
	}
	return key, strings.TrimSpace(rest), true
}

// scalar accepts a plain or fully quoted string and rejects every other YAML node type.
// Rejecting is the point: an anchor, block scalar, or flow collection reaching the audit
// as a literal string would silently corrupt the baseline it is supposed to define.
func scalar(n int, s string) (string, error) {
	if s == "" {
		return "", fmt.Errorf("line %d: empty value", n)
	}
	if quote := s[0]; quote == '"' || quote == '\'' {
		if len(s) < 2 || s[len(s)-1] != quote {
			return "", fmt.Errorf("line %d: unterminated quoted value %q", n, s)
		}
		inner := s[1 : len(s)-1]
		if inner == "" {
			return "", fmt.Errorf("line %d: empty value", n)
		}
		if strings.ContainsRune(inner, rune(quote)) || strings.ContainsRune(inner, '\\') {
			return "", fmt.Errorf("line %d: escapes inside quoted values are not supported", n)
		}
		return inner, nil
	}
	if strings.ContainsAny(s[:1], "&*!|>[]{}%@`,") {
		return "", fmt.Errorf("line %d: unsupported YAML construct in value %q", n, s)
	}
	if strings.Contains(s, " #") {
		return "", fmt.Errorf("line %d: inline comments are not supported in values (%q)", n, s)
	}
	return s, nil
}
