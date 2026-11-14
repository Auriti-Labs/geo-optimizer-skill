"""Stage 1 of the calibration study (original script of 2026-10-17, unchanged apart from this note):

Usage: python stage1_sample.py WORKDIR   (WORKDIR must contain tranco-top1m.csv, a "rank,domain" file from tranco-list.eu;
the list used was the one current on 2026-10-17: it is third-party data and is not republished here.)
Writes WORKDIR/sample.jsonl (domains and page URLs: do not publish).

Stage 1 (v2) of the calibration study: no Perplexity, read-only fetches of public pages.

Draws domains from the Tranco list in 10 log-spaced rank strata, keeps reachable English sites (declared lang,
or English detected from the text when the lang attribute is missing) and chooses ONE informational page per
site from its sitemap. Resumable (sample.jsonl is append-only; the last record per domain wins; domains that
failed only for a missing/unknown language in v1 are retried). 6 worker threads over different domains;
each request sleeps 1 s first, so a single site never gets more than about one request per second.
"""
import hashlib, ipaddress, json, random, re, socket, sys, threading, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(sys.argv[1]); SEED = 20261017; WORKERS = 6
UA = "geo-optimizer-skill research (+https://github.com/Auriti-Labs/geo-optimizer-skill)"
EDGES = [0, 1000, 3000, 10000, 30000, 100000, 200000, 400000, 600000, 800000, 1000000]
PER_STRATUM = 450
BAD = re.compile(r"porn|xxx|sex|adult|casino|bet(?!a)|hentai|escort|nude|cam(?!era|p)|gambl|slot", re.I)
SKIP_PATH = re.compile(r"login|signin|cart|checkout|account|tag/|category/|/page/|search|\.(jpg|png|gif|pdf|zip|xml)$|feed|wp-json|cdn-cgi", re.I)
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
STOP = set("the and of to in is for that with on as are this by it from be or an at was not have you your can will more all our".split())
lock = threading.Lock()

def looks_english(words):
    w = [x.lower() for x in words]
    return len(w) >= 150 and sum(1 for x in w if x in STOP) / len(w) >= 0.15

def public_host(host):
    try:
        for _, _, _, _, sa in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP):
            ip = ipaddress.ip_address(sa[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: return False
        return True
    except Exception: return False

def get(url, limit=1_500_000, timeout=15):
    time.sleep(1)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read(limit).decode("utf-8", "replace"), r.geturl()

class P(HTMLParser):
    def __init__(self): super().__init__(); self.h1 = None; self.title = None; self.lang = None; self._t = None; self._buf = []; self.text = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html": self.lang = a.get("lang")
        if tag in ("script", "style", "noscript"): self.skip += 1
        if tag == "h1" and self.h1 is None: self._t = "h1"; self._buf = []
        if tag == "title" and self.title is None: self._t = "title"; self._buf = []
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip: self.skip -= 1
        if tag == self._t:
            setattr(self, tag, re.sub(r"\s+", " ", "".join(self._buf)).strip()); self._t = None
    def handle_data(self, d):
        if self._t: self._buf.append(d)
        if not self.skip: self.text.append(d)

def parse(html):
    p = P()
    try: p.feed(html)
    except Exception: pass
    wl = re.findall(r"\w+", " ".join(p.text))
    return p.lang, p.title, p.h1, len(wl), wl

def sitemap_pages(host):
    base = f"https://{host}"; cands = []
    try:
        _, _, robots, _ = get(base + "/robots.txt", 200_000)
        cands = re.findall(r"(?im)^sitemap:\s*(\S+)", robots)
    except Exception: pass
    for sm in (cands or [base + "/sitemap.xml"])[:2]:
        try:
            _, _, xml, _ = get(sm, 3_000_000)
            locs = LOC.findall(xml)
            if locs and all(".xml" in l for l in locs[:3]): _, _, xml, _ = get(locs[0], 3_000_000); locs = LOC.findall(xml)
            pages = [l for l in locs if urllib.parse.urlparse(l).netloc.endswith(host) and urllib.parse.urlparse(l).path.count("/") >= 2 and not SKIP_PATH.search(l)]
            if pages: return pages
        except Exception: continue
    return []

def process(c):
    stratum, rank, host = c
    rec = {"stratum": stratum, "rank": rank, "domain": host, "ok": False}
    try:
        if not public_host(host): rec["reason"] = "not_public_host"; return rec
        st, ct, html, _ = get(f"https://{host}/")
        if st != 200 or "html" not in ct: rec["reason"] = f"home_{st}"; return rec
        lang, _, _, _, wl = parse(html)
        if lang and not lang.lower().startswith("en"): rec["reason"] = f"lang_{lang}"; return rec
        if not lang and not looks_english(wl): rec["reason"] = "lang_unknown_not_english"; return rec
        pages = sitemap_pages(host)
        if not pages: rec["reason"] = "no_sitemap_pages"; return rec
        url = sorted(pages, key=lambda u: hashlib.sha256((u + str(SEED)).encode()).hexdigest())[0]
        if not public_host(urllib.parse.urlparse(url).netloc): rec["reason"] = "page_not_public"; return rec
        st, ct, html, _ = get(url)
        lang, title, h1, words, wl = parse(html)
        if (lang and not lang.lower().startswith("en")) or (not lang and not looks_english(wl)): rec["reason"] = f"page_lang_{lang}"; return rec
        if st != 200 or "html" not in ct or not h1 or not (20 <= len(h1) <= 120) or words < 300: rec["reason"] = f"page_unfit(status={st},words={words},h1={bool(h1)})"; return rec
        rec.update(ok=True, url=url, title=title, h1=h1, words=words, page_lang=lang)
    except Exception as e: rec["reason"] = "error_" + type(e).__name__
    return rec

rows = [l.split(",", 1) for l in (BASE / "tranco-top1m.csv").read_text().splitlines()]
rng = random.Random(SEED); cands = []
for i in range(10):
    pool = [(int(r), d) for r, d in rows if EDGES[i] < int(r) <= EDGES[i + 1] and not BAD.search(d) and "." in d and not re.match(r"^\d+\.\d+", d)]
    for r, d in rng.sample(pool, min(len(pool), PER_STRATUM)): cands.append((i + 1, r, d))
out = BASE / "sample.jsonl"; last = {}
if out.exists():
    for l in out.read_text().splitlines(): r = json.loads(l); last[r["domain"]] = r
done = {d for d, r in last.items() if r.get("ok") or not str(r.get("reason", "")).startswith(("lang_None", "lang_unknown"))}
todo = [c for c in cands if c[2] not in done]
print(f"candidates {len(cands)}, to do {len(todo)} (done {len(done)})", flush=True)
cnt = 0
with ThreadPoolExecutor(WORKERS) as ex:
    for rec in ex.map(process, todo):
        with lock:
            with out.open("a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        cnt += 1
        if cnt % 50 == 0: print(cnt, rec["domain"], rec.get("ok"), rec.get("reason"), flush=True)
print("done", flush=True)
