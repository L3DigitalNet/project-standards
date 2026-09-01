package mutate

import "github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"

// The two Workflow values the `land` transaction moves between, exposed to the external
// test package so its fixture cannot spell them differently from the command under test.
// A fixture that wrote "ready" in the wrong case would make the advance step skip, and the
// test would still pass while proving nothing.
const (
	WorkflowReadyForTest      = workflowReady
	WorkflowInProgressForTest = relation.WorkflowInProgress
)

// LandingProofCommandForTest exposes the rendered landing-proof diff, which is a contract
// with the operator who runs it rather than an implementation detail.
var LandingProofCommandForTest = landingProofCommand
