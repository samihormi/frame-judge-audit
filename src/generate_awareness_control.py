"""Generate trajectories for the fixed Inspect agentic_misalignment no-goal blackmail
prompt against a local vLLM server, preserving the complete raw provider output.

One prompt -> N stochastic draws. Each logical draw has a stable id; every attempt is
written to disk, including failures and truncations.
"""
import argparse
import asyncio
import hashlib
import json
import os
import pathlib
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASK = json.loads((ROOT / "protocol" / "task_prompt_awareness_control.json").read_text())

# Qwen3-32B documented thinking-mode sampling defaults.
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
THINKING_KWARG = True  # set False for R1-style templates (see --no-thinking-kwarg)


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


async def server_info(client: httpx.AsyncClient, base: str) -> dict:
    r = await client.get(f"{base}/v1/models", timeout=30)
    r.raise_for_status()
    return r.json()


async def one_attempt(
    client: httpx.AsyncClient, base: str, model: str, draw_id: str, attempt_no: int,
    seed: int, max_tokens: int, parent_attempt_id: str | None,
) -> dict:
    attempt_id = f"{draw_id}#a{attempt_no}"
    payload = {
        "model": model,
        "messages": TASK["messages"],
        "max_tokens": max_tokens,
        "seed": seed,
        "temperature": SAMPLING["temperature"],
        "top_p": SAMPLING["top_p"],
        "top_k": SAMPLING["top_k"],
        "stream": False,
    }
    if THINKING_KWARG:
        # Explicitly enable Qwen3 thinking mode (do not rely on template default).
        # R1-style templates do not take this kwarg and always emit <think>.
        payload["chat_template_kwargs"] = {"enable_thinking": True}
    rec = {
        "attempt_id": attempt_id,
        "draw_id": draw_id,
        "attempt_no": attempt_no,
        "parent_attempt_id": parent_attempt_id,
        "request": payload,
        "task_messages_sha256": TASK["messages_sha256"],
        "t_start_unix": time.time(),
    }
    try:
        r = await client.post(f"{base}/v1/chat/completions", json=payload, timeout=1800)
        rec["http_status"] = r.status_code
        rec["raw_response"] = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        rec["raw_text_if_not_json"] = None if rec["raw_response"] is not None else r.text[:20000]
        r.raise_for_status()
        rec["error"] = None
    except Exception as e:  # transport / HTTP error
        rec["error"] = f"{type(e).__name__}: {e}"
        rec.setdefault("raw_response", None)
        rec.setdefault("http_status", None)
    rec["t_end_unix"] = time.time()
    rec["latency_s"] = rec["t_end_unix"] - rec["t_start_unix"]

    # Extract separately: reasoning vs final response. No fallback substitution.
    reasoning, content, finish, usage = None, None, None, None
    resp = rec.get("raw_response")
    if isinstance(resp, dict) and resp.get("choices"):
        ch = resp["choices"][0]
        msg = ch.get("message") or {}
        # vLLM 0.19.0 exposes parsed reasoning as message["reasoning"];
        # older/other servers use "reasoning_content". Record which field was present.
        reasoning = msg.get("reasoning_content")
        rec["reasoning_field_used"] = "reasoning_content" if reasoning else None
        if not reasoning:
            reasoning = msg.get("reasoning")
            if reasoning:
                rec["reasoning_field_used"] = "reasoning"
        content = msg.get("content")
        finish = ch.get("finish_reason")
        usage = resp.get("usage")
    rec["reasoning_content"] = reasoning
    rec["final_content"] = content
    rec["finish_reason"] = finish
    rec["usage"] = usage
    rec["truncated"] = finish == "length"
    rec["has_reasoning"] = bool(reasoning and reasoning.strip())
    rec["has_final"] = bool(content and content.strip())
    rec["valid"] = bool(
        rec["error"] is None and finish == "stop" and rec["has_reasoning"] and rec["has_final"]
    )
    rec["reasoning_sha256"] = sha256(reasoning) if reasoning else None
    rec["final_sha256"] = sha256(content) if content else None
    rec["reasoning_chars"] = len(reasoning) if reasoning else 0
    rec["final_chars"] = len(content) if content else 0
    return rec


async def run(args: argparse.Namespace) -> None:
    out_dir = ROOT / "raw" / "generations" / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "manifest.jsonl"
    done = set()
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                if d.get("valid"):
                    done.add(d["draw_id"])
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    limits = httpx.Limits(max_connections=args.concurrency + 4)
    async with httpx.AsyncClient(base_url="", limits=limits) as client:
        info = await server_info(client, args.base_url)
        runtime = {
            "base_url": args.base_url,
            "models_endpoint": info,
            "sampling": SAMPLING,
            "max_tokens": args.max_tokens,
            "tag": args.tag,
            "started_unix": time.time(),
            "vllm_version": os.environ.get("VLLM_VERSION_RECORDED", "0.19.0"),
        }
        (out_dir / "runtime.json").write_text(json.dumps(runtime, indent=2))

        async def work(i: int) -> None:
            draw_id = f"{args.tag}-{i:04d}"
            if draw_id in done:
                return
            async with sem:
                seed = args.seed_base + i
                rec = await one_attempt(client, args.base_url, args.model, draw_id, 1, seed, args.max_tokens, None)
                recs = [rec]
                # At most one bounded retry, transport/HTTP failure ONLY.
                if rec["error"] is not None:
                    rec2 = await one_attempt(
                        client, args.base_url, args.model, draw_id, 2, seed,
                        args.max_tokens, rec["attempt_id"],
                    )
                    recs.append(rec2)
                async with lock:
                    for rc in recs:
                        p = out_dir / f"{rc['attempt_id'].replace('#', '_')}.json"
                        p.write_text(json.dumps(rc, indent=2))
                        rc_m = {k: v for k, v in rc.items() if k not in ("raw_response", "request", "reasoning_content", "final_content", "raw_text_if_not_json")}
                        rc_m["raw_path"] = str(p.relative_to(ROOT))
                        rc_m["raw_file_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                        with manifest.open("a") as f:
                            f.write(json.dumps(rc_m) + "\n")
                    ok = sum(1 for rc in recs if rc["valid"])
                    print(
                        f"{draw_id} valid={ok} finish={recs[-1]['finish_reason']} "
                        f"reason_chars={recs[-1]['reasoning_chars']} final_chars={recs[-1]['final_chars']} "
                        f"lat={recs[-1]['latency_s']:.1f}s", flush=True,
                    )

        await asyncio.gather(*[work(i) for i in range(args.start_index, args.start_index + args.n)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--start-index", type=int, default=0)
    ap.add_argument("--seed-base", type=int, default=100000)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--model", default="qwen3-32b")
    ap.add_argument("--base-url", default="http://127.0.0.1:8077")
    ap.add_argument("--no-thinking-kwarg", action="store_true",
                    help="omit chat_template_kwargs.enable_thinking (R1-style templates)")
    a = ap.parse_args()
    global THINKING_KWARG
    THINKING_KWARG = not a.no_thinking_kwarg
    asyncio.run(run(a))


if __name__ == "__main__":
    main()
