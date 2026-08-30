package ghapi

// The GraphQL half of the client, and the only part of the tool that is not REST.
//
// Through 1.6 the tool was REST-only (OQ-002). Version 1.7 has to reach three facts and
// two mutations that the REST API does not express at all, and none of them can be worked
// around by reading something else:
//
//   - `mergeStateStatus` and `reviewDecision` are GraphQL-only fields on PullRequest. REST
//     reports `mergeable` (can it merge) but nothing about whether branch protection would
//     currently let it, and no REST field summarizes review outcome.
//   - Marking a draft ready is the `markPullRequestReadyForReview` mutation. REST's PATCH
//     on a pull request accepts `draft` only for setting it to true, never for clearing it.
//   - Enabling auto-merge is the `enablePullRequestAutoMerge` mutation. REST has no
//     auto-merge write; it only reports the resulting `auto_merge` object.
//
// Both mutations address the PR by GraphQL node id, which is why PullRequest carries
// NodeID: the paired Ready and Merge commands take the id from the REST read they already
// performed rather than spending a lookup call on it (NFR-008).
//
// A GraphQL failure is an operational failure like any other API failure, including the
// case that has no REST analogue: a 200 response carrying a nonempty `errors` array. That
// shape is the trap here — treating HTTP status as the verdict would read a refused
// mutation as a completed one.

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

// graphqlPath is the endpoint every query and mutation below posts to.
const graphqlPath = "/graphql"

// Merge methods, in the spelling each API surface demands: REST takes the lowercase form
// in its request body, GraphQL takes the uppercase enum. Callers use the REST spelling and
// graphqlMergeMethod converts, so no caller has to remember which surface it is on.
const (
	MergeMethodMerge  = "merge"
	MergeMethodSquash = "squash"
	MergeMethodRebase = "rebase"
)

type graphqlRequest struct {
	Query     string         `json:"query"`
	Variables map[string]any `json:"variables,omitempty"`
}

type graphqlError struct {
	Type    string `json:"type"`
	Message string `json:"message"`
}

type graphqlResponse struct {
	Data   json.RawMessage `json:"data"`
	Errors []graphqlError  `json:"errors"`
}

// graphql performs one GraphQL operation and decodes `data` into out.
//
// The `errors` array is checked before `data` is looked at, because GraphQL returns both:
// a partially-resolved `data` alongside errors is still a failed operation for every
// caller here, all of which need a complete answer or none.
func (c *Client) graphql(ctx context.Context, query string, variables map[string]any, out any) error {
	var envelope graphqlResponse
	if err := c.send(ctx, http.MethodPost, graphqlPath,
		graphqlRequest{Query: query, Variables: variables}, &envelope); err != nil {
		return err
	}
	if len(envelope.Errors) > 0 {
		messages := make([]string, 0, len(envelope.Errors))
		for _, e := range envelope.Errors {
			if e.Type != "" {
				messages = append(messages, e.Type+": "+e.Message)
				continue
			}
			messages = append(messages, e.Message)
		}
		return &GraphQLError{Messages: messages}
	}
	if out == nil {
		return nil
	}
	if err := json.Unmarshal(envelope.Data, out); err != nil {
		return fmt.Errorf("%w: the GraphQL response data: %w", ErrDecode, err)
	}
	return nil
}

// GraphQLError is a GraphQL operation that returned errors, whatever its HTTP status was.
type GraphQLError struct {
	Messages []string
}

func (e *GraphQLError) Error() string {
	return "the GitHub GraphQL API returned errors: " + strings.Join(e.Messages, "; ")
}

// Operational marks GraphQL failures alongside every other API failure (exit 3).
func (e *GraphQLError) Operational() bool { return true }

// graphqlMergeMethod converts a REST merge method to the GraphQL enum, refusing anything
// outside the three GitHub accepts rather than sending a value the schema will reject.
func graphqlMergeMethod(method string) (string, error) {
	switch strings.ToLower(strings.TrimSpace(method)) {
	case MergeMethodMerge:
		return "MERGE", nil
	case MergeMethodSquash:
		return "SQUASH", nil
	case MergeMethodRebase:
		return "REBASE", nil
	default:
		return "", fmt.Errorf("merge method %q is not one of merge, squash, rebase", method)
	}
}
