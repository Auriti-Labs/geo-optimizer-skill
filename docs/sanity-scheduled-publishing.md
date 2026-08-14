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

### A green workflow does not prove the site was deployed

The claim above holds only when the endpoint actually rejects a bad request. On
2026-08-13 it did not: `GEOREADY_DEPLOY_WEBHOOK_URL` held a placeholder pointing
at an echo service, which answers `200` to any POST, so `curl --fail` passed and
every step reported success while the article stayed `404` for half an hour.

Nothing caught it earlier because the deployment step is guarded by
`if: published_count != '0'`, and the roughly forty runs since the workflow
reached the default branch had all found nothing due. A step behind a condition
that has never been met is not tested code — it is code that has never run. Read
the step's output, not the job's conclusion.

## Reconciliation (the safety net)

Because publishing is push-based, a broken link anywhere in the chain leaves an
article promoted in Sanity and absent from the site, with no failure signal. The
reconciler closes that gap by pulling instead of pushing:

- `frontend/scripts/check-live-drift.mjs` compares the live Sanity articles
  against the public sitemap and exits `10` when at least one live article is not
  served, `0` when aligned, `1` on any error. It needs no token, deploys nothing,
  and cannot deploy anything — it only decides.
- `frontend/scripts/reconcile-live-site.sh` runs on the server, and calls
  `rebuild-geo-web.py` only on exit `10`. Install it hourly in cron:

  ```
  17 * * * * /home/debian/geo-optimizer-skill/frontend/scripts/reconcile-live-site.sh
  ```

Three properties are deliberate. An error in the check (`1`) never triggers a
deployment, so an unreachable Sanity or an unparsable sitemap cannot cause a
rebuild "just in case". A `flock` prevents overlapping runs, since a rebuild
takes over two minutes. And after the rebuild the check runs again: a rebuild
that reports success without resolving the drift is logged as needing a human,
rather than assumed to have worked — which is precisely the failure mode above.

An aligned run logs nothing. Twenty-four "all fine" lines a day would bury the
ones that matter.

This makes the webhook secret non-critical: with the reconciler installed, a
broken deployment trigger delays publication by up to an hour instead of
dropping it silently.

## Local commands

```bash
npm --prefix frontend run sanity:publish-due:dry-run
npm --prefix frontend run sanity:check-schedule
npm --prefix frontend run site:check-drift
SANITY_API_TOKEN=... npm --prefix frontend run sanity:publish-due
```

The dry run uses the public Sanity dataset and never needs a write token. The
write command requires the token only in the process environment and never
prints it. `sanity:check-schedule` is read-only and exits with an error while
one or more scheduled articles are overdue; use it before a manual deployment.
`site:check-drift` is read-only too and answers a different question: whether
what is already published is actually being served.
