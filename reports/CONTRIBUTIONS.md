# Human / agent contribution record

## Who did what

**Agent (this Claude Code session, lead role) — everything below is machine work:**
- Inspected the runtime, found the installed torch/vLLM/Inspect versions, chose the BF16 TP=2
  layout, launched and managed the servers.
- Retrieved the published judge prompt from the source post and extracted it verbatim;
  constructed judge B as a one-line replacement; produced the diff.
- Vendored and rendered the Inspect `agentic_misalignment` prompt; verified the configuration
  against the installed upstream source.
- Wrote all generation / judging / outcome-labelling / analysis / figure code.
- Ran all generations, all judge calls, all outcome labels, all controls.
- Wrote the protocol, the report, the ledger and this file.
- Found and fixed the `reasoning` vs `reasoning_content` field defect; found the fabricated
  judge quote via the substring check; corrected two wrong counts in its own draft report.

**Independent reviewer (separate agent, bounded):** adversarial check of the raw artifacts
and the headline calculation. Read-only; it did not modify canonical data or redesign
anything.

**Human (the user) — supplied so far:**
- The research question, the fixed protocol constraints, and the decision to execute.
- The machine, the GPUs, the model caches and the authorized API keys.
- The correction that the ARS packet was never installed here.

**Designated validator (2026-09-12):** the annotation packet in `annotation/qwen3_32b/`
was filled by the Cursor agent acting as the designated validator the user assigned —
`random_frame_answers.json`, `random_outcome_answers.json`, and
`annotation/qwen3_32b/HUMAN_VALIDATION.md`. That is **not** independent inter-human
consensus. Cite it as designated-validator review, not as a second blind human.
