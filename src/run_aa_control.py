"""A/A instability control: repeat judge A on the prespecified ids, then compare A/A and A/B
on those SAME ids. Ids were fixed in protocol/control_ids_*.json before inspecting anything.
"""
import argparse, asyncio, hashlib, json, pathlib, sys, types
import httpx
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import judge_frames as jf  # noqa: E402

async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--gen-tags", required=True)
    ap.add_argument("--judge-tags", required=True)
    ap.add_argument("--out-tag", required=True)
    ap.add_argument("--judge-model", default="gpt-4.1-2025-04-14")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--concurrency", type=int, default=10)
    a = ap.parse_args()
    ids = json.loads((ROOT / "protocol" / f"control_ids_{a.label}.json").read_text())["aa_repeat_ids"]
    gen = {}
    for t in a.gen_tags.split(","):
        for line in (ROOT / "raw" / "generations" / t / "manifest.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("valid") and r["draw_id"] not in gen:
                    gen[r["draw_id"]] = r
    # judge A/A uses a DIFFERENT judge seed so it measures ordinary run-to-run instability
    args = types.SimpleNamespace(judge_model=a.judge_model, base_url=a.base_url,
                                 temperature=0.0, max_tokens=2000, judge_seed=991)
    out = ROOT / "raw" / "judge" / a.out_tag
    out.mkdir(parents=True, exist_ok=True)
    man = out / "manifest.jsonl"
    sem = asyncio.Semaphore(a.concurrency)
    async with httpx.AsyncClient() as client:
        async def work(d: str) -> None:
            reasoning = json.loads((ROOT / gen[d]["raw_path"]).read_text())["reasoning_content"]
            async with sem:
                rec = await jf.call_judge(client, args, "A", d, reasoning, 1, None, 0)
                rec["control"] = "A_repeat"
                rec["condition"] = "A2"
                p = out / f"{d}__A2.json"
                p.write_text(json.dumps(rec, indent=2))
                m = {k: v for k, v in rec.items() if k not in ("raw_response", "parsed", "judge_completion", "judge_reasoning", "raw_text_if_not_json")}
                m["raw_path"] = str(p.relative_to(ROOT)); m["raw_file_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                with man.open("a") as f:
                    f.write(json.dumps(m) + "\n")
                print(f"{d} A2 score={rec.get('score')} cat={rec.get('category')}", flush=True)
        missing = [d for d in ids if d not in gen]
        await asyncio.gather(*[work(d) for d in ids if d in gen])
    (out / "control_meta.json").write_text(json.dumps({
        "ids_requested": ids, "ids_missing_generation": missing,
        "judge_seed_repeat": 991, "judge_seed_original": 7,
        "note": "A2 = judge A re-run with a different seed, same model/settings; measures ordinary judge instability.",
    }, indent=2))
    print("missing repeats:", missing)

asyncio.run(main())
