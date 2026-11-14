"""Charts of the note. Run it in the folder that holds results.csv. The odds ratios of the first chart are copied by
hand from analysis-results.txt. Needs pandas, numpy, matplotlib."""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
BG="#FAF5EE"; INK="#2D3340"; MUTE="#6B7280"; BLUE="#4F6DB8"; TEAL="#2F7D6D"; PEACH="#C27A45"; RULE="#CFC6BB"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.edgecolor":RULE,"axes.labelcolor":INK,"xtick.color":INK,"ytick.color":INK})
# ---- chart 1: odds ratios (values copied from analysis-results.txt)
rows=[("Primary: domain cited,\nquestion A",0.9625,0.7827,1.1836,BLUE),
      ("Primary, resampled\n2,000 times",0.9592,0.7587,1.2049,BLUE),
      ("Question B\ninstead of A",0.9660,0.7848,1.1890,TEAL),
      ("Exact page cited,\nquestion A",1.0568,0.8364,1.3354,TEAL),
      ("Sites that do not block\nAI bots (253 pages)",1.0408,0.8302,1.3048,PEACH)]
fig,ax=plt.subplots(figsize=(8.8,4.4),dpi=150); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
y=np.arange(len(rows))[::-1]
for yi,(lab,m,lo,hi,c) in zip(y,rows):
    ax.plot([lo,hi],[yi,yi],color=c,lw=3,solid_capstyle="round"); ax.plot(m,yi,"o",color=c,ms=9,mec=BG,mew=1.5)
    ax.text(1.95,yi,f"{m:.2f}  ({lo:.2f} to {hi:.2f})",va="center",ha="left",color=INK,fontsize=10.5)
ax.axvline(1,color=INK,ls="--",lw=1)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows],fontsize=10.5)
ax.set_xscale("log"); ax.set_xlim(0.6,1.9); ax.set_xticks([0.6,0.8,1,1.25,1.5]); ax.set_xticklabels(["0.6","0.8","1","1.25","1.5"])
ax.minorticks_off(); ax.set_xlabel("Odds ratio per 10 score points (1 = no difference), with 95% confidence interval")
for s in ("top","right","left"): ax.spines[s].set_visible(False)
ax.tick_params(axis="y",length=0); ax.set_ylim(-0.6,len(rows)-0.1)
ax.text(0.985,len(rows)-0.35,"less likely cited",ha="right",va="center",fontsize=9,color=MUTE); ax.text(1.015,len(rows)-0.35,"more likely cited",ha="left",va="center",fontsize=9,color=MUTE)
fig.subplots_adjust(left=0.27,right=0.80,top=0.93,bottom=0.17); fig.savefig("chart1_odds_ratios.png",facecolor=BG)
# ---- chart 2: share cited by popularity band (from results.csv)
d=pd.read_csv("results.csv")
order=["1-1000","1001-3000","3001-10000","10001-30000","30001-100000","100001-200000","200001-400000","400001-600000","600001-800000","800001-1000000"]
labels=["1-1k","1k-3k","3k-10k","10k-\n30k","30k-\n100k","100k-\n200k","200k-\n400k","400k-\n600k","600k-\n800k","800k-\n1M"]
g=d.groupby("rank_band").agg(n=("domain_cited_A","size"),c=("domain_cited_A","sum")).reindex(order); share=100*g.c/g.n
fig,ax=plt.subplots(figsize=(8.8,4.4),dpi=150); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
bars=ax.bar(range(10),share,color=BLUE,width=0.68)
for i,(s,n) in enumerate(zip(share,g.n)):
    ax.text(i,s+1.6,f"{s:.0f}%",ha="center",va="bottom",fontsize=10,color=INK); ax.text(i,2,f"n={int(n)}",ha="center",va="bottom",fontsize=8.5,color="white")
tot=100*d.domain_cited_A.mean(); ax.axhline(tot,color=PEACH,ls="--",lw=1.2); ax.text(9.62,tot+1.2,f"all pages: {tot:.0f}%",ha="left",va="bottom",fontsize=9.5,color=PEACH)
ax.set_xlim(-0.6,11.4); ax.set_xticks(range(10)); ax.set_xticklabels(labels,fontsize=9.5); ax.set_ylim(0,75); ax.set_yticks([0,20,40,60]); ax.set_yticklabels(["0%","20%","40%","60%"])
ax.set_xlabel("Popularity band (Tranco rank)"); ax.set_ylabel("Pages whose domain was cited")
for s in ("top","right"): ax.spines[s].set_visible(False)
fig.subplots_adjust(left=0.10,right=0.98,top=0.97,bottom=0.20); fig.savefig("chart2_cited_by_band.png",facecolor=BG)
print("ok")
