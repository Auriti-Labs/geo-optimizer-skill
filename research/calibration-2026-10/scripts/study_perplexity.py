"""Calibration study FULL STUDY (spends money, capped). All eligible pages (brand-free H1), two fixed topic-level templates, 1 run each, as pre-registered in PREREGISTRATION.md.

Reads the API key from the environment variable PERPLEXITY_API_KEY (never printed, never stored). Only generic questions built from public
page H1s leave the server (no brand/domain, no user data). Hard spending cap; no retries; appends to study.jsonl.
Spending cap given on the command line (the study used 5 USD and spent about 3.58 USD).
Usage: PERPLEXITY_API_KEY=... python study_perplexity.py WORKDIR CAP_USD   (needs WORKDIR/audits.jsonl from stage 2).
Writes WORKDIR/study.jsonl (queries are built from public page headlines, and the file lists cited hosts: do not publish).
"""
import json, os, random, re, sys, time, urllib.request, urllib.parse
from pathlib import Path
BASE = Path(sys.argv[1]); CAP_USD = float(sys.argv[2]); N_PAGES = 10**6; RUNS = 1; SEED = 20261017
EST_PER_CALL = 0.0065            # $5/1000 request fee (low context) + ~1,500 tokens at $1/M, docs read 2026-10-17
key = os.environ.get("PERPLEXITY_API_KEY") or sys.exit("set PERPLEXITY_API_KEY")
audits = [json.loads(l) for l in (BASE / "audits.jsonl").read_text().splitlines()]
good = {a["url"]: a for a in audits if not a.get("error") and a.get("score") is not None and a.get("h1")}
def brand_in_h1(a):
    label = a["domain"].split(".")[0].lower()
    return len(label) >= 4 and label in a["h1"].lower().replace(" ", "").replace("-", "")
pool = [a for a in good.values() if not brand_in_h1(a)]
chosen = sorted(pool, key=lambda a: a['url'])
TEMPLATES = {"A": "What are the most reliable sources on: {h1}", "B": "Explain this topic and cite your sources: {h1}"}
out = BASE / "study.jsonl"; done = {(json.loads(l)["url"], json.loads(l)["template"]) for l in out.read_text().splitlines()} if out.exists() else set()
spent = sum(json.loads(l).get("cost_usd") or EST_PER_CALL for l in out.read_text().splitlines()) if out.exists() else 0.0
print(f"pool {len(pool)}, chosen {len(chosen)}, already {len(done)} calls, spent so far ~{spent:.3f} USD, cap {CAP_USD}", flush=True)
def host(u): return urllib.parse.urlparse(u).netloc.lower().removeprefix("www.")
def norm(u): p = urllib.parse.urlparse(u); return (p.netloc.lower().removeprefix("www.") + p.path.rstrip("/")).lower()
for a in chosen:
  for tid, tpl in TEMPLATES.items():
    q = tpl.format(h1=a["h1"])
    for run in range(1, RUNS + 1):
        if (a["url"], tid) in done: continue
        if spent + EST_PER_CALL > CAP_USD: print("CAP reached, stopping", flush=True); sys.exit(0)
        body = json.dumps({"model": "sonar", "messages": [{"role": "user", "content": q}], "max_tokens": 1024, "web_search_options": {"search_context_size": "low"}}).encode()
        req = urllib.request.Request("https://api.perplexity.ai/chat/completions", data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        rec = {"url": a["url"], "domain": a["domain"], "stratum": a["stratum"], "score": a["score"], "run": run, "template": tid, "query": q, "ts": time.strftime("%FT%TZ", time.gmtime())}
        try:
            with urllib.request.urlopen(req, timeout=60) as r: d = json.load(r)
            cites = d.get("citations") or [x.get("url") for x in d.get("search_results", []) if x.get("url")]
            usage = d.get("usage") or {}; cost = (usage.get("cost") or {}).get("total_cost") if isinstance(usage.get("cost"), dict) else None
            rec.update(model=d.get("model"), n_citations=len(cites), domain_cited=any(host(c) == a["domain"].removeprefix("www.") or host(c).endswith("." + a["domain"].removeprefix("www.")) for c in cites),
                       page_cited=any(norm(c) == norm(a["url"]) for c in cites), citation_hosts=sorted({host(c) for c in cites})[:12], cost_usd=cost, tokens=usage.get("total_tokens"))
        except Exception as e: rec["error"] = type(e).__name__ + ": " + str(e)[:80]
        with out.open("a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        spent += rec.get("cost_usd") or EST_PER_CALL; time.sleep(1)
print(f"done, spent ~{spent:.3f} USD", flush=True)
