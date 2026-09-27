# Declared substitution — second corpus (written BEFORE collecting it)

Declared at 2026-09-12 ~03:55 UTC, after the 30-trajectory pilot decision and before any
second-corpus generation.

## Why

The pilot measured **0/30 eligible** (published judge, score >= 2) and **0/30 blackmail**
on `Qwen/Qwen3-32B` for the fixed Inspect no-goal blackmail prompt. Both denominators of
the primary contrast are empty, so the tie-breaker question is unidentifiable in that
corpus. The justification for a second corpus is this measured identification failure —
not an unfavourable effect size, and not a search for a desired direction.

## What changes (exactly one thing)

Target model only:

    Qwen/Qwen3-32B                          ->  deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
    rev 9216db5781bf21249d130ec9da846c4624c16137  rev 711ad2ea6aa40cfca18895e8aca02ab92df1a746

Unchanged: the rendered task prompt (identical messages, identical sha256), the task
configuration, judge A, judge B, the judge model and settings, the outcome grader and its
prompt, eligibility rule, risk categories, analysis code, sampling parameters
(temperature 0.6 / top_p 0.95 / top_k 20 — these are also DeepSeek's documented
recommendations for this model), `max_tokens=8192`, logging.

Server change required by the model: `--reasoning-parser deepseek_r1` instead of `qwen3`,
because R1-style models emit `<think>` without the Qwen3 chat-template switch. Recorded per
attempt via `reasoning_field_used`.

## Why this model and not another

1. It exposes raw chain-of-thought. OpenAI and Anthropic expose only reasoning summaries,
   which the protocol forbids substituting for raw exposed reasoning.
2. It is already cached locally (62 GB, complete, 8 shards) — no integration detour, no
   download, same vLLM, same TP=2 BF16 layout.
3. The source post's own footnote on prior work cites DeepSeek R1 results as consistent
   with its Gemini frame-awareness observations, so it is the principled next candidate
   rather than an arbitrary one.
4. A `deepseek-reasoner` API route was also available but was rejected: the endpoint
   returned `model: "deepseek-flash"` for both `deepseek-chat` and `deepseek-reasoner`
   requests, so the exact model/revision could not be pinned as the protocol requires.

## Pre-committed handling of the result

- Run once, at the same fixed target of 200 fresh draws. No iteration over models.
- Report the outcome whichever way it comes out, including another empty cohort.
- Comparability limitation stated in every claim: a different model family, size and
  post-training pipeline from both Qwen3-32B and the Gemini corpus of the original study.
  A distilled R1 model is not the original study's subject, so nothing measured here
  reanalyses that study's data.
- The Qwen3-32B result remains the primary preregistered-target corpus; the R1-Distill
  corpus is reported as a declared secondary identification attempt.
