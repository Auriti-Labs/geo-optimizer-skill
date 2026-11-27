# Conformance cases

Shared test cases for the checks that exist in both the Python engine (`src/geo_optimizer`) and the JS core
(`integrations/core`). One JSON file per rule:

| File | Rule | Python | JS |
|------|------|:------:|:--:|
| `robots.json` | `robots-ai-bots`: is a bot blocked on a path (RFC 9309) | yes | yes |
| `canonical.json` | `canonical`: pass / warn / fail | yes | yes |
| `jsonld.json` | `jsonld-valid`: syntactically valid JSON-LD, per block (`input.block`) and per page (`input.html`) | yes | yes |
| `sitemap.json` | `sitemap-lastmod`: valid W3C datetime | no | yes |
| `sitemap-indexable.json` | `sitemap-indexable`: 4xx/5xx or noindex pages in the sitemap | no | yes |

Each case has `name`, `input`, `expect` and `engines` (the engines that run it). A case that only `js` runs is a rule
the Python engine has no counterpart for; it is still here so the JS behaviour is written down once.

Run them:

```bash
pytest tests/test_conformance.py
cd integrations/core && npm test
```

Rules for adding a case: one behaviour per case, a name that states it, and no case that only one engine can pass,
unless it is a known divergence (below). If the two engines disagree on a case, that is a finding: fix the engine that
is wrong, never the expectation to match the engine. For `robots.json` use paths other than `/` (the Python engine
reads `/` as a site-wide status). A `robots` input may be a list of `{text, repeat}` parts that the runner joins: the byte-limit cases (500 KiB, counted in UTF-8 bytes in both engines) use it so the file does not carry the text.

## Page cases for JSON-LD

A `jsonld.json` case whose input is `html` goes through the extraction each engine really uses, not through a bare
JSON parser: Python builds an `html.parser` soup (as `audit.py` does) and reads `audit_schema(...).json_parse_errors`;
JS calls `checkJsonLd`, which extracts with `jsonLdBlocks` and validates with `jsonLdStatus`. The expectation is the
number of invalid blocks, `{"invalid": n}`, the only quantity both engines report. Shared page cases cover only what
both engines do the same way.

The block cases (`input.block`) still run Python through `json.loads` directly, not through the audit path. That is
why the block case `empty block` passes for Python while the audit itself skips an empty block.
The page-level audit of both engines skips such a block (the former D2, closed).

## Self-checks

Both runners fail, instead of skipping, when:

- one of the five expected files is missing, or a file carries a different `rule`;
- a file has no cases;
- a case has no `name`/`input`/`expect`, or its `engines` is missing, empty, duplicated or holds a value other than
  `python` or `js`;
- a case is run by no engine, or declares an engine that has no runner for its rule;
- fewer cases run than declare that engine (Python: collected; JS: executed). A partial pytest run (`-k`) skips the
  collected count, since it is not comparable.

## Known divergences

A case that only one engine passes is marked with `divergence`, `note` (what the other engine does) and `reason` (why
the expectation is right), and lists only the engine that passes. The expectation is the normative behaviour; the
case moves to both engines once the other engine is fixed.

| ID | Cases | Divergence | Normative reference | Owner | Closing criterion |
|----|-------|------------|---------------------|-------|-------------------|
| D1 | `NaN is not JSON`, `Infinity is not JSON`, `-Infinity is not JSON`, `page: NaN inside a block`, `page: Infinity inside a block` (`js`) | Python's `json.loads` accepts `NaN`, `Infinity` and `-Infinity`: the block runner says valid and the audit counts no parse error. | RFC 8259 §6 (not permitted number values); JSON-LD 1.1 requires a JSON document | Python engine: `utils/jsonld.py` (`iter_jsonld_objects`) | Python rejects these constants (e.g. `parse_constant` that raises) in the audit path and the block runner; the five cases list `python` too. |
| D3 | `page: the type value is matched case-insensitively`, `page: a type value with parameters is still JSON-LD` (`js`) | Python finds scripts with an exact `type="application/ld+json"` match, so `Application/LD+JSON` or `application/ld+json; charset=utf-8` is never read. | RFC 2045, RFC 6838 (case-insensitive names, parameters) | Python engine: `utils/jsonld.py`, `core/audit_schema.py` | Python matches the media type essence case-insensitively, ignoring parameters; both cases list `python` too. |
| D4 | `page: an HTML comment inside a script is literal text` (`python`) | JS removes every `<!-- -->` from the page before extracting, script bodies included, so it validates a body that is not what the page carries. | HTML Living Standard (script content is raw text) | JS core: `integrations/core/src/html.js` (`withoutComments` in `jsonLdBlocks`) | JS strips comments only outside script bodies; the case lists `js` too. |
| D5 | none (a fixture over 512 KiB is not kept in the repo) | Python skips a script body larger than `SCHEMA_JSONLD_MAX_BYTES` (512 KiB, counted in characters) without counting it; JS validates it whatever its size. Observed: a 600 KB invalid block gives Python 0, JS 1. | none: a resource limit, not a format rule | Both: `models/config.py` and the JS core | A shared size limit (or a documented "not judged" outcome) in both engines, with a generated case. |
| D6 | `noindex inside a template is not a directive …` (`js`, in `canonical.json`) | Python's `html.parser` reads the content of a `<template>` as live markup, so a `noindex` meta inside it counts as a directive; JS ignores `<template>` content. | HTML Standard (template contents are an inert document fragment) | Python engine: the robots-meta readers (candidates `core/audit.py`, `core/audit_google_ai.py`; not yet traced) | Python ignores `<template>` content; the case lists `python` too. |
