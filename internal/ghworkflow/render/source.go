package render

import (
	"context"
	"regexp"
	"strings"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/relation"
)

// Fetch reads one repository's open work.
//
// Every call is a GET through the injected transport, so the three rendering surfaces
// cannot mutate anything and the whole suite runs offline against a fake. The read is
// timestamped once, up front: the snapshot describes a moment, and deriving "overdue"
// from a clock that moved during the read would make the summary disagree with its own
// header.
//
// The raw open pull requests are returned beside the snapshot rather than discarded: the
// summary's per-PR topology loads need exactly this list for the one-open-Final rule, and
// letting each of them read it again is the repeated shared read NFR-008 forbids. The
// slice is the complete list, so an empty one means the repository has none.
func Fetch(ctx context.Context, client *ghapi.Client, repo Repository) (*Snapshot, []ghapi.PullRequest, error) {
	readAt := time.Now().UTC()

	rawIssues, err := client.ListOpenIssues(ctx, repo.Owner, repo.Name)
	if err != nil {
		return nil, nil, err
	}
	issues := make([]WorkItem, 0, len(rawIssues))
	for _, issue := range rawIssues {
		issues = append(issues, issueItem(issue))
	}

	rawPulls, err := client.ListOpenPullRequests(ctx, repo.Owner, repo.Name)
	if err != nil {
		return nil, nil, err
	}
	pulls := make([]WorkItem, 0, len(rawPulls))
	for _, pull := range rawPulls {
		item, err := pullItem(ctx, client, repo, pull)
		if err != nil {
			return nil, nil, err
		}
		pulls = append(pulls, item)
	}

	return NewSnapshot(repo.String(), readAt, issues, pulls), rawPulls, nil
}

// FetchIssue reads one issue for a receipt.
func FetchIssue(ctx context.Context, client *ghapi.Client, repo Repository, number int) (WorkItem, error) {
	issue, err := client.GetIssue(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return WorkItem{}, err
	}
	return issueItem(*issue), nil
}

// FetchPullRequest reads one pull request for a receipt.
func FetchPullRequest(ctx context.Context, client *ghapi.Client, repo Repository, number int) (WorkItem, error) {
	pull, err := client.GetPullRequest(ctx, repo.Owner, repo.Name, number)
	if err != nil {
		return WorkItem{}, err
	}
	return pullItem(ctx, client, repo, *pull)
}

// issueItem projects one API issue onto the render model.
//
// Every string that originates with a GitHub author — title, Issue Type name, and each
// Issue Field name and value — is passed through SanitizeText here, at the single point
// where untrusted text enters the model. Sanitizing on ingestion rather than in each
// renderer is what makes the human view and the JSON envelope carry identical bytes;
// see safetext.go for what the encoding removes and why.
func issueItem(issue ghapi.Issue) WorkItem {
	item := WorkItem{
		Kind:                  KindIssue,
		Number:                issue.Number,
		Title:                 SanitizeText(issue.Title),
		URL:                   issue.HTMLURL,
		State:                 issue.State,
		StateReason:           issue.StateReason,
		HasAcceptanceCriteria: hasAcceptanceCriteria(issue.Body),
	}
	if issue.Type != nil {
		item.Type = SanitizeText(issue.Type.Name)
	}
	for _, value := range issue.FieldValues {
		display := value.Display()
		if value.Name == "" || display == "" {
			continue
		}
		if item.Fields == nil {
			item.Fields = map[string]string{}
		}
		item.Fields[SanitizeText(value.Name)] = SanitizeText(display)
	}
	return item
}

func pullItem(ctx context.Context, client *ghapi.Client, repo Repository, pull ghapi.PullRequest) (WorkItem, error) {
	ci, err := client.CIState(ctx, repo.Owner, repo.Name, pull.Head.SHA)
	if err != nil {
		return WorkItem{}, err
	}
	// relation.ParseBody is the only authority on the governing relationship (D15).
	// Payload 1.6 read GitHub's own `Closes #N` syntax here instead; that heuristic is
	// gone, so a PR whose body carries a closing keyword but no `## Governing work`
	// declaration now reads as declaring nothing — which is what it does.
	decl, _ := relation.ParseBody(pull.Body)
	item := WorkItem{
		Kind:   KindPullRequest,
		Number: pull.Number,
		Title:  SanitizeText(pull.Title),
		URL:    pull.HTMLURL,
		State:  pull.State,
		Draft:  pull.Draft,
		Merged: pull.IsMerged(),
		CI:     ci,
	}
	item.Relationship = relationshipName(decl.Relationship)
	if decl.Relationship.Governed() {
		item.GoverningIssue = decl.IssueNumber
	}
	return item, nil
}

// relationshipName renders a parsed relationship in the spelling the declaration itself
// uses, which is the spelling every reference document and operator message uses. The
// engine's own constants are lowercase because they are identifiers, not display text;
// printing them raw would put `final: #12` in a receipt whose remediation says to write
// `Final: #N`.
func relationshipName(r relation.Relationship) string {
	switch r {
	case relation.RelationshipFinal:
		return "Final"
	case relation.RelationshipSupporting:
		return "Supporting"
	case relation.RelationshipStandalone:
		return "Standalone"
	default:
		return ""
	}
}

var acceptanceHeading = regexp.MustCompile(`(?im)^#{1,6}[ \t]+acceptance criteria[ \t]*$`)

// hasAcceptanceCriteria reports whether the body carries a populated acceptance-criteria
// section. An empty heading does not count: the gap the layouts report is the absence of
// criteria, and a heading with nothing under it is exactly that.
func hasAcceptanceCriteria(body string) bool {
	location := acceptanceHeading.FindStringIndex(body)
	if location == nil {
		return false
	}
	for _, line := range strings.Split(body[location[1]:], "\n") {
		trimmed := strings.TrimSpace(line)
		switch {
		case trimmed == "":
			continue
		case strings.HasPrefix(trimmed, "#"):
			return false
		default:
			return true
		}
	}
	return false
}
