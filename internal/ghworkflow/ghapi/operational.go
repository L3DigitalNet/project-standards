package ghapi

// Operational-failure marking: the cross-package contract that decides exit 3.
//
// Spec IR-005 splits failures four ways, and only one of them belongs to this package: an
// authentication, transport, non-2xx API, decode, or pagination-truncation failure is an
// *operational* failure the operator must clear before the tool can answer at all. Domain
// findings and usage refusals are not errors from here — they are produced by the command
// layer — so nothing in this file may leak into those classes.
//
// The marker is a structural interface rather than a shared sentinel because the
// classifier lives in package cli and this package must not import it (that would close an
// import cycle through the command packages). cli asks `errors.As` for any value in the
// chain implementing `interface{ Operational() bool }` returning true and exits
// cli.ExitOperational. Package ghauth carries its own four-line copy of the same marker for
// the same reason; both are ends of one contract, so a change here needs the counterpart in
// internal/ghworkflow/ghauth/token.go checked in the same edit.
//
// Identity refusals (identity.go) deliberately carry no marker: a mistyped `--repo` is the
// operator's input error, not an operational failure, and must stay exit 2.

import "errors"

// operationalError is a sentinel that marks itself and everything wrapping it as an
// operational failure.
type operationalError struct{ message string }

func (e *operationalError) Error() string { return e.message }

// Operational satisfies the cross-package marker interface described above.
func (e *operationalError) Operational() bool { return true }

var (
	// ErrUnreachable marks a transport-level failure: DNS, dial, TLS, timeout.
	ErrUnreachable error = &operationalError{"github api is unreachable"}
	// ErrUnauthorized marks a credential rejection (401/403).
	ErrUnauthorized error = &operationalError{"github rejected the credentials"}
	// ErrDecode marks a response that arrived but could not be read as the documented
	// shape, which is an API-contract failure rather than anything the operator typed.
	ErrDecode error = &operationalError{"the github response could not be decoded"}
	// ErrPaginationTruncated marks a list read whose advertised total disagrees with the
	// number of entries actually decoded, with no `rel="next"` link left to explain the
	// difference (spec NFR-007, closing DEV-024).
	//
	// This sentinel is distinct on purpose. A short list is the one failure mode that
	// otherwise looks exactly like success: the Merge phase would read a truncated check
	// set as "every required check passed" and admit a pull request on evidence it never
	// saw. Callers that must fail closed on unknown evidence (ERR-013) match this
	// specifically rather than treating every read error alike.
	ErrPaginationTruncated error = &operationalError{"the github list response was truncated"}
	// ErrPaginationLimit marks a server that kept advertising rel="next" past maxPages.
	ErrPaginationLimit error = &operationalError{"github pagination exceeded its page ceiling"}
	// ErrPaginationRefused marks a rel="next" link the client would not follow because it
	// leaves the API origin the bearer token belongs to (NFR-007, ERR-010).
	ErrPaginationRefused error = &operationalError{"the github pagination link left the API origin"}
)

// Operational marks every non-2xx read, matching RequestError.
func (e *APIError) Operational() bool { return true }

// Operational marks every non-2xx write, matching APIError.
func (e *RequestError) Operational() bool { return true }

// IsOperational reports whether err carries the operational marker anywhere in its chain.
// It is the same question package cli asks; exposing it here keeps this package's own
// tests honest about which errors are marked without duplicating the interface literal.
func IsOperational(err error) bool {
	var marked interface{ Operational() bool }
	return errors.As(err, &marked) && marked.Operational()
}
