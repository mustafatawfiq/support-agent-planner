"""L6 Hand-off: what may go out alone, and what goes to a person.

The send rules run on every ticket from the first one, like the log. The room sees them last.
The agent writes. This code decides, using send-rules.yaml:
- some cases always go to a person (the agent handed off, or the sender is not verified),
- every other reply follows the rule for its ticket type (send or draft),
- a reply marked send must pass the checks first, or it stays a draft.
"""
import re
from datetime import datetime

from helpers import add_row, read_rows

CLAIM_LINK = re.compile(r"\b(sent|sending|resent)\b.{0,30}\b(new|access)\b.{0,10}\blink", re.I | re.S)
CLAIM_REFUND = re.compile(r"\b(opened|created|submitted|raised)\b.{0,30}\brefund request|refund request.{0,20}\b(is|has been) open", re.I | re.S)
PROMISE = re.compile(r"(refund|money).{0,60}\b(approved|processed|issued|done|on its way|sent back)\b"
                     r"|\bdiscount\b|\bguarantee", re.I | re.S)


def hand_off_to_person(ctx, reason, urgency, summary, suggested_reply=""):
    path = ctx.out / "queue" / "people-queue.csv"
    for old in read_rows(path):
        if old["ticket_id"] == ctx.ticket["ticket_id"]:
            ctx.handed_off = {"queue_id": old["queue_id"], "urgency": old["urgency"]}
            return {"result": {"queue_id": old["queue_id"], "note": "Already with a person."}, "show": "Already with a person."}
    queue_id = "Q-" + ctx.ticket["ticket_id"].split("-")[-1]
    urgency = "high" if urgency == "high" else "normal"
    add_row(path, {
        "queue_id": queue_id, "ticket_id": ctx.ticket["ticket_id"], "customer": ctx.ticket["from_name"],
        "urgency": urgency, "reason": reason, "summary": summary,
        "already_checked": ", ".join(ctx.tools_called) or "nothing",
        "suggested_reply": suggested_reply, "added_by": "agent",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    ctx.handed_off = {"queue_id": queue_id, "urgency": urgency}
    when = "today" if urgency == "high" else "within one working day"
    return {"result": {"queue_id": queue_id, "customer_is_told": f"A person from the team replies {when}."},
            "show": f"{queue_id}, urgency {urgency}: {reason}"}


def _code_queue_item(ctx, reason):
    path = ctx.out / "queue" / "people-queue.csv"
    if any(r["ticket_id"] == ctx.ticket["ticket_id"] for r in read_rows(path)):
        return None
    queue_id = "Q-" + ctx.ticket["ticket_id"].split("-")[-1]
    add_row(path, {
        "queue_id": queue_id, "ticket_id": ctx.ticket["ticket_id"], "customer": ctx.ticket["from_name"],
        "urgency": "normal", "reason": reason, "summary": (ctx.reply or {}).get("note_for_team", ""),
        "already_checked": ", ".join(ctx.tools_called) or "nothing",
        "suggested_reply": (ctx.reply or {}).get("text", ""), "added_by": "code",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    return queue_id


def effective_type(ctx):
    if {"check_refund_eligibility", "open_refund_request"} & set(ctx.tools_called):
        return "refund"
    if ctx.reply is not None:
        return ctx.reply["ticket_type"]
    return ctx.ticket_type or "other"


def run_checks(ctx, rules):
    text = (ctx.reply or {}).get("text", "")
    low = text.lower()
    checks = []
    banned = [w for w in rules.get("never_in_replies", []) if w.lower() in low]
    note = (ctx.customer or {}).get("internal_note", "")
    note_words = re.findall(r"[a-z0-9]+", note.lower())
    leaked = [" ".join(note_words[i:i + 3]) for i in range(len(note_words) - 2)
              if " ".join(note_words[i:i + 3]) in " ".join(re.findall(r"[a-z0-9]+", low))]
    checks.append(("No internal words", not banned and not leaked,
                   "ok" if not banned and not leaked else "found: " + ", ".join(banned + leaked[:2])))
    refund_done = any(a.startswith("refund request") for a in ctx.actions)
    promise = PROMISE.search(text) if not refund_done else None
    checks.append(("No promise outside the policy", promise is None,
                   "ok" if promise is None else f"found: \"{promise.group(0)[:60]}\""))
    allowed = rules.get("allowed_link_domains", [])
    hosts = re.findall(r"https?://([^/\s)\]]+)", text)
    off = [h for h in hosts if allowed and not any(h == d or h.endswith("." + d) for d in allowed)]
    checks.append(("Links only to allowed sites", not off, "ok" if not off else "found: " + ", ".join(off[:2])))
    claims = []
    if CLAIM_LINK.search(text) and "new access link" not in ctx.actions:
        claims.append("a new link was sent")
    if CLAIM_REFUND.search(text) and not refund_done:
        claims.append("a refund request was opened")
    checks.append(("No action claimed that did not happen", not claims, "ok" if not claims else "claims " + ", ".join(claims)))
    if str(rules.get("must_name_a_source", "yes")).lower() in ("yes", "true"):
        named = bool((ctx.reply or {}).get("sources")) or any(d in low for d in allowed)
        checks.append(("A source is named", named, "ok" if named else "no source"))
    return checks


def add_review_line(ctx):
    """A declined refund always says how to ask a person to review it. If the agent forgot, code adds it."""
    link = ctx.settings.get("review_link", "")
    if ctx.refund_decision and not ctx.refund_decision["eligible"] and ctx.reply and link not in ctx.reply["text"]:
        ctx.reply["text"] += f"\n\nIf you think this is wrong, you can ask a person to review it: {link}"
        return True
    return False


def holding_reply(ctx):
    first = ctx.ticket["from_name"].split()[0]
    when = "today" if (ctx.handed_off or {}).get("urgency") == "high" else "within one working day"
    return (f"Hi {first},\n\nThank you for your message. A person from our team has it now and will reply {when}."
            f"\n\n{ctx.settings.get('business_name', 'The')} Support")


def decide_delivery(ctx, rules):
    """Returns (mode, reasons, checks). mode is send, draft or person."""
    reasons, checks = [], []
    if add_review_line(ctx):
        reasons.append("The refund was declined and the reply did not say how to ask a person to review it, so code added it.")
    if ctx.reply is None:
        reasons.append("The agent did not finish the ticket.")
        _code_queue_item(ctx, "The agent did not finish this ticket.")
        return "person", reasons, checks
    if ctx.handed_off:
        reasons.append("The agent handed this ticket to a person.")
        return "person", reasons, checks
    if ctx.reply.get("decision") == "needs_person":
        reasons.append("The agent said a person must take it.")
        _code_queue_item(ctx, "The agent said a person must take it.")
        return "person", reasons, checks
    if ctx.verified is False:
        reasons.append("The sender is not verified. Always a person.")
        _code_queue_item(ctx, "Sender not verified.")
        return "person", reasons, checks
    kind = effective_type(ctx)
    mode = rules.get(kind, "draft")
    reasons.append(f"Send rule for '{kind}': {mode}.")
    checks = run_checks(ctx, rules)
    if mode == "send" and not all(ok for _, ok, _ in checks):
        mode = "draft"
        reasons.append("A check failed, so it stays a draft.")
    if ctx.refund_decision and not ctx.refund_decision["eligible"]:
        q = _code_queue_item(ctx, "Refund declined by the rule. The customer was told how to ask a person to review it.")
        if q:
            reasons.append(f"Declined refund added to the people queue ({q}).")
    return mode, reasons, checks


TOOLS = [
    {
        "name": "hand_off_to_person",
        "layer": "L6",
        "label": "Handed the ticket to a person",
        "description": (
            "Give the ticket to a person. Use it for: an angry customer, a legal or bank-dispute threat, a request "
            "for an exception or a special reason, a sender who is not verified, a sales lead for a team, or when "
            "you are not sure. Write a summary so the person does not have to read everything again."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why a person must take it, in a few words."},
                "urgency": {"type": "string", "enum": ["normal", "high"]},
                "summary": {"type": "string", "description": "Who, what they want, what you already checked."},
                "suggested_reply": {"type": "string", "description": "A reply the person can edit and send."},
            },
            "required": ["reason", "urgency", "summary", "suggested_reply"],
            "additionalProperties": False,
        },
        "run": hand_off_to_person,
    }
]
