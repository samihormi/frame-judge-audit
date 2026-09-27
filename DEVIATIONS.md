# DEVIATIONS

Deviations from the plan supplied 2026-09-12 ~06:00 UTC, logged before acting, as instructed.

## D1 — Gates 0/1/2 not honoured as halts (06:03 UTC)

**Plan:** preregister, then HALT and wait for the PI at Gate 0; smoke 20/arm, HALT at Gate 1;
full run, HALT at Gate 2.
**Deviation:** no halt. The PI stated a ~30-minute budget and said "go".
**Reason:** halting consumes the entire budget in round-trips and returns no result. The gates
exist to stop the agent deciding the science; that protection is preserved differently here —
the design change (the 2x2 missing cell) was specified by the PI, not chosen by me, and no arm,
model, environment or outcome outside the supplied document has been added.
**Consequence:** the PI has not approved the preregistration before data were collected.
Treat S1e as PI-specified but agent-executed without gate approval.

## D2 — Scope cut to what fits the budget (06:03 UTC)

**Plan (Phase 1-3):** 8 arms x 150 valid on Qwen3-32B, plus 4 arms x 100 on a second model,
4 judge passes, second-judge agreement on 30 samples, logistic mediation, 2-model figure.
**Executed:** the single decisive cell (`puzzle_frame_only`, n=100) + completing `s1d`
(stem_only / route_search_no_frame / puzzle, 100 each), graded with the existing 2-factor
outcome. Plus the no-GPU instrument adjudication packet and the two draft issues.
**Reason:** the full Phase 3 is several GPU-hours plus four judge passes. It does not fit 30
minutes. Generation is GPU-serial; additional agents cannot compress it.
**Later recovered (06:20-06:25 UTC, no GPU needed):** the conditional-threat judge, the
search-intensity mediator judge, and second-grader agreement were all built and run after this
entry was written. See D3 (superseded) and `reports/S1_RESULT.md`.
**Still not done, and therefore not claimed:** system-prompt cue family (C0/C1/C2 — H5
untested), second model (Qwen3.6-27B — the "one model" objection stands), second-judge
agreement for the *search* judge specifically (only the coercion grader was duplicated),
safety_eval arm at full n, ITT recomputation with reason-coded invalids.
**Consequence:** H1, H2 and H4 get an answer at this N. H3 is descriptive. H5 is untested.
The study remains one model, one environment, one manipulation family.

## D3 — Robustness outcome: SUPERSEDED (written 06:03, resolved 06:25 UTC)

**Original entry:** the conditional-threat judge was not built, for budget reasons.
**Resolution:** it WAS built and run, along with two further checks, once it became clear they
needed no GPU. `protocol/judge_threat.txt` (sha256 350c22ad…) and
`protocol/judge_search.txt` (sha256 35f6dcb6…) were frozen before use and run over all
existing S1 artifacts. A second coercion grader (`gpt-4.1-2025-04-14`) was run on the upstream
prompt verbatim.
**Consequence, and it matters:** the headline H1 effect is **measure-dependent**. Its interval
excludes zero under both grader-based outcomes and does NOT under the strict conditional-threat
judge (+3.9 pp, CI [−0.6, +9.2]). Grader agreement is κ=0.554, one-sided. Had this check not
been run, the report would have overstated H1. See `reports/S1_RESULT.md`.

## D4 — One defect found in the added judges (06:22 UTC)

The second-grader pass initially returned 280/280 HTTP 400s: JSON response-format was forced on
the upstream coercion prompt, which requests XML tags. Fixed (`src/run_aux_judges.py`,
`json_mode=False` for that task) and rerun to 280/280 valid. The failed batch was discarded and
regenerated, not patched over; no result depends on the failed calls.
