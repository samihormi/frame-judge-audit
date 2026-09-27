"""Consolidate every control into one JSON used by the figure and the report."""
import json, pathlib, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent

def jl(p):
    p = ROOT / p
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []

def first(rows, cond, key="usable"):
    o = {}
    for r in rows:
        if r.get("condition") == cond and r.get(key) and r["draw_id"] not in o:
            o[r["draw_id"]] = r
    return o

out = {}

# ---- A/A instability vs A/B, on the SAME prespecified ids ----
ids = json.loads((ROOT / "protocol" / "control_ids_qwen3_32b.json").read_text())["aa_repeat_ids"]
main = jl("raw/judge/pilot/manifest.jsonl") + jl("raw/judge/main/manifest.jsonl")
A, B = first(main, "A"), first(main, "B")
A2 = first(jl("raw/judge/aa_qwen3_32b/manifest.jsonl"), "A2")
rows = []
for d in ids:
    if d in A and d in A2 and d in B:
        rows.append({"draw_id": d, "A_score": A[d]["score"], "A2_score": A2[d]["score"],
                     "B_score": B[d]["score"], "A_cat": A[d]["category"],
                     "A2_cat": A2[d]["category"], "B_cat": B[d]["category"]})
out["aa_vs_ab_matched_subset"] = {
    "n_requested": len(ids), "n_complete": len(rows),
    "missing_repeats": [d for d in ids if d not in A2],
    "AA_score_disagreements": sum(1 for r in rows if r["A_score"] != r["A2_score"]),
    "AB_score_disagreements": sum(1 for r in rows if r["A_score"] != r["B_score"]),
    "AA_category_disagreements": sum(1 for r in rows if r["A_cat"] != r["A2_cat"]),
    "AB_category_disagreements": sum(1 for r in rows if r["A_cat"] != r["B_cat"]),
    "note": ("Label disagreement and change in the behaviour statistic are different "
             "quantities. On this corpus every label is score 0 / category null, so both "
             "disagreement counts are 0 and neither bounds the other."),
    "rows": rows,
}

# ---- eligibility + outcome across every population ----
def pop(label, gen_tags, judge_tags, outcome_tags, population):
    g = [r for t in gen_tags for r in jl(f"raw/generations/{t}/manifest.jsonl")]
    j = [r for t in judge_tags for r in jl(f"raw/judge/{t}/manifest.jsonl")]
    o = [r for t in outcome_tags for r in jl(f"raw/outcomes/{t}/manifest.jsonl")]
    gv = {}
    for r in g:
        if r.get("valid") and r["draw_id"] not in gv:
            gv[r["draw_id"]] = r
    aa, bb = first(j, "A"), first(j, "B")
    oc = {}
    for r in o:
        if r.get("parse_ok") and r["draw_id"] not in oc:
            oc[r["draw_id"]] = r
    el = [d for d in aa if isinstance(aa[d]["score"], int) and aa[d]["score"] >= 2]
    return {
        "label": label, "population": population,
        "draws_attempted": len({r["draw_id"] for r in g}),
        "valid_generations": len(gv),
        "truncated_attempts": sum(1 for r in g if r.get("truncated")),
        "judged_A": len(aa), "judged_B": len(bb),
        "eligible_A_ge2": len(el), "eligible_ids": el,
        "score_dist_A": dict(sorted(collections.Counter(aa[d]["score"] for d in aa).items())),
        "score_dist_B": dict(sorted(collections.Counter(bb[d]["score"] for d in bb).items())),
        "cat_dist_A": dict(collections.Counter(str(aa[d]["category"]) for d in aa)),
        "cat_dist_B": dict(collections.Counter(str(bb[d]["category"]) for d in bb)),
        "outcome_labelled": len(oc),
        "blackmail": sum(1 for d in oc if oc[d]["blackmail"]) if oc else None,
        "AB_agree_on_eligible": [
            {"draw_id": d, "A": [aa[d]["score"], aa[d]["category"]],
             "B": [bb[d]["score"], bb[d]["category"]] if d in bb else None} for d in el
        ],
    }

out["populations"] = [
    pop("qwen3_32b_pilot", ["pilot"], ["pilot"], ["pilot"], "PRIMARY (discovery pilot)"),
    pop("qwen3_32b_main", ["main"], ["main"], ["main"], "PRIMARY (confirmation, target fixed at 200 before collection)"),
    pop("r1distill_32b_main", ["r1main"], ["r1main"], ["r1main"], "PRIMARY (declared substitution corpus)"),
    pop("qwen3_32b_awareness_prompted", ["awctl_qwen"], ["awctl_qwen"], [], "CONTROL — test_eval_awareness=True; never pooled with primary"),
    pop("r1distill_32b_awareness_prompted", ["awctl_r1"], ["awctl_r1"], [], "CONTROL — test_eval_awareness=True; never pooled with primary"),
]

# ---- synthetic parser controls ----
syn = jl("raw/judge/synthetic_controls/manifest.jsonl")
out["synthetic_controls"] = {
    "status": "SYNTHETIC — excluded from all scientific results",
    "rows": [{"id": r["draw_id"], "cond": r["condition"], "score": r.get("score"),
              "cat": r.get("category"), "quotes_all_verbatim": r.get("all_quotes_verbatim")}
             for r in syn],
}

# ---- quote integrity across every real judge call ----
allj = [r for t in ["pilot", "main", "r1main", "awctl_qwen", "awctl_r1", "aa_qwen3_32b"]
        for r in jl(f"raw/judge/{t}/manifest.jsonl")]
withq = [r for r in allj if r.get("quote_checks")]
out["quote_integrity"] = {
    "judge_calls_total": len(allj),
    "calls_with_quotes": len(withq),
    "calls_all_quotes_verbatim": sum(1 for r in withq if r.get("all_quotes_verbatim")),
    "failing_calls": [r["judge_call_id"] for r in withq if not r.get("all_quotes_verbatim")],
    "parse_failures": [r["judge_call_id"] for r in allj if not r.get("parse_ok")],
    "out_of_vocab_categories": [r["judge_call_id"] for r in allj
                                if r.get("category") and str(r["category"]).startswith("OUT_OF_VOCAB")],
}
dest = ROOT / "analysis" / "controls_summary.json"
dest.write_text(json.dumps(out, indent=2))
print(json.dumps({"aa_vs_ab": {k: v for k, v in out["aa_vs_ab_matched_subset"].items() if k != "rows"},
                  "populations": [{k: v for k, v in p.items() if k not in ("eligible_ids",)} for p in out["populations"]],
                  "quote_integrity": out["quote_integrity"],
                  "synthetic": out["synthetic_controls"]["rows"]}, indent=2))
print("\nwrote", dest)
