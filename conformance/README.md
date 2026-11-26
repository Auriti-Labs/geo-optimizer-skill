# Conformance cases

Shared test cases for the checks that exist in both the Python engine (`src/geo_optimizer`) and the JS core
(`integrations/core`). One JSON file per rule:

| File | Rule | Python | JS |
|------|------|:------:|:--:|
| `robots.json` | `robots-ai-bots`: is a bot blocked on a path (RFC 9309) | yes | yes |
| `canonical.json` | `canonical`: pass / warn / fail | yes | yes |
| `jsonld.json` | `jsonld-valid`: syntactically valid JSON-LD | yes | yes |
| `sitemap.json` | `sitemap-lastmod`: valid W3C datetime | no | yes |
| `sitemap-indexable.json` | `sitemap-indexable`: 4xx/5xx or noindex pages in the sitemap | no | yes |

Each case has `name`, `input`, `expect` and `engines` (the engines that run it). A case that only `js` runs is a rule
the Python engine has no counterpart for; it is still here so the JS behaviour is written down once.

Run them:

```bash
pytest tests/test_conformance.py
cd integrations/core && npm test
```

Rules for adding a case: one behaviour per case, a name that states it, and no case that only one engine can pass.
If the two engines disagree on a case, that is a finding: fix the engine that is wrong, never the expectation to
match the engine. For `robots.json` use paths other than `/` (the Python engine reads `/` as a site-wide status).
