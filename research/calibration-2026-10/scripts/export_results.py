"""Builds the published results.csv from audits.jsonl (stage 2) and study.jsonl (full study).

Usage: python export_results.py WORKDIR OUTPUT.csv

This step was missing from the original run: the published results.csv came from an earlier, unsaved export. This
script was written afterwards from the column description in the README and checked against the published table
(same 341 rows once both are sorted; the row order of the published file may differ because the rows are shuffled
there, here with the study seed). It drops the domain, the page address and the headline, keeps the band of the
Tranco rank and the natural log of the exact rank rounded to one decimal.
"""
import csv, json, math, random, sys
from pathlib import Path

BASE = Path(sys.argv[1]); OUT = Path(sys.argv[2]); SEED = 20261017
EDGES = [0, 1000, 3000, 10000, 30000, 100000, 200000, 400000, 600000, 800000, 1000000]  # as in stage1_sample.py
CATS = ["google_ai", "robots", "schema", "content", "brand_entity", "meta", "llms", "signals", "ai_discovery", "negative_penalty"]
COLUMNS = ["rank_band", "ln_rank_1dp", "score", *CATS, "words", "blocks_ai_bot",
           "domain_cited_A", "domain_cited_B", "page_cited_A", "page_cited_B"]

audits = {}
for line in (BASE / "audits.jsonl").read_text().splitlines():
    r = json.loads(line); audits[r["url"]] = r
rows = {}
for line in (BASE / "study.jsonl").read_text().splitlines():
    s = json.loads(line)
    if s.get("error"):
        continue
    a = audits[s["url"]]
    band = f"{EDGES[a['stratum'] - 1] + 1}-{EDGES[a['stratum']]}"
    row = rows.setdefault(s["url"], {
        "rank_band": band, "ln_rank_1dp": round(math.log(a["rank"]), 1), "score": a["score"],
        **{c: (a.get("breakdown") or {}).get(c) for c in CATS},
        "words": a["words"], "blocks_ai_bot": int((a.get("bots_blocked") or 0) > 0)})
    row[f"domain_cited_{s['template']}"] = int(s["domain_cited"])
    row[f"page_cited_{s['template']}"] = int(s["page_cited"])
table = list(rows.values())
random.Random(SEED).shuffle(table)
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNS); w.writeheader(); w.writerows(table)
print(f"{len(table)} rows written to {OUT}")
