package ghapi

// The authenticated actor's own identity.
//
// Added in 1.10 for one purpose: evidence attribution. The `Final-Disposition:` record is
// an ordinary PR comment, so any account that can comment on the repository can write one.
// Until the tool knows which login its own token speaks as, it cannot tell the record it
// wrote from one a third party posted, and it treated both as authoritative — which let an
// outsider's comment either force a permanent disposition conflict or stand in for the
// operator's own `--reason`. Attribution needs an identity, and this is where it comes
// from.

import (
	"context"
	"strings"
	"sync"
)

// AuthenticatedLogin returns the login the client's token authenticates as (`GET /user`).
//
// The result is cached for the client's lifetime: the identity behind one token cannot
// change mid-run, and every gate that needs it would otherwise spend a round trip per
// call, which NFR-008 bounds. The cache holds the answer, not the error — a transient
// failure must not be remembered as a permanent one.
//
// The login is validated on the way out. It is used as a trust comparison, so a value
// GitHub could not have issued must be refused rather than silently matched against a
// comment author.
func (c *Client) AuthenticatedLogin(ctx context.Context) (string, error) {
	c.viewerOnce.Lock()
	defer c.viewerOnce.Unlock()
	if c.viewerLogin != "" {
		return c.viewerLogin, nil
	}
	user, err := getObject[struct {
		Login string `json:"login"`
	}](ctx, c, "/user")
	if err != nil {
		return "", err
	}
	login := strings.TrimSpace(user.Login)
	if err := ValidateLogin(login); err != nil {
		return "", err
	}
	c.viewerLogin = login
	return login, nil
}

// viewerCache is embedded in Client; it is a mutex rather than a sync.Once because the
// failed lookup must stay retryable.
type viewerCache struct {
	viewerOnce  sync.Mutex
	viewerLogin string
}
