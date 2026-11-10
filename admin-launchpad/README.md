# Calitoy Private Admin Launchpad

This is an admin-only Chrome launchpad, **not a public marketing website**. The initial snapshot contains the 68 repositories visible to the connected GitHub account on 2026-11-10. Deployment status, live URLs, admin URLs and hosting consoles are deliberately unverified.

## Go live safely
1. Merge this PR into the **private** CalitoyCorp repository, after review.
2. Configure repository secret `INVENTORY_GITHUB_TOKEN` with read-only repository metadata access to all intended repos. The default GitHub Actions token typically cannot enumerate other private repositories.
3. Run the **Refresh private admin launchpad inventory** workflow once manually, verify the private snapshot, and check subsequent runs.
4. Serve `admin-launchpad/` behind a real identity-aware access proxy (Cloudflare Access, authenticated internal hosting, or equivalent). **Never use public GitHub Pages for this directory.** A password box in client HTML is not authentication.
5. Once hosted at an authenticated URL, open Chrome Settings > On startup > Open a specific page or set of pages, and add that URL.

## Catalog curation
Each entry may be manually tagged with `verified: true`, `stage` (`Live`, `Staging`, `Development`, `Unknown`, `Archived`), `site`, `admin`, `host`, and `note`. The refresh script preserves verified metadata by repository identity. Do not add credentials or secret URLs.

## Operational caveats
- GitHub cron is best effort; the scheduled workflow is checked for **08:00 America/Los_Angeles** using both UTC DST offsets, but GitHub may start late, including past the check hour. For an exact-time SLA use an external scheduler.
- The workflow commits updated data on the default branch. No public deployment is configured by this PR.
- This is a repository inventory, not a one-row-per-app inventory yet. Monorepo app discovery and hosting verification are follow-up integrations.
- Access-restricted hosting remains a prerequisite for a usable private Chrome start page.
