# Admin panel deployment checklist

## Render environment

The web service must receive all three values:

- `ADMIN_ID`: login identifier.
- `ADMIN_PASS`: password.
- `ADMIN_SESSION_SECRET`: independently generated random secret, minimum 32 bytes.

The existing `Admin Pass` Environment Group can hold all three. Link that group to the **rti-intelligence-backend** web service. Creating a group alone does not attach it to a service. Never paste secret values into GitHub, README, issues, pull requests, or chat.

## Login and security

- Open `https://rti-intelligence-backend.onrender.com/admin`.
- Sign in with `ADMIN_ID` and `ADMIN_PASS`.
- The server issues a signed, 8-hour HttpOnly, Secure, SameSite=Strict cookie.
- Admin POST actions require a session CSRF token.
- Dashboard, source intake and legal-document verification APIs reject anonymous requests.
- Logout removes the browser cookie. Changing the admin password or rotating the signing secret invalidates existing sessions.

## Acceptance checks

1. Anonymous `GET /api/v1/admin/dashboard` returns HTTP 401.
2. Wrong credentials return HTTP 401.
3. Correct credentials return HTTP 200 and set a Secure + HttpOnly session cookie.
4. Authenticated dashboard reports `connected` only after the Supabase database connection succeeds.
5. Source intake rejects non-allowlisted domains and requires CSRF.
6. Document verification requires an authenticated session, explicit confirmation and a review note.
7. The crawler worker must be deployed separately and connected to the same database before queued sources are processed.

## Current limitation

The Render MCP connection can inspect the web service but does not expose Environment Group attach/list operations. If the group is not already linked, attach it manually in Render Dashboard under the service's Environment settings. Do not claim the admin panel is live until the PR is merged, the service deploys the new commit, and the acceptance checks pass.
