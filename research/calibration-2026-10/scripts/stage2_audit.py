"""Stage 2: audit the chosen pages with the published CLI (no Perplexity, no spend).

Usage: python stage2_audit.py WORKDIR   (needs WORKDIR/sample.jsonl from stage 1). The study used the PyPI release
geo-optimizer-skill 4.19.3 with its default rubric (v2): install it in a clean virtualenv and point GEO_CLI at its
`geo` executable (default: the `geo` found on PATH).
3 worker threads over different sites; resumable; writes audits.jsonl (append-only, last record per URL wins)."""
import json, os, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
BASE = Path(sys.argv[1]); CLI = os.environ.get("GEO_CLI") or shutil.which("geo") or sys.exit("geo CLI not found: set GEO_CLI"); lock = threading.Lock()
last = {}
for l in (BASE / "sample.jsonl").read_text().splitlines(): r = json.loads(l); last[r["domain"]] = r
sel = [r for r in last.values() if r.get("ok")]
out = BASE / "audits.jsonl"
done = {json.loads(l)["url"] for l in out.read_text().splitlines() if not (json.loads(l).get("error") or "").startswith("audit_")} if out.exists() else set()
todo = [r for r in sel if r["url"] not in done]
print(f"pages to audit {len(todo)} (selected {len(sel)}, done {len(done)})", flush=True)
def audit(r):
    tmp = BASE / f"tmp_audit_{threading.get_ident()}.json"; tmp.unlink(missing_ok=True)
    rec = {"domain": r["domain"], "url": r["url"], "rank": r["rank"], "stratum": r["stratum"], "words": r["words"], "h1": r["h1"]}; t0 = time.time()
    try:
        subprocess.run([CLI, "audit", "--url", r["url"], "--format", "json", "--output", str(tmp)], capture_output=True, timeout=150)
        d = json.loads(tmp.read_text()); rb = (d.get("checks", {}).get("robots_txt", {}) or {}).get("details", {}) or {}
        rec.update(score=d.get("score"), band=d.get("band"), error=d.get("error"), score_version=d.get("score_version"), http_status=d.get("http_status"),
                   breakdown=d.get("score_breakdown"), robots_found=rb.get("found"), bots_blocked=len(rb.get("bots_blocked") or []), bots_allowed=len(rb.get("bots_allowed") or []),
                   citation_bots_ok=rb.get("citation_bots_ok"), secs=round(time.time() - t0, 1))
    except Exception as e: rec["error"] = "audit_" + type(e).__name__
    tmp.unlink(missing_ok=True); time.sleep(1); return rec
cnt = 0
with ThreadPoolExecutor(3) as ex:
    for rec in ex.map(audit, todo):
        with lock:
            with out.open("a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        cnt += 1
        if cnt % 20 == 0: print(cnt, rec["domain"], rec.get("score"), rec.get("error"), flush=True)
print("done", flush=True)
