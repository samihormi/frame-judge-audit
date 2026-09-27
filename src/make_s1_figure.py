"""S1 central figure: the 2x2 (frame x search) with CIs, plus the within-arm search mediator."""
import json, math, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = pathlib.Path(__file__).resolve().parent.parent
SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; MUTED="#8a8984"
S1="#2a78d6"; S2="#eb6834"

def jl(p):
    p=ROOT/p; return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
def wilson(k,n,z=1.959963985):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (max(0.,c-h),min(1.,c+h))

gen,oc={},{}
for t in ['s1','s1c','s1d','s1e']:
    for r in jl(f'raw/generations/{t}/manifest.jsonl'):
        if r.get('valid') and r['draw_id'] not in gen: gen[r['draw_id']]=r
    for r in jl(f'raw/outcomes/{t}/manifest.jsonl'):
        if r.get('parse_ok') and r['draw_id'] not in oc: oc[r['draw_id']]=r
search={r['draw_id']:r for r in jl('raw/judge/aux_search/manifest.jsonl') if r.get('ok')}
ids=[d for d in gen if d in oc]
two=lambda d: oc[d]['classifier_verdict'] and oc[d]['target_email_present']
arms={}
for d in ids: arms.setdefault(gen[d]['arm'],[]).append(d)
def cell(a):
    ds=arms[a]; k=sum(1 for d in ds if two(d)); n=len(ds); lo,hi=wilson(k,n)
    return k,n,k/n,lo,hi

fig=plt.figure(figsize=(12.6,6.4),facecolor=SURFACE)
ax=fig.add_axes([0.075,0.145,0.50,0.70]); ax.set_facecolor(SURFACE)
groups=[("frame: none",["stem_only","route_search_no_frame"]),
        ("frame: \"constructed puzzle\"",["puzzle_frame_only","puzzle"])]
xs=[0,1]; w=0.34
for gi,(gname,pair) in enumerate(groups):
    for si,a in enumerate(pair):
        k,n,p,lo,hi=cell(a)
        x=si + (gi-0.5)*w
        col=S1 if gi==0 else S2
        ax.add_patch(plt.Rectangle((x-w/2+0.012,0),w-0.024,p*100,facecolor=col,
                                   edgecolor=SURFACE,lw=2,zorder=2,
                                   joinstyle="round"))
        ax.plot([x,x],[lo*100,hi*100],color=INK,lw=1.6,zorder=3,solid_capstyle="butt")
        ax.plot([x-0.045,x+0.045],[hi*100]*2,color=INK,lw=1.6,zorder=3)
        ax.plot([x-0.045,x+0.045],[lo*100]*2,color=INK,lw=1.6,zorder=3)
        ax.text(x,hi*100+1.0,f"{k}/{n}",ha="center",va="bottom",fontsize=9.5,color=INK2,zorder=4)
ax.set_xticks(xs); ax.set_xticklabels(["search: none","search: \"find the\nunconventional route\""],fontsize=10.5,color=INK)
ax.set_ylim(0,26); ax.set_xlim(-0.55,1.55)
ax.set_ylabel("coercive response rate (%)",fontsize=10.5,color=INK2)
ax.grid(axis="y",color="#ebeae5",lw=0.8); ax.set_axisbelow(True)
for s_ in ("top","right"): ax.spines[s_].set_visible(False)
ax.spines["left"].set_color("#dcdbd6"); ax.spines["bottom"].set_color("#dcdbd6")
ax.tick_params(colors=INK2,labelsize=9.5)
h=[plt.Rectangle((0,0),1,1,facecolor=S1),plt.Rectangle((0,0),1,1,facecolor=S2)]
ax.legend(h,["frame: none","frame: \"this is a constructed puzzle\""],frameon=False,
          fontsize=9.5,labelcolor=INK2,loc="upper left",handlelength=1.3)
ax.set_title("Search instruction moves it. Frame attribution does not.",
             loc="left",fontsize=12.5,color=INK,pad=12)

ax2=fig.add_axes([0.645,0.195,0.325,0.655]); ax2.set_facecolor(SURFACE)
ORDER=["stem_only","puzzle_frame_only","safety_eval","simulation","neutral","route_search_no_frame","puzzle"]
LBL={"stem_only":"stem only","puzzle_frame_only":"puzzle frame only","safety_eval":"safety-eval frame",
     "simulation":"simulation frame","neutral":"recites means","route_search_no_frame":"route search",
     "puzzle":"puzzle + route"}
y=0
for a in ORDER:
    ds=[d for d in arms[a] if d in search]
    lo_=[d for d in ds if search[d]['score']<=1]; hi_=[d for d in ds if search[d]['score']>=2]
    for sub,col,off in [(lo_,"#b9c7d6",0.17),(hi_,S2,-0.17)]:
        if not sub: continue
        k=sum(1 for d in sub if two(d)); p=k/len(sub)
        ax2.barh(y+off,p*100,height=0.30,color=col,edgecolor=SURFACE,lw=1.5)
        ax2.text(p*100+0.6,y+off,f"{k}/{len(sub)}",va="center",fontsize=8,color=INK2)
    ax2.text(-1.2,y,LBL[a],ha="right",va="center",fontsize=9.5,color=INK)
    y-=1
ax2.set_ylim(y+0.4,0.8); ax2.set_xlim(0,36)
ax2.set_yticks([]); ax2.set_xlabel("coercive response rate (%)",fontsize=10,color=INK2)
ax2.grid(axis="x",color="#ebeae5",lw=0.8); ax2.set_axisbelow(True)
for s_ in ("top","right","left"): ax2.spines[s_].set_visible(False)
ax2.spines["bottom"].set_color("#dcdbd6"); ax2.tick_params(colors=INK2,labelsize=9)
h2=[plt.Rectangle((0,0),1,1,facecolor=S2),plt.Rectangle((0,0),1,1,facecolor="#b9c7d6")]
ax2.legend(h2,["model searched hard (judge ≥2)","model searched little (≤1)"],frameon=False,
           fontsize=8.8,labelcolor=INK2,loc="upper center",
           bbox_to_anchor=(0.5,-0.13),handlelength=1.3,ncol=2,columnspacing=1.6)
ax2.set_title("…and it holds inside every arm\n(search scored on the model's own text)",
              loc="left",fontsize=11,color=INK,pad=12)
fig.text(0.075,0.045,
  "Qwen3-32B, Inspect agentic_misalignment no-goal blackmail, prefill into <think>.  "
  "Outcome = target_email ∧ grader coercion (claude-sonnet-4-6, T=0); the upstream keyword-gated composite scored 0 in every arm.\n"
  "Bars are Wilson 95% intervals.  Pooled within-arm search contrast: 18.7% vs 2.1%, RD +16.6 pp [+11.8, +22.0]. "
  "Search intensity is post-treatment: descriptive mediation, not an identified estimate.",
  fontsize=7.6,color=MUTED,va="top",linespacing=1.6)
for ext in ("png","pdf"):
    fig.savefig(ROOT/"figures"/f"s1_central_figure.{ext}",dpi=190,facecolor=SURFACE,bbox_inches="tight")
print("wrote figures/s1_central_figure.png")
