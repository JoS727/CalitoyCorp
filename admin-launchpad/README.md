# Calitoy master admin: replaces the merch-only landing page

This is a private app/repository directory, not the merchandise approval screen.
The intended home is `admin.calitoy.com/`. Existing merch files are left in source
as a non-operational module; this does not claim they work or publish them as the
master dashboard.

## Security correction

CalitoyCorp is PUBLIC. Never commit a private repository inventory, private catalog,
access tokens, or owner email configuration here. The earlier tracked inventory
was removed from the current branch, and public Pages publishing excludes this
entire directory. That removal does NOT erase earlier commits, PR diffs, old Pages
branches, caches, or copies. Review exposure and arrange GitHub history/cache
cleanup separately; no destructive history rewrite is performed by this change.

## Architecture

- `worker.mjs` serves the root HTML directly, with NO Static Assets binding.
- Cloudflare Worker-level Access authenticates each request. `core.mjs` additionally
  requires Cloudflare's server-provided `ctx.access` identity and an exact approved
  email. Incoming email headers and `?k=` values cannot authenticate.
- Both HTML and API fail closed without identity/configuration. Friendly access and
  loading errors replace the white page. Private responses are `no-store`.
- `INVENTORY` is a PRIVATE Cloudflare KV binding. `inventory:latest` holds the last
  successful snapshot. `catalog:overrides` holds manually confirmed app/admin/host
  links and statuses. No snapshot is written to Git or public workflow artifacts.
- The sync preserves the last snapshot if fetching fails, returns empty, or loses
  previously visible repositories. An explicit workflow input permits reviewed
  deletions/access reductions. Token scope limits completeness.
- The UI distinguishes repositories from deployed apps; unknown links stay unknown.
  Monorepo apps are not automatically inferred by this first version.

## Deployment (not completed by committing this code)

1. Identify and export the CURRENT Cloudflare route/Worker serving
   `admin.calitoy.com` before replacing it. Do not overwrite an unidentified Worker.
2. Create a private KV namespace. Copy `wrangler.example.jsonc` to the ignored local file
   `wrangler.local.jsonc`, fill in namespace ID and owner-approved email(s), and deploy the
   new Worker with Wrangler. No custom domain or workers.dev URL is enabled by the
   example configuration; initially it has no public route.
3. In Workers & Pages > this Worker > Access, enable **Worker-level Access** for the
   owner only. This Worker uses the platform's `ctx.access` identity and must NOT
   be changed to an assets-based Worker without revisiting authentication.
4. Attach `admin.calitoy.com` as its custom domain only after the Access policy is
   in place. Verify signed-out login, an unauthorized account, and the approved
   owner's session. Keep the old route export for rollback; do not restore public
   private-inventory files as part of rollback.
5. Configure GitHub environment `admin-inventory`:
   - Secret `INVENTORY_GITHUB_TOKEN`: read-only GitHub metadata access to all
     intended repositories. The ordinary per-repo GITHUB_TOKEN is insufficient.
   - Secret `ADMIN_KV_API_TOKEN`: KV read/write restricted to the required account.
   - Variables `CLOUDFLARE_ACCOUNT_ID` and `ADMIN_KV_NAMESPACE_ID`.
   - Review environment protection: unattended schedules cannot wait for daily
     manual approvals. Keep production code/deploy approvals separate from sync.
6. Run **Refresh private master admin inventory** manually and verify the result in
   an authenticated session. The daily schedule is 08:00 America/Los_Angeles, with
   native timezone handling. GitHub may delay or drop scheduled runs. A snapshot
   older than 27 hours is visibly flagged. Reload fetches the saved snapshot, not
   a new GitHub scan; the page rechecks the saved snapshot every five minutes.
7. Only after a successful private deployment, use the protected domain in Chrome
   Settings > On startup > Open a specific page or set of pages.

## Private catalog shape (store in KV, not this public repository)

`catalog:overrides` is an object keyed by full repository name. Each record supports
`verified` (boolean), `stage` (Live, Staging, Development, Not operational, Unknown,
Archived), `site`, `admin`, `host`, and `note`. URLs must be HTTPS with no embedded
credentials. Verification records a human confirmation, not continuous health.
Mark the old merch app **Not operational**, not Live. Never assume `/admin` exists
by appending it to a homepage. GitHub homepage values are explicitly unverified.

## Tests

    node --test admin-launchpad/tests/core.test.mjs
    python3 -m unittest discover -s admin-launchpad/tests -p 'test_*.py'

These are local/CI logic tests, not proof of Cloudflare deployment, real Access
configuration, production browser behavior, or a successful scheduled sync.

## Primary documentation

- https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- https://developers.cloudflare.com/workers/wrangler/configuration/
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
