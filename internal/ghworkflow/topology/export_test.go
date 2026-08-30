package topology

// The unexported field names and date layout, exposed to the external test package that
// pins them against render's own constants. They are test-only: production callers have
// no business reading them, and exporting them properly would invite a second authority.
const (
	FieldWorkflowForTest   = fieldWorkflow
	FieldTargetDateForTest = fieldTargetDate
	DateLayoutForTest      = dateLayout
)
