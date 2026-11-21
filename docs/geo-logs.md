# geo logs

Analyze server access logs for AI crawler activity.

## Usage

```bash
geo logs --file /var/log/nginx/access.log
geo logs --file access.log --format json

# Check each crawler visit by its source address (offline, with the vendors' range files in a folder)
geo logs --file access.log --ip-ranges ./ranges

# Same, downloading the 7 vendor files (7 requests, no log data sent)
geo logs --file access.log --fetch-ip-ranges
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--file` | required | Path to server access log |
| `--format` | text | Output format: `text` or `json` |
| `--ip-ranges` | off | Folder with the vendors' published range files; checks each visit's source address, offline |
| `--fetch-ip-ranges` | off | Same check, downloading the files from the vendors' URLs (7 GET requests) |

## Supported log formats

- **Apache/Nginx combined** — standard `combined` log format
- **JSON lines** — CloudFront, Vercel, custom (fields: `user_agent`, `path`, `timestamp`)

## Bot detection

Uses the `AI_BOTS` registry (27 bots). Case-insensitive User-Agent matching.

## Source address check

A visit that claims a bot name proves nothing by itself: anyone can send `GPTBot` as a User-Agent. With `--ip-ranges` or
`--fetch-ip-ranges` every such visit is compared with the address ranges the vendor publishes. The files, by name:
`gptbot.json`, `searchbot.json`, `chatgpt-user.json` (OpenAI), `googlebot.json` (Google), `perplexitybot.json`,
`perplexity-user.json` (Perplexity), `bingbot.json` (Microsoft). Their URLs are in `CRAWLER_RANGE_SOURCES`; each answered
HTTP 200 with `{"creationTime", "prefixes": [{"ipv4Prefix" | "ipv6Prefix"}]}` when checked on 2026-11-21.

For each bot the report gives visits, **verified** (inside a published range), **outside the ranges** and visits with no usable
address. A bot whose vendor publishes no such file that was checked (ClaudeBot, Claude-SearchBot, Applebot and the others) is shown as
*no published ranges*: it is unverifiable, not clean.

What "outside the ranges" means. A spoofed name, or an address the vendor has not listed. Measured on a real log of 362,260 lines: for
Bingbot and Googlebot every sampled "verified" address passed a forward-confirmed reverse DNS check (40 of 40 each) and every sampled
"outside" address failed it (0 of 32 and 0 of 40). For GPTBot, 18 of 25 addresses outside OpenAI's file belonged to Microsoft Azure, which
runs OpenAI's own crawlers and also anybody's virtual machines: nothing independent says which. Read the publication dates printed above
the table against your log period.

It is an address check, **not** an RFC 9421 signature check: standard access logs do not record the `Signature` headers, so a
signature cannot be verified from a log. Behind a proxy or CDN the first field of the log must be the visitor's address, not the proxy's.

## Python API

```python
from geo_optimizer.core.log_analyzer import analyze_log_file

result = analyze_log_file("/var/log/nginx/access.log")
```
