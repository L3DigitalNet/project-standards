package render

import (
	"context"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/L3DigitalNet/project-standards/internal/ghworkflow/ghapi"
)

// Fetch reads one repository's open work.
//
// Every call is a GET through the injected transport, so the three rendering surfaces
// cannot mutate anything and the whole suite runs offline against a fake. The read is
// timestamped once, up front: the snapshot describes a moment, and deriving "overdue"
// from a clock that moved during the read would make the summary disagree with its own
// header.
func Fetch(ctx context.Context, client *ghapi.Client, repo Repository) (*Snapshot, error) {
	readAt := time.Now().UTC()

	rawIssues, err := client.ListOpenIssues(ctx, repo.Owner, repo.Name)
	if err != nil {
		return nil, err
	}
	issues := make([]WorkItem, 0, len(rawIssues))
	for _, issue := range rawIssues {
		issues = append(issues, issueItem(issue))
	}

	rawPulls, err := client.ListOpenPullRequests(ctx, repo.Owner, repo.Name)
	if err != nil {
		return nil, err
	}
	pulls := make([]WorkItem, 0, len(rawPulls))
	for _, pull := range rawPulls {
		item, err := pullItem(ctx, client, repo, pull)
		if err != nil {
			return nil, err
		}
		pulls = append(pulls, item)
	}

	return NewSnapshot(repo.String(), readAt, issues, pulls), nil
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
	return WorkItem{
		Kind:           KindPullRequest,
		Number:         pull.Number,
		Title:          SanitizeText(pull.Title),
		URL:            pull.HTMLURL,
		State:          pull.State,
		Draft:          pull.Draft,
		CI:             ci,
		GoverningIssue: GoverningIssue(pull.Body),
	}, nil
}

// closingKeyword matches GitHub's own issue-closing syntax, which is the link the
// platform acts on. Reading the same syntax means the tool reports the link GitHub will
// honor rather than a second, private notion of "governing issue".
var closingKeyword = regexp.MustCompile(`(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[:\s]+#(\d+)`)

// GoverningIssue returns the issue a pull request body declares it closes, or zero.
//
// The pattern bounds nothing, and the body is arbitrary authored text: a reference wider
// than an int is an unusable number, not a large one, and it lands in a committed summary.
// An unparsable reference therefore reads as "no governing issue" rather than as whatever
// value the digits happened to produce.
func GoverningIssue(body string) int {
	match := closingKeyword.FindStringSubmatch(body)
	if match == nil {
		return 0
	}
	number, err := strconv.Atoi(match[1])
	if err != nil {
		return 0
	}
	return number
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
