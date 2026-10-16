"""L7 Log and tests: one line per step, so anyone can answer "why did it say that?".

Personal data is masked in the log: emails keep only the first letter, names become initials.
The tests live in tests/expected.csv and run with the eval script.
"""
import json
from datetime import datetime

from helpers import header_value, mask_email


def _mask(ctx, text):
    text = mask_email(text)
    for name in {ctx.ticket.get("from_name", ""), (ctx.customer or {}).get("name", "")}:
        if name and name.split():
            initials = " ".join(p[0] + "." for p in name.split())
            text = text.replace(name, initials).replace(name.split()[0], initials.split()[0])
    return text


def write_step(ctx, event):
    line = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "ticket": ctx.ticket["ticket_id"],
        "layer": event.get("layer", ""),
        "step": "model call" if event.get("kind") == "usage" else event.get("kind"),
        "tool": event.get("tool", ""),
        "by": event.get("by", "agent"),
        "customer": (ctx.customer or {}).get("customer_id", ""),
        "verified": {True: "sender address matches the account", False: "not verified", None: ""}[ctx.verified],
        "input": event.get("input", ""),
        "output": event.get("show", "") or event.get("text", "")
                  or (f"{event.get('tokens_in')} tokens in, {event.get('tokens_out')} out" if event.get("kind") == "usage" else ""),
        "model": ctx.model_id,
        "run": ctx.run_mode,
        "effort": ctx.settings.get("effort", ""),
        "request_id": event.get("request_id", ""),
        "cost_usd": round(ctx.cost, 5),
        "policy_version": (header_value(ctx.folder / "policies" / "refund-policy.md", "Version")
                           if (ctx.folder / "policies" / "refund-policy.md").exists() else ""),
    }
    path = ctx.out / "log" / "steps.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(_mask(ctx, json.dumps(line, ensure_ascii=False)) + "\n")
