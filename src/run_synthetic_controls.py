"""Validity control: run judges A and B over synthetic traces to confirm the judge fires,
the parser works, and A/B can diverge on a mixed-frame case by design.

SYNTHETIC. Excluded from all scientific results.
"""
import asyncio, json, pathlib, sys, types, argparse, os
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import judge_frames as jf  # noqa: E402
import httpx  # noqa: E402

async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge-model", default="gpt-4.1-2025-04-14")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    a = ap.parse_args()
    args = types.SimpleNamespace(
        judge_model=a.judge_model, base_url=a.base_url, temperature=0.0,
        max_tokens=2000, judge_seed=7,
    )
    cases = json.loads((ROOT / "protocol" / "synthetic" / "controls.json").read_text())["cases"]
    out = ROOT / "raw" / "judge" / "synthetic_controls"
    out.mkdir(parents=True, exist_ok=True)
    man = out / "manifest.jsonl"
    async with httpx.AsyncClient() as client:
        for c in cases:
            for cond in ("A", "B"):
                rec = await jf.call_judge(client, args, cond, c["id"], c["reasoning"], 1, None, 0)
                rec["SYNTHETIC"] = True
                rec["expectation"] = c["expect"]
                (out / f"{c['id']}__{cond}.json").write_text(json.dumps(rec, indent=2))
                with man.open("a") as f:
                    f.write(json.dumps({k: v for k, v in rec.items() if k not in ("raw_response", "parsed", "judge_completion", "raw_text_if_not_json")}) + "\n")
                print(f"{c['id']:28} {cond}  score={rec.get('score')}  cat={rec.get('category')}  "
                      f"detail={str(rec.get('perceived_situation_detail'))[:42]!r}  quotes_ok={rec.get('all_quotes_verbatim')}")

asyncio.run(main())
