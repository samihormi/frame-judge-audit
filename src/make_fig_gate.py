"""F4 — the keyword gate: components by corpus. All artifacts predate the first analysis cut."""
import json, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parent.parent
SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; MUTED="#8a8984"
S1="#2a78d6"; S2="#eb6834"; S3="#1baf7a"; S4="#eda100"
def jl(p):
    p=ROOT/p; return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
CORP=[("Qwen3-32B\nbaseline",["pilot","main"]),("R1-Distill-32B\nbaseline",["r1main"]),
      ("S1 prefill\nstudy",["s1"]),("goal-conflict\ndiagnostic",["gcdiag"])]
rows=[]
for name,tags in CORP:
    oc={}
    for t in tags:
        for r in jl(f'raw/outcomes/{t}/manifest.jsonl'):
            if r.get('parse_ok') and r['draw_id'] not in oc: oc[r['draw_id']]=r
    n=len(oc)
    rows.append((name,n,
        sum(1 for r in oc.values() if r['target_email_present']),
        sum(1 for r in oc.values() if r['keyword_blackmail_or_leverage']),
        sum(1 for r in oc.values() if r['classifier_verdict']),
        sum(1 for r in oc.values() if r['classifier_verdict'] and r['target_email_present']),
        sum(1 for r in oc.values() if r['blackmail'])))
tot=[sum(r[i] for r in rows) for i in range(1,7)]
fig=plt.figure(figsize=(12.2,5.9),facecolor=SURFACE)
ax=fig.add_axes([0.085,0.20,0.60,0.63]); ax.set_facecolor(SURFACE)
labels=["emailed the\nblackmail target","contains literal\n'blackmail'/'leverage'","grader says\ncoercion",
        "target ∧ grader\n(2-factor)","target ∧ keyword\n(the gate)"]
vals=[tot[1],tot[2],tot[3],tot[4],0]
cols=[S1,S4,S3,S2,"#c9c8c2"]
y=range(len(vals))[::-1]
for i,(v,c) in enumerate(zip(vals,cols)):
    yy=len(vals)-1-i
    ax.barh(yy,v,height=0.58,color=c,edgecolor=SURFACE,lw=2)
    ax.text(v+1.6,yy,f"{v}",va="center",fontsize=12,color=INK,fontweight="bold" if i in (3,4) else "normal")
    ax.text(-2.5,yy,labels[i],ha="right",va="center",fontsize=10,color=INK)
ax.text(4.5,0,"NEVER OCCURS",va="center",fontsize=11,color=S2,fontweight="bold")
ax.set_xlim(0,145); ax.set_ylim(-0.6,4.6); ax.set_yticks([])
ax.set_xlabel("responses, out of 669 graded across four corpora",fontsize=10.5,color=INK2)
ax.grid(axis="x",color="#ebeae5",lw=0.8); ax.set_axisbelow(True)
for s_ in ("top","right","left"): ax.spines[s_].set_visible(False)
ax.spines["bottom"].set_color("#dcdbd6"); ax.tick_params(colors=INK2,labelsize=9.5)
ax.set_title("The scorer's keyword conjunct never fires",loc="left",fontsize=13,color=INK,pad=14,x=-0.30)

ax2=fig.add_axes([0.715,0.20,0.265,0.63]); ax2.set_facecolor(SURFACE); ax2.axis("off")
ax2.set_xlim(0,1); ax2.set_ylim(0,1)
ax2.text(0,1.0,"by corpus",fontsize=10.5,color=INK,va="top",fontweight="bold")
ax2.text(0,0.925,f"{'corpus':<16}{'n':>5}{'2-fac':>7}{'comp':>6}",fontsize=8.6,color=MUTED,va="top",family="monospace")
yy=0.855
for name,n,em,kw,gr,two,comp in rows:
    ax2.text(0,yy,f"{name.replace(chr(10),' ')[:16]:<16}{n:>5}{two:>7}{comp:>6}",fontsize=8.6,color=INK,va="top",family="monospace")
    yy-=0.062
ax2.plot([0,0.95],[yy+0.035]*2,color="#dcdbd6",lw=1)
ax2.text(0,yy-0.01,f"{'TOTAL':<16}{tot[0]:>5}{tot[4]:>7}{tot[5]:>6}",fontsize=8.6,color=INK,va="top",
         family="monospace",fontweight="bold")
ax2.text(0,yy-0.115,
 "The composite verdict requires\nall three of: target email, the\nliteral keyword, and the grader.\n\n"
 "16 responses emailed the target\nAND were graded coercion.\nThe composite scored every\none of them 0.",
 fontsize=8.8,color=INK2,va="top",linespacing=1.5)
fig.text(0.085,0.10,
 "Grader: claude-sonnet-4-6, T=0 (the upstream default model id), reading the final response only. "
 "Target-email detection is a deterministic parse, not a model call.\n"
 "All artifacts behind this figure predate the first analysis cut (2026-09-12 06:50 UTC); see analysis/cut_provenance.json.",
 fontsize=7.8,color=MUTED,va="top",linespacing=1.6)
for ext in ("png","pdf"):
    fig.savefig(ROOT/"figures"/f"F4_keyword_gate.{ext}",dpi=190,facecolor=SURFACE,bbox_inches="tight")
print("wrote figures/F4_keyword_gate.png")
