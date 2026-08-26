package render_test

import (
	"os"
	"path/filepath"
	"slices"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
)

// TestWriteGeneratedOutputForGateRun materializes the rendered surfaces into the
// directory named by GH_WORKFLOW_GATE_DIR so the repository's own Prettier and
// markdownlint can be run over them (spec FR-019). It is a no-op in an ordinary test
// run: the gate is an external command, not something a Go test can assert.
//
// The summary is printed rather than written since payload 1.5 removed `ledger`, but the
// operator pastes it into Markdown, so the fidelity constraint it is checked against is
// unchanged.
func TestWriteGeneratedOutputForGateRun(t *testing.T) {
	dir := os.Getenv("GH_WORKFLOW_GATE_DIR")
	if dir == "" {
		t.Skip("set GH_WORKFLOW_GATE_DIR to emit generated output for the markdown gate")
	}
	hostile := render.WorkItem{
		Kind: render.KindIssue, Number: 99,
		Title: "Underscores in snake_case_name, [brackets], <html>, *stars* and https://example.test/a_b",
		Type:  "Research", State: "open",
		Fields: map[string]string{render.FieldWorkflow: "Inbox"},
	}
	snapshot := fixtureSnapshot(t)
	// Cloned first: appending to the fixture's own slice would write through to it
	// whenever its capacity allows, which is a shared-fixture bug waiting for the day
	// another test reads the same snapshot.
	full := render.NewSnapshot(snapshot.Target, snapshot.ReadAt,
		append(slices.Clone(snapshot.Issues), hostile), snapshot.PullRequests)

	for name, body := range map[string]string{
		"summary.md":       render.Summary(full),
		"summary-empty.md": render.Summary(render.NewSnapshot(snapshot.Target, snapshot.ReadAt, nil, nil)),
	} {
		// #nosec G304 G703 -- the destination is the operator's own GH_WORKFLOW_GATE_DIR.
		if err := os.WriteFile(filepath.Join(dir, name), []byte(body), 0o600); err != nil {
			t.Fatalf("WriteFile(%s) error = %v", name, err)
		}
	}
}
