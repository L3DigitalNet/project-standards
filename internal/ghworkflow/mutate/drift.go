package mutate

// The ERR-011 live-schema-drift precondition (FR-021): before any field write, the
// baseline vocabulary the invocation was validated against must still be the vocabulary
// the organization actually has.
//
// Two disagreements are drift rather than operator error, because the invocation already
// passed offline validation against the delivered baseline: a field the baseline defines
// and the organization does not, and a live *number* field whose baseline-accepted value
// is not a JSON number. Both mean the two schemas have diverged, so the correct answer is
// to stop before writing and point at the audit that explains the divergence — blaming
// the flag would send the operator to fix an invocation that is already correct.
//
// The precondition is structural, not a check: resolveFieldIDs runs before the first
// write on every path, so a drifted schema cannot strand a paired operation between its
// steps.

import (
	"errors"
	"fmt"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// schemaDriftError is a disagreement between the baseline schema and the live
// organization, detected while resolving a field write.
//
// It carries the same message the untyped error carried through 1.6, because that text is
// what the `set`, `close`, and `reopen` failure paths print; the type exists so the 1.7
// paired commands can additionally render it as a DR-004 finding rather than reparsing
// prose.
type schemaDriftError struct {
	Field   string
	message string
}

func (e *schemaDriftError) Error() string { return e.message }

// driftFinding projects a schema-drift error onto the envelope, or reports false for any
// other error.
//
// The category is Blocked and the effect requires-disposition: nothing the tool can do
// converges a schema divergence, and the organization schema is explicitly outside this
// package's write surface (FR-009), so the resolution is a human decision recorded
// elsewhere. Classifying it as requires-synchronization would advertise a deterministic
// convergence this package must never perform.
func driftFinding(err error, kind relation.Kind, number int) (relation.Finding, bool) {
	var drift *schemaDriftError
	if !errors.As(err, &drift) {
		return relation.Finding{}, false
	}
	return relation.Finding{
		Code:     "GHW-ISSUE-STRUCTURAL-SCHEMA-DRIFT",
		Phase:    relation.PhaseStructural,
		Category: relation.CategoryBlocked,
		Effect:   relation.EffectRequiresDisposition,
		Kind:     kind,
		Number:   number,
		Message: fmt.Sprintf("the live organization schema has drifted from the baseline for %q: %s",
			drift.Field, drift.Error()),
		Remediation: "Run `gh-workflow audit` to see the drift; the organization schema is changed by a human, never by this package.",
	}, true
}
