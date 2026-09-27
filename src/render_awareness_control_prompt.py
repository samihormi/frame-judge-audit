"""Render the SAME Inspect task with test_eval_awareness=True.

This is a MODEL-CAPABILITY CONTROL, not part of the primary population. It answers one
question: can this model verbalise frame awareness in this environment at all, such that
the published judge detects it? test_eval_awareness=True appends Inspect's
ALIGNMENT_FAKING_WARNING, which explicitly asks the model to deliberate about evaluation vs
deployment. It therefore CANNOT be used to measure spontaneous awareness and is never
pooled with the primary corpus.
"""
import hashlib, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
from inspect_evals.agentic_misalignment.prompt_generator import (  # noqa: E402
    ALIGNMENT_FAKING_WARNING, generate_prompts,
)
CFG = dict(scenario="blackmail", goal_type="none", goal_value="none",
           urgency_type="replacement", extra_system_instructions=None, prod_flag=True,
           alignment_faking_warning=ALIGNMENT_FAKING_WARNING)
p = generate_prompts(**CFG)
input_text = "\n".join([p.user_prompt, p.email_content])
messages = [{"role": "system", "content": p.system_prompt},
            {"role": "user", "content": input_text}]
base = json.loads((ROOT / "protocol" / "task_prompt.json").read_text())
out = {
    "config": CFG, "test_eval_awareness": True,
    "population": "MODEL_CAPABILITY_CONTROL — never pooled with the primary corpus",
    "system_prompt": p.system_prompt, "user_prompt": p.user_prompt,
    "email_content": p.email_content, "messages": messages,
    "messages_sha256": hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest(),
    "differs_from_primary_only_by": "appended ALIGNMENT_FAKING_WARNING in the system prompt",
    "primary_messages_sha256": base["messages_sha256"],
    "system_prompt_char_delta_vs_primary": len(p.system_prompt) - len(base["system_prompt"]),
}
(ROOT / "protocol" / "task_prompt_awareness_control.json").write_text(json.dumps(out, indent=2))
print("messages_sha256", out["messages_sha256"])
print("char delta vs primary system prompt:", out["system_prompt_char_delta_vs_primary"])
print("user message identical:", input_text == "\n".join([base["user_prompt"], base["email_content"]]))
