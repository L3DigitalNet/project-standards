package render_test

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/cli"

	// `check` lives in the mutation package. Importing it blank registers that subcommand
	// in the same registry the rendering surfaces register into, which is exactly how
	// cmd/gh-workflow assembles the binary — so this test compares the three surfaces as
	// an operator meets them, not as three library calls.
	_ "github.com/L3DigitalNet/project-standards/internal/ghworkflow/mutate"
)

// findingCodes runs one command in JSON mode and returns its findings as
// "kind#number:code" strings, which is the comparable identity of a finding across
// surfaces: the same invariant, about the same work item.
func findingCodes(t *testing.T, args ...string) []string {
	t.Helper()

	h := newHarness(t)
	// `check` exits 1 on findings and the report surfaces exit 0 on the same findings
	// (IR-005); both wrote their envelope before returning, which is what this reads.
	if code := h.run(args...); code != cli.ExitOK && code != cli.ExitFailure {
		t.Fatalf("%v = %d (stderr: %s)", args, code, h.stderr)
	}
	var decoded struct {
		Findings []struct {
			Code   string `json:"code"`
			Kind   string `json:"kind"`
			Number int    `json:"number"`
		} `json:"findings"`
	}
	if err := json.Unmarshal(h.stdout.Bytes(), &decoded); err != nil {
		t.Fatalf("json.Unmarshal(%v) error = %v, output:\n%s", args, err, h.stdout)
	}
	var codes []string
	for _, finding := range decoded.Findings {
		codes = append(codes, finding.Kind+"#"+itoa(finding.Number)+":"+finding.Code)
	}
	return codes
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var digits []byte
	for ; n > 0; n /= 10 {
		digits = append([]byte{byte('0' + n%10)}, digits...)
	}
	return string(digits)
}

// One engine, three surfaces, one verdict (FR-022). `check --pr`, `receipt --pr`, and the
// summary must report the same findings about the same pull request from the same
// observed state — a renderer that reimplemented any part of the policy would show up
// here as a code the other two do not have.
//
// PR #21 is the fixture used because its observed state (open and not draft) admits every
// pre-event phase, so the equivalence is tested across the whole cumulative gate rather
// than across the Structural subset a draft would filter down to.
func TestCheckReceiptAndSummaryAgreeOnOnePullRequest(t *testing.T) {
	t.Parallel()

	check := findingCodes(t, "check", "--pr", "21", "--output", "json")
	receipt := findingCodes(t, "receipt", "--pr", "21", "--output", "json")
	if strings.Join(check, "|") != strings.Join(receipt, "|") {
		t.Errorf("check and receipt disagree\n--- check ---\n%v\n--- receipt ---\n%v", check, receipt)
	}
	if len(check) == 0 {
		t.Fatal("the fixture produced no findings, so the comparison proves nothing")
	}

	// The summary reports on every open work item, so its finding set is compared over
	// the pull request in question. Its independent Issue findings are its own — an Issue
	// read on its own carries attention no single PR's gate can see.
	summary := map[string]bool{}
	for _, code := range findingCodes(t, "summary", "--output", "json") {
		summary[code] = true
	}
	for _, code := range check {
		if !summary[code] {
			t.Errorf("the summary omits %s, which check and receipt both report", code)
		}
	}
}
