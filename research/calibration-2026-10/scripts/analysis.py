"""Analysis exactly as in PREREGISTRATION.md. Usage: python analysis.py WORKDIR (needs audits.jsonl and study.jsonl).
Writes WORKDIR/analysis-results-4dp.txt. Needs numpy, pandas, scipy, statsmodels."""
import json, math, sys, numpy as np, pandas as pd, statsmodels.api as sm
from scipy import stats
from pathlib import Path
B = Path(sys.argv[1]); rng = np.random.default_rng(20261017)
aud = {}
for l in (B / "audits.jsonl").read_text().splitlines(): r = json.loads(l); aud[r["url"]] = r
S = [json.loads(l) for l in (B / "study.jsonl").read_text().splitlines()]
S = [r for r in S if not r.get("error")]
rows = {}
for r in S:
    a = aud[r["url"]]; d = rows.setdefault(r["url"], {"url": r["url"], "domain": r["domain"], "score": a["score"], "rank": a["rank"], "stratum": a["stratum"], "words": a["words"],
                                                       "blocked": (a.get("bots_blocked") or 0) > 0, **{f"cat_{k}": v for k, v in (a.get("breakdown") or {}).items()}})
    d[f"dom_{r['template']}"] = int(r["domain_cited"]); d[f"page_{r['template']}"] = int(r["page_cited"])
df = pd.DataFrame(rows.values()); df["either"] = ((df.dom_A == 1) | (df.dom_B == 1)).astype(int)
df["lrank"] = np.log(df["rank"]); df["lwords"] = np.log(df["words"]); df["s10"] = df["score"] / 10
out = []
def P(*a): s = " ".join(str(x) for x in a); print(s); out.append(s)
P(f"pages {len(df)} | base rate: A domain {df.dom_A.mean():.4f}, B domain {df.dom_B.mean():.4f}, A page {df.page_A.mean():.4f}, B page {df.page_B.mean():.4f}, either {df.either.mean():.4f}")
P("score: mean %.1f sd %.1f | A/B agreement %.3f" % (df.score.mean(), df.score.std(), (df.dom_A == df.dom_B).mean()))
P("cited share by stratum (A):", {int(k): round(v, 2) for k, v in df.groupby("stratum").dom_A.mean().items()})
def fit(data, y, x="s10", ctrl=("lrank", "lwords")):
    X = sm.add_constant(data[[x, *ctrl]]); m = sm.Logit(data[y], X).fit(disp=0); b = m.params[x]; ci = m.conf_int().loc[x]
    return m, b, ci, m.pvalues[x]
def report(label, data, y, x="s10", scale=1.0):
    try:
        m, b, ci, p = fit(data, y, x)
        P(f"{label}: OR per {scale:g} unit(s) = {math.exp(b):.4f} (95% CI {math.exp(ci[0]):.4f} to {math.exp(ci[1]):.4f}), p = {p:.4f}, n = {len(data)}")
        return b, p
    except Exception as e: P(f"{label}: model failed ({type(e).__name__}: {e})"); return None, None
P("\n== PRIMARY: domain cited (template A) ~ score/10 + log rank + log words")
b, p = report("primary", df, "dom_A", "s10", 10)
bs = []
for _ in range(2000):
    s = df.sample(len(df), replace=True, random_state=int(rng.integers(1e9)))
    try: bs.append(fit(s, "dom_A")[1])
    except Exception: pass
bs = np.array(bs); P(f"bootstrap (n={len(bs)} fits): OR per 10 points {math.exp(np.median(bs)):.4f}, 95% interval {math.exp(np.percentile(bs, 2.5)):.4f} to {math.exp(np.percentile(bs, 97.5)):.4f}")
def partial_spearman(data, y):
    rx, ry, rz = (stats.rankdata(data[c]) for c in ("score", y, "lrank"))
    res = lambda v: v - np.polyval(np.polyfit(rz, v, 1), rz)
    r, p = stats.pearsonr(res(rx), res(ry)); return r, p
r, p = partial_spearman(df, "dom_A"); P(f"partial Spearman (score, domain cited A | log rank): {r:.4f}, p = {p:.4f}")
P("\n== SECONDARY outcomes")
for y, lab in (("dom_B", "domain cited B"), ("page_A", "exact page A"), ("page_B", "exact page B"), ("either", "domain cited A or B")): report(lab, df, y, "s10", 10)
P("\n== SECONDARY: nine categories (one at a time, domain cited A, same controls), Holm correction")
cats = [c for c in df.columns if c.startswith("cat_") and c != "cat_negative_penalty"]; res = []
for c in cats:
    d = df.dropna(subset=[c]).copy()
    if d[c].nunique() < 3: P(f"{c}: skipped (no variation)"); continue
    d["z"] = (d[c] - d[c].mean()) / d[c].std()
    try:
        m, b, ci, p = fit(d, "dom_A", "z"); res.append((c, b, ci, p))
    except Exception as e: P(f"{c}: failed ({type(e).__name__})")
order = sorted(range(len(res)), key=lambda i: res[i][3]); holm = {}; mx = 0
for rank_, i in enumerate(order): mx = max(mx, min(1, (len(res) - rank_) * res[i][3])); holm[i] = mx
for i, (c, b, ci, p) in enumerate(res): P(f"{c:18s} OR per 1 SD = {math.exp(b):.4f} (95% CI {math.exp(ci[0]):.4f} to {math.exp(ci[1]):.4f}), p = {p:.4f}, Holm p = {holm[i]:.4f}")
P("\n== SENSITIVITY: excluding pages on sites that block at least one AI bot in robots.txt")
report("primary, not blocked", df[~df.blocked], "dom_A", "s10", 10)
P("\n== DESCRIPTIVE: mean score of cited vs not cited (A): %.1f (n=%d) vs %.1f (n=%d)" % (df[df.dom_A == 1].score.mean(), (df.dom_A == 1).sum(), df[df.dom_A == 0].score.mean(), (df.dom_A == 0).sum()))
(B / "analysis-results-4dp.txt").write_text("\n".join(out) + "\n")
