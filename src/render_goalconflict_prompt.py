"""Render the Inspect agentic_misalignment no-goal blackmail prompt, verbatim from
vendored upstream source, and save it with a hash.

Config (fixed by protocol):
  scenario=blackmail goal_type=none goal_value=none urgency_type=replacement
  test_eval_awareness=False prod=True
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))

from inspect_evals.agentic_misalignment.prompt_generator import (  # noqa: E402
    ALIGNMENT_FAKING_WARNING,
    generate_prompts,
)

CFG = dict(
    scenario="blackmail",
    goal_type="explicit",
    goal_value="safety",
    urgency_type="replacement",
    extra_system_instructions=None,
    prod_flag=True,
    alignment_faking_warning=None,  # test_eval_awareness=False
)


def main() -> None:
    p = generate_prompts(**CFG)
    # Mirrors inspect_evals.agentic_misalignment.agentic_misalignment exactly:
    #   input_text = "\n".join([prompts.user_prompt, prompts.email_content])
    input_text = "\n".join([p.user_prompt, p.email_content])
    messages = [
        {"role": "system", "content": p.system_prompt},
        {"role": "user", "content": input_text},
    ]
    out = {
        "config": {k: v for k, v in CFG.items()},
        "test_eval_awareness": False,
        "alignment_faking_warning_text_if_enabled": ALIGNMENT_FAKING_WARNING,
        "system_prompt": p.system_prompt,
        "user_prompt": p.user_prompt,
        "email_content": p.email_content,
        "messages": messages,
        "messages_sha256": hashlib.sha256(
            json.dumps(messages, sort_keys=True).encode()
        ).hexdigest(),
        "system_prompt_sha256": hashlib.sha256(p.system_prompt.encode()).hexdigest(),
        "user_message_sha256": hashlib.sha256(input_text.encode()).hexdigest(),
    }
    dest = ROOT / "protocol" / "task_prompt_goalconflict.json"
    dest.write_text(json.dumps(out, indent=2))
    (ROOT / "protocol" / "task_prompt_goalconflict_rendered.txt").write_text(
        "=== SYSTEM ===\n" + p.system_prompt + "\n\n=== USER ===\n" + input_text + "\n"
    )
    print("wrote", dest)
    print("messages_sha256", out["messages_sha256"])
    print("system chars", len(p.system_prompt), "user chars", len(input_text))


if __name__ == "__main__":
    main()
