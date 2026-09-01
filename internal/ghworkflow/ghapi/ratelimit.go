package ghapi

// Rate-limit handling: the one place a 403 or 429 is distinguished from a credential
// rejection and waited out instead of reported as a failure.
//
// Through 1.9 both error types unwrapped every 403 to ErrUnauthorized. GitHub answers a
// primary rate limit with 403 (and a secondary one with 403 or 429) carrying the same
// headers, so an agent that had simply run too fast was told its credentials had been
// rejected — the one diagnosis that sends an operator to re-authenticate a token that was
// never the problem. Distinguishing the two is therefore an operability fix first: the
// retry is what makes the corrected classification useful rather than merely accurate.
//
// Only rate-limit responses are retried. A 403 that is a genuine permission refusal
// carries none of these headers, is returned on the first attempt, and still unwraps to
// ErrUnauthorized; retrying it would multiply a refusal that will never change.

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

const (
	// maxRateLimitRetries bounds how many extra attempts one request may make. The tool
	// is non-interactive and runs inside an agent turn, so the wait must be bounded by
	// something the operator can predict: at most this many sleeps of at most
	// maxRateLimitWait each.
	maxRateLimitRetries = 2
	// maxRateLimitWait caps a single sleep. GitHub's primary-limit reset can be an hour
	// away, and a tool that silently blocks for an hour is indistinguishable from a hang;
	// past this bound the operator is better served by the classified error.
	maxRateLimitWait = 30 * time.Second
	// defaultRateLimitWait is used when the response says it is rate-limited but names no
	// usable delay, which is the documented secondary-limit case.
	defaultRateLimitWait = 2 * time.Second
)

// waitFor sleeps for d, or returns early when the caller's context is done — a cancelled
// run must not be held for the rate-limit window it was about to wait out.
func waitFor(ctx context.Context, d time.Duration) error {
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

// rateLimited reports whether resp is a rate-limit refusal and, if so, how long to wait.
//
// The three signals are checked in GitHub's own order of authority: an explicit
// `Retry-After` (secondary limits), then an exhausted `x-ratelimit-remaining` with an
// `x-ratelimit-reset` epoch (primary limits), then a bare 429, which is a rate limit by
// status alone even when a proxy stripped the headers.
func rateLimited(resp *http.Response) (time.Duration, bool) {
	if resp.StatusCode != http.StatusForbidden && resp.StatusCode != http.StatusTooManyRequests {
		return 0, false
	}
	if wait, ok := retryAfter(resp.Header.Get("Retry-After")); ok {
		return clampWait(wait), true
	}
	if strings.TrimSpace(resp.Header.Get("X-RateLimit-Remaining")) == "0" {
		if reset, err := strconv.ParseInt(strings.TrimSpace(resp.Header.Get("X-RateLimit-Reset")), 10, 64); err == nil {
			return clampWait(time.Until(time.Unix(reset, 0))), true
		}
		return defaultRateLimitWait, true
	}
	if resp.StatusCode == http.StatusTooManyRequests {
		return defaultRateLimitWait, true
	}
	return 0, false
}

// retryAfter reads the header in both forms RFC 9110 permits: delay-seconds and an HTTP
// date. GitHub sends seconds, but a proxy in front of it may rewrite the header, and a
// date parsed as zero would turn a rate limit into a busy loop.
func retryAfter(header string) (time.Duration, bool) {
	value := strings.TrimSpace(header)
	if value == "" {
		return 0, false
	}
	if seconds, err := strconv.Atoi(value); err == nil {
		return time.Duration(seconds) * time.Second, true
	}
	if when, err := http.ParseTime(value); err == nil {
		return time.Until(when), true
	}
	return 0, false
}

// clampWait keeps a delay inside [0, maxRateLimitWait]. A negative or absent reset means
// the window has already passed, so the retry is immediate rather than skipped.
func clampWait(d time.Duration) time.Duration {
	switch {
	case d < 0:
		return 0
	case d > maxRateLimitWait:
		return maxRateLimitWait
	default:
		return d
	}
}

// doWithRetry issues the request build produces, reads its whole body, and retries a
// rate-limit refusal up to maxRateLimitRetries times.
//
// It is the single transport step both request shapes use — the GET path in ghapi.go and
// the write path in mutations.go — so the retry policy cannot drift between reads and
// writes. build is a factory rather than a request because a retried write must present a
// fresh body reader; reusing a consumed one would send an empty payload on the second
// attempt, which for a merge or a field write is worse than the rate limit.
//
// Retrying a write is safe precisely because a rate-limited request was refused before it
// was applied: 403 and 429 are the two statuses GitHub returns without performing the
// mutation. Nothing else is retried here.
//
// The last return reports that the final response was still a rate-limit refusal, which
// is what the caller stamps onto its error type so the failure classifies as
// ErrRateLimited instead of ErrUnauthorized.
func (c *Client) doWithRetry(ctx context.Context, describe string,
	build func() (*http.Request, error),
) (*http.Response, []byte, bool, error) {
	for attempt := 0; ; attempt++ {
		req, err := build()
		if err != nil {
			return nil, nil, false, err
		}
		resp, err := c.http.Do(req)
		if err != nil {
			return nil, nil, false, fmt.Errorf("%w: %s: %w", ErrUnreachable, describe, err)
		}
		body, readErr := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
		_ = resp.Body.Close()
		if readErr != nil {
			return nil, nil, false, fmt.Errorf("%w: reading the response for %s: %w",
				ErrUnreachable, describe, readErr)
		}
		wait, limited := rateLimited(resp)
		if !limited {
			return resp, body, false, nil
		}
		if attempt >= maxRateLimitRetries {
			return resp, body, true, nil
		}
		if err := waitFor(ctx, wait); err != nil {
			return nil, nil, false, fmt.Errorf("%w: waiting out the rate limit for %s: %w",
				ErrUnreachable, describe, err)
		}
	}
}
