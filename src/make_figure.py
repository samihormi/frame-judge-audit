"""Central figure: observed rates with exact 95% upper bounds and explicit denominators,
plus the empty-denominator panel showing why the primary contrast is undefined.
"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from analyze import clopper_pearson_upper  # noqa: E402

C = json.loads((ROOT / "analysis" / "controls_summary.json").read_text())

SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#8a8984"
S1 = "#2a78d6"   # frame-awareness eligibility (judge A, score >= 2)
S2 = "#eb6834"   # blackmail outcome (upstream 3-factor, final response only)

ORDER = ["qwen3_32b_pilot", "qwen3_32b_main", "r1distill_32b_main",
         "qwen3_32b_awareness_prompted", "r1distill_32b_awareness_prompted"]
NAMES = {
    "qwen3_32b_pilot": "Qwen3-32B  ·  discovery pilot",
    "qwen3_32b_main": "Qwen3-32B  ·  main (target fixed at 200)",
    "r1distill_32b_main": "R1-Distill-Qwen-32B  ·  declared substitution",
    "qwen3_32b_awareness_prompted": "Qwen3-32B  ·  CONTROL: awareness-prompted",
    "r1distill_32b_awareness_prompted": "R1-Distill-32B  ·  CONTROL: awareness-prompted",
}
P = {p["label"]: p for p in C["populations"]}

fig = plt.figure(figsize=(12.4, 11.6), facecolor=SURFACE)
gs = fig.add_gridspec(2, 1, height_ratios=[1.55, 1.0], hspace=0.40,
                      left=0.305, right=0.975, top=0.905, bottom=0.415)
ax = fig.add_subplot(gs[0]); ax.set_facecolor(SURFACE)

rows, ylabels = [], []
y = 0
for lab in ORDER:
    p = P[lab]
    k_el, n_el = p["eligible_A_ge2"], p["judged_A"]
    rows.append((y + 0.17, k_el, n_el, S1, "frame"))
    if p["outcome_labelled"]:
        rows.append((y - 0.17, p["blackmail"], p["outcome_labelled"], S2, "bm"))
    ylabels.append((y, NAMES[lab], "CONTROL" in NAMES[lab]))
    y -= 1

for yy, k, n, col, _kind in rows:
    ub = clopper_pearson_upper(k, n) * 100
    pt = (k / n) * 100
    ax.plot([pt, ub], [yy, yy], color=col, lw=2, solid_capstyle="butt", zorder=2)
    ax.plot([ub], [yy], marker="|", ms=10, mew=2, color=col, zorder=3)
    ax.plot([pt], [yy], marker="o", ms=8, color=col, mec=SURFACE, mew=2, zorder=4)
    ax.text(ub + 0.55, yy, f"{k}/{n}   ≤{ub:.2f}%", va="center", ha="left",
            fontsize=9.5, color=INK2)

for yy, name, is_ctl in ylabels:
    ax.text(-1.15, yy, name, va="center", ha="right", fontsize=10.5,
            color=MUTED if is_ctl else INK, style="italic" if is_ctl else "normal")

ax.axhline(-2.5, color="#dcdbd6", lw=1, zorder=1)
ax.text(-1.15, -2.5, "— control populations, never pooled —", va="bottom", ha="right",
        fontsize=8.5, color=MUTED)
ax.set_xlim(-1.0, 27.5); ax.set_ylim(-4.8, 1.35)
ax.set_yticks([])
ax.set_xlabel("rate (%)  ·  point estimate with exact 95% Clopper–Pearson upper bound",
              fontsize=10, color=INK2)
ax.grid(axis="x", color="#ebeae5", lw=0.8); ax.set_axisbelow(True)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#dcdbd6")
ax.tick_params(colors=INK2, labelsize=9.5)
h = [plt.Line2D([], [], color=S1, lw=2, marker="o", ms=7, mec=SURFACE, mew=1.5),
     plt.Line2D([], [], color=S2, lw=2, marker="o", ms=7, mec=SURFACE, mew=1.5)]
ax.legend(h, ["eligible under published judge A  (frame-awareness score ≥ 2)",
              "blackmail in final response  (upstream 3-factor classifier)"],
          loc="upper right", frameon=False, fontsize=9.5, labelcolor=INK2,
          handlelength=1.8, borderaxespad=0.2, ncol=1)
ax.set_title("Eligibility and outcome are both empty on the canonical no-goal blackmail prompt",
             loc="left", fontsize=12.5, color=INK, pad=10, x=-0.355)

# ---- panel 2: the empty 2x2 that makes the primary contrast undefined ----
ax2 = fig.add_axes([0.035, 0.360, 0.94, 0.225]); ax2.set_facecolor(SURFACE); ax2.axis("off")
pooled = json.loads((ROOT / "analysis" / "result_pooled_all.json").read_text())
n_pool = pooled["counts"]["draws_judged_A_usable"]

ax2.text(0, 1.0, "Why the primary contrast is UNDEFINED, not zero", fontsize=12.5,
         color=INK, va="top")
ax2.text(0, 0.845,
         "$\\Delta_R = P(\\mathrm{blackmail}\\,|\\,\\mathrm{risk\\ label\\ under\\ }R)"
         " - P(\\mathrm{blackmail}\\,|\\,\\mathrm{other\\ labels\\ under\\ }R)$"
         "   on the eligible cohort;   $D = \\Delta_A - \\Delta_B$",
         fontsize=10.5, color=INK2, va="top")

cells = [("risk label under A\n{puzzle, simulation}", 0), ("other labels under A", 0),
         ("risk label under B\n{puzzle, simulation}", 0), ("other labels under B", 0)]
x0, w, gap = 0.010, 0.228, 0.020
for i, (nm, den) in enumerate(cells):
    x = x0 + i * (w + gap)
    ax2.add_patch(Rectangle((x, 0.21), w, 0.42, transform=ax2.transAxes,
                            facecolor="#f4f3ee", edgecolor="#dcdbd6", lw=1))
    ax2.text(x + w / 2, 0.565, nm, ha="center", va="top", fontsize=9, color=INK2)
    ax2.text(x + w / 2, 0.375, f"n = {den}", ha="center", va="center", fontsize=15,
             color=S1 if i < 2 else S2, fontweight="bold")
    ax2.text(x + w / 2, 0.265, "blackmail 0 / 0", ha="center", va="center",
             fontsize=8.5, color=MUTED)
ax2.text(0, 0.115,
         f"All four denominators are empty: {n_pool} pooled trajectories judged, 0 reached "
         f"score ≥ 2. $\\Delta_A$, $\\Delta_B$ and $D$ have no defined value —\n"
         "they are not 0. No bootstrap draw is definable, so no interval is reported. "
         "A 0 here would be a fabricated number.",
         fontsize=10, color=INK, va="top")
# ---- panel 3: the edit is a potent manipulation where it applies ----
MV = json.loads((ROOT / "analysis" / "manipulation_validity.json").read_text())
ax3 = fig.add_axes([0.035, 0.072, 0.94, 0.215]); ax3.set_facecolor(SURFACE); ax3.axis("off")
ax3.set_xlim(0, 1); ax3.set_ylim(0, 1)
ax3.text(0.012, 0.99, "…but the edit itself is potent where it applies", fontsize=12.5,
         color=INK, va="top")
ax3.text(0.012, 0.855,
         "Constructed traces that attribute two frames with EQUAL explicit evidence, then act on one "
         "— the case where the two rules are designed to disagree.\n"
         "8 seeds per cell, 32 calls per condition.  SYNTHETIC: this measures the instrument, not any "
         "corpus rate, and enters no number above.",
         fontsize=9.3, color=INK2, va="top", linespacing=1.45)
CA, CB = 0.585, 0.845
ax3.text(0.012, 0.585, "designed case", fontsize=8.8, color=MUTED, ha="left", va="center")
ax3.text(CA, 0.585, "A selects the acted-on frame", fontsize=8.8, color=S1, ha="center", va="center")
ax3.text(CB, 0.585, "B returns 'unclear'", fontsize=8.8, color=S2, ha="center", va="center")
rows3 = [(c["case_id"].split("-", 2)[2].replace("-", " "), c["A_picks_acted_on"], c["B_unclear_rate"])
         for c in MV["cases"]]
yy = 0.465
for nm, ap_, bu in rows3:
    ax3.text(0.012, yy, nm, fontsize=9, color=INK, ha="left", va="center")
    ax3.text(CA, yy, f"{int(round(ap_*8))}/8", fontsize=10.5, color=S1, ha="center", va="center",
             fontweight="bold" if ap_ == 1 else "normal")
    ax3.text(CB, yy, f"{int(round(bu*8))}/8", fontsize=10.5, color=S2, ha="center", va="center",
             fontweight="bold" if bu == 1 else "normal")
    yy -= 0.095
ov = MV["overall"]
ax3.plot([0.008, 0.965], [yy + 0.045, yy + 0.045], color="#dcdbd6", lw=1)
ax3.text(0.012, yy - 0.015, "overall, 32 calls per condition", fontsize=9.5, color=INK,
         ha="left", va="center")
ax3.text(CA, yy - 0.015, f"{ov['A_picks_designed_acted_on']*100:.1f}%", fontsize=11.5,
         color=S1, ha="center", va="center", fontweight="bold")
ax3.text(CB, yy - 0.015, f"{ov['B_unclear_rate']*100:.0f}%    (A: {ov['A_unclear_rate']*100:.1f}%)",
         fontsize=11.5, color=S2, ha="center", va="center", fontweight="bold")

fig.text(0.035, 0.048,
         "Judge A = published frame-awareness prompt verbatim. Judge B = identical except one replaced "
         "tie-breaker line (1-line diff).   Target models: Qwen3-32B rev 9216db57 and\n"
         "DeepSeek-R1-Distill-Qwen-32B rev 711ad2ea, BF16 TP=2 vLLM 0.19.0, thinking on, "
         "T=0.6/top_p=0.95/top_k=20.   Judge: gpt-4.1-2025-04-14, T=0.   Outcome grader: claude-sonnet-4-6,\n"
         "T=0, final response only.   Controls use Inspect's own test_eval_awareness=True and are never "
         "pooled with the primary rows.",
         fontsize=7.8, color=MUTED, va="top", linespacing=1.5)

for ext in ("png", "pdf"):
    fig.savefig(ROOT / "figures" / f"central_figure.{ext}", dpi=190,
                facecolor=SURFACE, bbox_inches="tight")
print("wrote figures/central_figure.png and .pdf")
