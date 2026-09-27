"""Does the B edit change anything when A's rule and B's rule are designed to disagree?

SYNTHETIC — tests the instrument, not any model or corpus. Excluded from all corpus claims.
Repeats each (trace, condition) N times with varied seeds to separate a real manipulation
effect from ordinary judge noise.
"""
import argparse, asyncio, hashlib, json, pathlib, sys, types, collections
import httpx
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import judge_frames as jf  # noqa: E402

async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--judge-model", default="gpt-4.1-2025-04-14")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--concurrency", type=int, default=10)
    a = ap.parse_args()
    spec = json.loads((ROOT / "protocol" / "synthetic" / "manipulation_validity.json").read_text())
    out = ROOT / "raw" / "judge" / "manipulation_validity"
    out.mkdir(parents=True, exist_ok=True)
    man = out / "manifest.jsonl"
    sem = asyncio.Semaphore(a.concurrency)
    lock = asyncio.Lock()
    results = []
    async with httpx.AsyncClient() as client:
        async def work(case, cond, rep):
            args = types.SimpleNamespace(judge_model=a.judge_model, base_url=a.base_url,
                                         temperature=0.0, max_tokens=2000, judge_seed=1000 + rep)
            async with sem:
                rec = await jf.call_judge(client, args, cond, f"{case['id']}#r{rep}",
                                          case["reasoning"], 1, None, 0)
                rec["SYNTHETIC"] = True
                rec["case_id"] = case["id"]; rec["rep"] = rep
                rec["designed_acted_on"] = case["acted_on"]
                rec["designed_explicit_frames"] = case["explicit_frames"]
                async with lock:
                    p = out / f"{case['id']}__{cond}__r{rep}.json"
                    p.write_text(json.dumps(rec, indent=2))
                    m = {k: v for k, v in rec.items() if k not in ("raw_response", "parsed", "judge_completion", "judge_reasoning", "raw_text_if_not_json")}
                    m["raw_path"] = str(p.relative_to(ROOT)); m["raw_file_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                    with man.open("a") as f:
                        f.write(json.dumps(m) + "\n")
                    results.append(rec)
        tasks = [work(c, cond, r) for c in spec["cases"] for cond in ("A", "B") for r in range(a.reps)]
        await asyncio.gather(*tasks)

    summary = {"reps_per_cell": a.reps, "judge_model": a.judge_model, "cases": []}
    for c in spec["cases"]:
        row = {"case_id": c["id"], "designed_acted_on": c["acted_on"],
               "designed_explicit_frames": c["explicit_frames"]}
        for cond in ("A", "B"):
            sub = [r for r in results if r["case_id"] == c["id"] and r["condition"] == cond]
            row[f"{cond}_categories"] = dict(collections.Counter(str(r.get("category")) for r in sub))
            row[f"{cond}_scores"] = dict(sorted(collections.Counter(r.get("score") for r in sub).items(), key=lambda kv: str(kv[0])))
            row[f"{cond}_unclear_rate"] = sum(1 for r in sub if r.get("category") == "unclear") / len(sub) if sub else None
            row[f"{cond}_picks_acted_on"] = sum(1 for r in sub if r.get("category") == c["acted_on"]) / len(sub) if sub else None
        summary["cases"].append(row)
    allA = [r for r in results if r["condition"] == "A"]
    allB = [r for r in results if r["condition"] == "B"]
    summary["overall"] = {
        "n_per_condition": len(allA),
        "A_unclear_rate": sum(1 for r in allA if r.get("category") == "unclear") / len(allA),
        "B_unclear_rate": sum(1 for r in allB if r.get("category") == "unclear") / len(allB),
        "A_picks_designed_acted_on": sum(1 for r in allA if r.get("category") == r["designed_acted_on"]) / len(allA),
        "B_picks_designed_acted_on": sum(1 for r in allB if r.get("category") == r["designed_acted_on"]) / len(allB),
    }
    (ROOT / "analysis" / "manipulation_validity.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

asyncio.run(main())
