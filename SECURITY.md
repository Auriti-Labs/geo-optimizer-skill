# Security Policy

## Reporting a Vulnerability

We take security seriously. If you believe you have found a security
vulnerability in GeoReady, please report it to us privately before
disclosing it publicly.

**Please do NOT open a public GitHub issue for security findings.**

## How to report

Send a private report to the maintainer:

- **Email:** `juan@geoready.dev`
- **GitHub:** open the repository's **Security** tab and click
  **Report a vulnerability**
  (https://github.com/Auriti-Labs/geo-optimizer-skill/security/advisories/new).
  The report is visible only to you and the maintainers.

Include in your report:

- The affected endpoint / file / component
- A clear step-by-step reproduction (repro)
- The impact you observe
- Whether you consider it critical and why

## Scope

This policy covers:

- The `geoready.dev` website and its public endpoints
- The `geo-optimizer-skill` package (`geo` CLI, FastAPI web demo, MCP server)
- The build and CI configuration in this repository

Out of scope:

- Third-party services we integrate with (Sanity, Google Analytics, etc.)
- Known, documented limitations

## What happens next

1. We acknowledge your report within **5 business days**.
2. We triage and validate the finding with a reproducible proof.
3. If confirmed, we fix it, and coordinate disclosure so you can publish
   responsibly once a patch is available.

## Bounty / recognition

We currently do not run a paid bounty program. We do not negotiate or pay
for findings before they are demonstrated with a verified repro.

We gratefully credit verified reporters in our release notes unless they
prefer to stay anonymous.

## Public disclosure

We follow responsible disclosure: reporters who give us a head start
(ideally 90 days) before publishing will have their finding credited and
taken seriously. Reports sent through unofficial channels (e.g. a DM
requesting payment before showing any proof) will not be treated as valid
security submissions.

Thanks for helping keep GeoReady safe.
