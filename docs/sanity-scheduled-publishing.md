# Scheduled publishing with Sanity

GeoReady is a static Astro site. A content change in Sanity therefore needs two
separate actions: promote the article to `published`, then rebuild the static
site and its sitemap. The `Publish scheduled Sanity articles` workflow performs
both actions every ten minutes and can be run manually from GitHub Actions.

## Editorial flow

For each future article, set:

- `status` to `scheduled`;
- `scheduledFor` to the intended UTC publication timestamp;
- all required public metadata, body, and slug before the scheduled time.

Until the workflow promotes the document, scheduled content is excluded from
the article routes, guide hubs, and `sitemap.xml`. Legacy articles that do not
have a `status` field remain public for backwards compatibility.

## One-time production configuration

Create these **repository secrets** in GitHub Actions. Never commit their
values, add them to `.env` files tracked by Git, or paste them into workflow
logs.

| Secret | Required value | Purpose |
| --- | --- | --- |
| `SANITY_API_TOKEN` | A Sanity API token with the minimum Editor permission for the production dataset. | Promotes only due documents from `scheduled` to `published`. |
| `GEOREADY_DEPLOY_WEBHOOK_URL` | An authenticated endpoint that starts the production static-site deployment. | Rebuilds GeoReady after at least one article was published. |

The deployment webhook must check out the current production revision and run,
in this order:

```bash
npm --prefix frontend run generate:sitemap
npm --prefix frontend run build
```

Both commands independently stop if any article is past `scheduledFor` but has
not yet been promoted to `published`; this prevents a manual rebuild from
deploying an incomplete site or sitemap. The endpoint must deploy the resulting
`frontend/dist/` atomically. The URL itself is a secret because it authenticates
the deployment trigger.

## Verification and recovery

1. Run **Publish scheduled Sanity articles** manually with `dry_run=true`.
   The log lists only the documents already due and changes nothing.
2. Run it again with `dry_run=false`; it publishes the due documents and calls
   the deployment endpoint only when at least one document changed.
3. Confirm the article URL, `/guides/`, and `/sitemap.xml` are live before
   submitting changed URLs to IndexNow.

If the deployment endpoint fails, the workflow fails visibly. Do not manually
change an article back to `scheduled`: fix the deployment endpoint, then rerun
the workflow manually with `dry_run=false` and `force_deploy=true`. That forces
the static rebuild even when the prior run already promoted the documents.
Documents already promoted to `published` remain safe and the site has no
route-level exposure of drafts.

## Local commands

```bash
npm --prefix frontend run sanity:publish-due:dry-run
npm --prefix frontend run sanity:check-schedule
SANITY_API_TOKEN=... npm --prefix frontend run sanity:publish-due
```

The dry run uses the public Sanity dataset and never needs a write token. The
write command requires the token only in the process environment and never
prints it. `sanity:check-schedule` is read-only and exits with an error while
one or more scheduled articles are overdue; use it before a manual deployment.
