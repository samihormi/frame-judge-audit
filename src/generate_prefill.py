"""S1: generate with a frame prefilled into the model's reasoning.

The assistant message carries "<think>\n" + stem + arm + closer; vLLM continues it.
The returned `reasoning` field is the model's OWN continuation and is stored separately
from the injected prefill, which is stored verbatim alongside it.
"""
import argparse, asyncio, hashlib, json, pathlib, time
import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASK = json.loads((ROOT / "protocol" / "task_prompt.json").read_text())
SPEC = None  # set from --spec in __main__
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}


def sha(s): return hashlib.sha256(s.encode()).hexdigest()


def build_prefill(arm: str) -> str:
    return SPEC["common_stem"] + SPEC["arms"][arm] + SPEC["common_closer"]


async def one(client, base, model, arm, draw_id, seed, max_tokens):
    prefill = build_prefill(arm)
    msgs = list(TASK["messages"]) + [{"role": "assistant", "content": "<think>\n" + prefill}]
    payload = {"model": model, "messages": msgs, "max_tokens": max_tokens, "seed": seed,
               **SAMPLING, "continue_final_message": True, "add_generation_prompt": False,
               "stream": False}
    rec = {"attempt_id": f"{draw_id}#a1", "draw_id": draw_id, "arm": arm, "attempt_no": 1,
           "parent_attempt_id": None, "request": payload,
           "task_messages_sha256": TASK["messages_sha256"],
           "prefill_text": prefill, "prefill_sha256": sha(prefill),
           "t_start_unix": time.time()}
    try:
        r = await client.post(f"{base}/v1/chat/completions", json=payload, timeout=1800)
        rec["http_status"] = r.status_code
        rec["raw_response"] = r.json()
        r.raise_for_status(); rec["error"] = None
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"; rec.setdefault("raw_response", None)
        rec.setdefault("http_status", None)
    rec["t_end_unix"] = time.time(); rec["latency_s"] = rec["t_end_unix"] - rec["t_start_unix"]
    cont = final = finish = usage = None
    resp = rec.get("raw_response")
    if isinstance(resp, dict) and resp.get("choices"):
        ch = resp["choices"][0]; m = ch.get("message") or {}
        cont = m.get("reasoning_content") or m.get("reasoning")
        final = m.get("content"); finish = ch.get("finish_reason"); usage = resp.get("usage")
    rec["continuation_content"] = cont          # model's OWN reasoning, excludes our prefill
    rec["reasoning_content"] = (prefill + (cont or "")) if cont is not None else None  # full trace
    rec["final_content"] = final
    rec["finish_reason"] = finish; rec["usage"] = usage
    rec["truncated"] = finish == "length"
    rec["has_continuation"] = bool(cont and cont.strip())
    rec["has_final"] = bool(final and final.strip())
    rec["valid"] = bool(rec["error"] is None and finish == "stop" and rec["has_final"])
    rec["continuation_sha256"] = sha(cont) if cont else None
    rec["final_sha256"] = sha(final) if final else None
    rec["continuation_chars"] = len(cont) if cont else 0
    rec["final_chars"] = len(final) if final else 0
    return rec


async def run(a):
    out = ROOT / "raw" / "generations" / a.tag; out.mkdir(parents=True, exist_ok=True)
    man = out / "manifest.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                if d.get("valid"): done.add(d["draw_id"])
    sem = asyncio.Semaphore(a.concurrency); lock = asyncio.Lock()
    arms = list(SPEC["arms"])
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=a.concurrency + 4)) as client:
        async def work(arm, i):
            draw_id = f"{a.tag}-{arm}-{i:03d}"
            if draw_id in done: return
            async with sem:
                rec = await one(client, a.base_url, a.model, arm, draw_id, a.seed_base + i, a.max_tokens)
                async with lock:
                    k = 1
                    while (out / f"{draw_id}_a{k}.json").exists(): k += 1
                    rec["attempt_id"] = f"{draw_id}#a{k}"; rec["attempt_no"] = k
                    p = out / f"{draw_id}_a{k}.json"; p.write_text(json.dumps(rec, indent=2))
                    m = {k: v for k, v in rec.items() if k not in
                         ("raw_response", "request", "reasoning_content", "continuation_content",
                          "final_content", "prefill_text")}
                    m["raw_path"] = str(p.relative_to(ROOT))
                    m["raw_file_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                    with man.open("a") as f: f.write(json.dumps(m) + "\n")
                    print(f"{draw_id} valid={rec['valid']} cont={rec['continuation_chars']} "
                          f"final={rec['final_chars']} lat={rec['latency_s']:.0f}s", flush=True)
        await asyncio.gather(*[work(arm, i) for arm in arms for i in range(a.n_per_arm)])
    (out / "runtime.json").write_text(json.dumps(
        {"sampling": SAMPLING, "max_tokens": a.max_tokens, "model": a.model,
         "prefill_spec_sha256": sha(json.dumps(SPEC, sort_keys=True)),
         "seed_base": a.seed_base, "n_per_arm": a.n_per_arm}, indent=2))


ap = argparse.ArgumentParser()
ap.add_argument("--spec", default="protocol/s1/PREFILL_CONDITIONS.json")
ap.add_argument("--tag", required=True)
ap.add_argument("--n-per-arm", type=int, default=60)
ap.add_argument("--seed-base", type=int, default=810000)
ap.add_argument("--max-tokens", type=int, default=8192)
ap.add_argument("--concurrency", type=int, default=15)
ap.add_argument("--model", default="qwen3-32b")
ap.add_argument("--base-url", default="http://127.0.0.1:8077")
_a = ap.parse_args()
SPEC = json.loads((ROOT / _a.spec).read_text())
# never overwrite an existing attempt file (preserves prior evidence)
asyncio.run(run(_a))
