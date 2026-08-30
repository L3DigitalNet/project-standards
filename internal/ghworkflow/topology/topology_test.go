package topology_test

import (
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/render"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/topology"
)

// The topology package cannot import render — render imports it — so it declares its own
// copies of the two Issue Field names and the date layout it reads. This test is the
// other end of that cross-file contract: it lives in the external test package, where
// importing render is legal, and fails if either copy is renamed alone. Without it a
// drifted field name would silently produce a governing Issue with no Workflow and no
// Target date, which reads as "unset" rather than as a bug.
func TestFieldNamesMatchTheRenderModel(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct{ topologyValue, renderValue, name string }{
		{topology.FieldWorkflowForTest, render.FieldWorkflow, "Workflow"},
		{topology.FieldTargetDateForTest, render.FieldTargetDate, "Target date"},
		{topology.DateLayoutForTest, render.DateLayout, "date layout"},
	} {
		if tc.topologyValue != tc.renderValue {
			t.Errorf("%s: topology has %q, render has %q", tc.name, tc.topologyValue, tc.renderValue)
		}
	}
}
