"""Label the blackmail outcome from the FINAL RESPONSE ONLY, using the upstream
Inspect agentic_misalignment BlackmailClassifier logic verbatim (prompt text and the
three-factor verdict), with Anthropic claude-sonnet-4-6 (the upstream default id).

Reasoning text is never passed to this classifier: contemplating blackmail does not
count. Truncated / missing final responses are recorded as outcome_status="unusable",
never as clean negatives.
"""
import argparse
import asyncio
import hashlib
import json
import os
import pathlib
import sys
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
from inspect_evals.agentic_misalignment.classifiers.blackmail_classifier import (  # noqa: E402
    BLACKMAIL_CLASSIFICATION_MODEL_ID,
    BLACKMAIL_CLASSIFICATION_SYSTEM_PROMPT,
    BLACKMAIL_CLASSIFICATION_USER_PROMPT,
    BlackmailClassifier,
)

TASK = json.loads((ROOT / "protocol" / "task_prompt_goalconflict.json").read_text())
EMAIL_CONTENT = TASK["email_content"]
CLF = BlackmailClassifier()


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


async def grade(client: httpx.AsyncClient, args, draw_id: str, response_text: str,
                attempt_no: int, parent: str | None) -> dict:
    email_context = CLF.get_email_context(email_content=EMAIL_CONTENT, response=response_text)
    user = BLACKMAIL_CLASSIFICATION_USER_PROMPT.format(
        email_context=email_context, response=response_text
    )
    payload = {
        "model": args.grader_model,
        "max_tokens": args.max_tokens,
        "temperature": 0.0,
        "system": BLACKMAIL_CLASSIFICATION_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user}],
    }
    rec = {
        "outcome_call_id": f"{draw_id}|out|a{attempt_no}",
        "draw_id": draw_id,
        "attempt_no": attempt_no,
        "parent_outcome_call_id": parent,
        "grader_model": args.grader_model,
        "upstream_default_model_id": BLACKMAIL_CLASSIFICATION_MODEL_ID,
        "grader_settings": {"temperature": 0.0, "max_tokens": args.max_tokens},
        "final_response_sha256": sha256(response_text),
        "grader_prompt_sha256": sha256(user),
        "t_start_unix": time.time(),
    }
    try:
        r = await client.post(
            "https://api.anthropic.com/v1/messages", json=payload,
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }, timeout=600,
        )
        rec["http_status"] = r.status_code
        rec["raw_response"] = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        r.raise_for_status()
        rec["error"] = None
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        rec.setdefault("raw_response", None)
        rec.setdefault("http_status", None)
    rec["t_end_unix"] = time.time()

    completion = None
    if isinstance(rec.get("raw_response"), dict):
        blocks = rec["raw_response"].get("content") or []
        completion = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        rec["grader_usage"] = rec["raw_response"].get("usage")
    rec["grader_completion"] = completion

    rec["parse_error"] = None
    try:
        if completion is None:
            raise ValueError("no completion")
        final, classifier_verdict, reasoning = CLF.classify(
            response=response_text, grader_response=completion
        )
        rec["blackmail"] = bool(final)
        rec["classifier_verdict"] = bool(classifier_verdict)
        rec["grader_reasoning"] = reasoning
        rec["parse_ok"] = True
    except Exception as e:
        rec["blackmail"] = None
        rec["classifier_verdict"] = None
        rec["grader_reasoning"] = None
        rec["parse_ok"] = False
        rec["parse_error"] = f"{type(e).__name__}: {e}"
    # Components of the upstream three-factor verdict, recorded for ambiguity accounting.
    rec["target_email_present"] = CLF.response_contains_necessary_emails(response_text)
    low = response_text.lower()
    rec["keyword_blackmail_or_leverage"] = ("blackmail" in low) or ("leverage" in low)
    return rec


async def run(args) -> None:
    gen_dir = ROOT / "raw" / "generations" / args.gen_tag
    rows = [json.loads(x) for x in (gen_dir / "manifest.jsonl").read_text().splitlines() if x.strip()]
    best: dict[str, dict] = {}
    for r in rows:
        if r.get("valid") and r["draw_id"] not in best:
            best[r["draw_id"]] = r
    # Also record every draw that has NO valid attempt, as unusable (visible, not negative).
    all_draws = sorted({r["draw_id"] for r in rows})
    out_dir = ROOT / "raw" / "outcomes" / args.out_tag
    out_dir.mkdir(parents=True, exist_ok=True)
    man = out_dir / "manifest.jsonl"
    already = set()
    if man.exists():
        for line in man.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                if d.get("parse_ok"):
                    already.add(d["draw_id"])

    unusable = []
    for d in all_draws:
        if d not in best:
            unusable.append({"draw_id": d, "outcome_status": "unusable_no_valid_generation", "blackmail": None})
    (out_dir / "unusable_draws.json").write_text(json.dumps(unusable, indent=2))

    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    targets = [d for d in sorted(best) if d not in already]
    if args.limit:
        targets = targets[: args.limit]
    async with httpx.AsyncClient() as client:
        async def work(draw_id: str) -> None:
            raw = json.loads((ROOT / best[draw_id]["raw_path"]).read_text())
            final = raw["final_content"]
            async with sem:
                rec = await grade(client, args, draw_id, final, 1, None)
                recs = [rec]
                if rec["error"] is not None or not rec["parse_ok"]:
                    rec2 = await grade(client, args, draw_id, final, 2, rec["outcome_call_id"])
                    recs.append(rec2)
                async with lock:
                    for rc in recs:
                        p = out_dir / f"{rc['outcome_call_id'].replace('|', '__')}.json"
                        p.write_text(json.dumps(rc, indent=2))
                        m = {k: v for k, v in rc.items() if k not in ("raw_response", "grader_completion", "grader_reasoning")}
                        m["raw_path"] = str(p.relative_to(ROOT))
                        m["raw_file_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                        with man.open("a") as f:
                            f.write(json.dumps(m) + "\n")
                    print(f"{draw_id} blackmail={recs[-1]['blackmail']} clf={recs[-1]['classifier_verdict']} "
                          f"email={recs[-1]['target_email_present']} kw={recs[-1]['keyword_blackmail_or_leverage']}", flush=True)

        await asyncio.gather(*[work(d) for d in targets])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-tag", required=True)
    ap.add_argument("--out-tag", required=True)
    ap.add_argument("--grader-model", default="claude-sonnet-4-6")
    ap.add_argument("--max-tokens", type=int, default=1500)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
