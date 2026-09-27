"""Prespecify the random subsets for the A/A instability control and the human audit.
Written BEFORE any disagreement is inspected. Seeded and therefore recomputable.
"""
import argparse, json, pathlib, random
ROOT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--gen-tags", required=True)
ap.add_argument("--label", required=True)
ap.add_argument("--n-aa", type=int, default=30)
ap.add_argument("--n-audit", type=int, default=30)
ap.add_argument("--seed", type=int, default=20260912)
a = ap.parse_args()
draws = []
for t in a.gen_tags.split(","):
    p = ROOT / "raw" / "generations" / t / "manifest.jsonl"
    draws += [json.loads(x)["draw_id"] for x in p.read_text().splitlines()
              if x.strip() and json.loads(x).get("valid")]
draws = sorted(set(draws))
rng = random.Random(a.seed)
aa = sorted(rng.sample(draws, min(a.n_aa, len(draws))))
audit = sorted(rng.sample(draws, min(a.n_audit, len(draws))))
dest = ROOT / "protocol" / f"control_ids_{a.label}.json"
dest.write_text(json.dumps({
    "gen_tags": a.gen_tags, "seed": a.seed, "n_pool": len(draws),
    "aa_repeat_ids": aa, "human_audit_ids": audit,
    "note": "Selected before inspecting any A/B disagreement. Two independent draws from the same pool; overlap is allowed and reported.",
    "overlap": sorted(set(aa) & set(audit)),
}, indent=2))
print(f"pool={len(draws)} aa={len(aa)} audit={len(audit)} overlap={len(set(aa)&set(audit))}")
print("wrote", dest)
