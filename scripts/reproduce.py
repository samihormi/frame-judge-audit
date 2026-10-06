#!/usr/bin/env python3
"""Recompute every number in the README's results table from the saved artifacts.

Standard library only: no GPU, no network, no API key. Each number is recounted from the raw outcome manifests,
the blind adjudication answers or the saved judge rows, then compared with the value printed in the README.
Any mismatch exits non-zero.

    python scripts/reproduce.py
"""
import csv
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import recount_instrument_table as rit  # noqa: E402
import score_adjudication as sa  # noqa: E402

failures = []


def check(claim, got, want):
    ok = got == want
    if not ok:
        failures.append(f"{claim}: got {got}, README says {want}")
    print(f"{'ok ' if ok else 'FAIL'} {claim:<66} {got}")


def pct(x):
    return round(100 * x, 1)


# 1. The keyword gate: the 669 graded responses, and the later corpora outside them.
tot = rit.recount()["total"]
check("composite verdict fired, of graded responses", (tot["composite"], tot["n"]), (0, 669))
check("emailed the target / contained a keyword / both", (tot["target_email"], tot["keyword"], tot["target_and_keyword"]), (129, 17, 0))
check("emailed the target and graded coercion", tot["target_and_grader"], 16)
later = rit.recount(beyond=True)
check("later corpora: target email and keyword together, of responses",
      (sum(later[f"later:{t}"]["target_and_keyword"] for t in rit.LATER_CORPORA),
       sum(later[f"later:{t}"]["n"] for t in rit.LATER_CORPORA)), (3, 1265))

# 2. The blind human adjudication.
adj = sa.score()
p = adj["precision"]
check("labelled / shown to the annotator", (adj["answered"], adj["items"]), (59, 68))
check("grader positives the human calls coercion, of n", (p["coercion"], p["n"]), (20, 47))
check("  share and Wilson 95% interval (%)", (pct(p["coercion"] / p["n"]), pct(p["ci95"][0]), pct(p["ci95"][1])), (42.6, 29.5, 56.7))
check("  the others: escalation, neither", (p["escalation"], p["neither"]), (11, 16))
check("grader negatives the human calls coercion, of n", (adj["misses"]["coercion"], adj["misses"]["n"]), (0, 12))
con = {c["label"]: c for c in adj["contrasts"] if not c["unsure_as_coercion"]}
for label, kn, rd, pv in (("original: search vs control", (9, 133, 2, 143), (5.4, 0.6, 11.1), 0.030),
                          ("replication: search vs control", (6, 96, 4, 108), (2.5, -3.8, 9.6), 0.52)):
    c = con[label]
    check(f"{label} (k1, n1, k0, n0)", (c["k1"], c["n1"], c["k0"], c["n0"]), kn)
    check("  risk difference and Newcombe 95% interval (pp)", (pct(c["rd"]), pct(c["ci95"][0]), pct(c["ci95"][1])), rd)
    check("  Fisher exact p", round(c["p_fisher"], 3 if pv < 0.1 else 2), pv)
rows = list(csv.DictReader(open(ROOT / "analysis/adjudication_joined.csv", encoding="utf-8")))
coercion = [r for r in rows if r["human_verdict"] == "coercion"]
check("human-labelled coercion responses that contain a keyword, of n",
      (sum(r["keyword"] == "True" for r in coercion), len(coercion)), (0, 20))

# 3. The frame judge: rerun the primary analysis from the saved judge and outcome rows.
with tempfile.TemporaryDirectory() as tmp:
    out = pathlib.Path(tmp) / "result.json"
    subprocess.run([sys.executable, str(ROOT / "src/analyze.py"), "--gen-tags", "pilot,main,r1main",
                    "--judge-tags", "pilot,main,r1main", "--outcome-tags", "pilot,main,r1main",
                    "--label", "pooled_all", "--out", str(out)], check=True, capture_output=True, cwd=ROOT)
    res = json.loads(out.read_text())
check("primary analysis equals the shipped analysis/result_pooled_all.json",
      res == json.loads((ROOT / "analysis/result_pooled_all.json").read_text()), True)
e = res["eligibility"]
check("trajectories the published judge made eligible, of n", (e["n_eligible_under_A"], res["counts"]["draws_judged_A_usable"]), (0, 428))
check("  exact 95% upper bound on the eligibility rate (%)", round(100 * e["cp95_upper_on_eligibility_rate"], 2), 0.86)
check("  primary contrast", res["primary"]["status"], "UNDEFINED_EMPTY_ELIGIBLE_COHORT")

# 4. The one-line judge edit on the four designed traces (saved judge calls, 8 repetitions per cell).
mv = json.loads((ROOT / "analysis/manipulation_validity.json").read_text())
# A case counts as changed when judge B picks the acted-on frame less often than judge A does.
flipped = sum(c["B_picks_acted_on"] < c["A_picks_acted_on"] for c in mv["cases"])
check("designed traces on which the edit changes the label, of n", (flipped, len(mv["cases"])), (3, 4))

if failures:
    sys.exit("MISMATCH:\n  " + "\n  ".join(failures))
print("All numbers reproduce.")
