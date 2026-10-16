"""L5 Actions and rules: skills, business rules, and the tools that change things.

Tools marked needs_verified are not even offered to the agent until the L4 identity check passes.

The refund rule is code. It reads its numbers from policies/refund-policy.md, so the policy text
and the rule cannot drift apart. The agent never decides eligibility or exceptions.
Every action checks its own conditions and is safe to call twice.
"""
from datetime import datetime

from helpers import (add_row, date_words, first_number, header_value, read_rows, table_values,
                     to_date, today_from)

POLICY = "policies/refund-policy.md"
ACCESS_LINK_DAYS = 7


def _blocked(why):
    return {"result": {"allowed": False, "error": why}, "show": f"Blocked by code: {why}", "error": True,
            "decided_by": "code"}


def read_skill(ctx, name):
    path = ctx.folder / "skills" / f"{name}.md"
    if not path.exists():
        names = ", ".join(p.stem for p in sorted((ctx.folder / "skills").glob("*.md")))
        return {"result": {"error": f"No skill called {name}. Skills: {names}"}, "show": f"No skill {name}", "error": True}
    ctx.skills_read.append(name)
    return {"result": {"skill": name, "steps": path.read_text()}, "show": f"skills/{name}.md"}


def check_refund_eligibility(ctx):
    if not ctx.verified:
        return _blocked("identity not verified, so no account action.")
    row = ctx.customer
    rules = table_values(ctx.folder / POLICY)
    window = int(first_number(rules.get("Refund window, days after the charge")) or 0)
    per_year = int(first_number(rules.get("Refunds per member in 12 months")) or 0)
    today = today_from(ctx.settings)
    charged = to_date(row["last_charge_date"])
    days = (today - charged).days
    used = int(row.get("refunds_last_12_months") or 0)

    if used >= per_year:
        eligible, reason = False, f"This member already had {used} refund in the last 12 months. The limit is {per_year}."
        line = f"Rule 2: one refund per member in any 12 months."
    elif days > window:
        eligible, reason = False, f"The last charge was {days} days ago. Refunds are possible within {window} days."
        line = f"Rule 1: a refund is possible within {window} days of a charge."
    else:
        eligible, reason = True, f"The last charge was {days} days ago, within the {window}-day window. No refund in the last 12 months."
        line = f"Rule 1: a refund is possible within {window} days of a charge."

    ctx.refund_decision = {"eligible": eligible, "amount": row["last_charge_amount"], "reason": reason}
    return {
        "result": {
            "eligible": eligible,
            "charge": f"{row['last_charge_amount']} USD on {date_words(charged)}",
            "days_since_charge": days,
            "reason": reason,
            "policy_line": line,
            "policy_link": header_value(ctx.folder / POLICY, "Link"),
            "ask_a_person_to_review": ctx.settings.get("review_link", ""),
        },
        "show": ("Eligible. " if eligible else "Not eligible. ") + reason,
        "decided_by": "code",
    }


def open_refund_request(ctx):
    if not ctx.verified:
        return _blocked("identity not verified, so no account action.")
    if not ctx.refund_decision or not ctx.refund_decision["eligible"]:
        return _blocked("the refund rule did not say eligible.")
    row = ctx.customer
    path = ctx.out / "queue" / "refund-requests.csv"
    for old in read_rows(path):
        if old["customer_id"] == row["customer_id"] and old["charge_date"] == row["last_charge_date"]:
            ctx.actions.append(f"refund request {old['request_id']} (already open)")
            return {"result": {"request_id": old["request_id"], "status": old["status"], "note": "Already open. Not opened twice."},
                    "show": f"Already open: {old['request_id']}. Not opened twice.", "decided_by": "code"}

    amount = float(row["last_charge_amount"])
    limit = float(ctx.settings.get("auto_refund_limit_usd") or 0)
    rules = table_values(ctx.folder / POLICY)
    days_back = rules.get("Days until the money is back on the card", "5 to 10 working days")
    if ctx.settings.get("eligible_refunds") == "auto_under_limit" and amount <= limit:
        status = "refunded (test mode, no money moved)"
        next_step = f"The refund is done. The money is back on the card in {days_back}. Membership ends today."
    else:
        status = "waiting for a person to approve"
        next_step = (f"A person approves the request within one working day. Then the money is back on the card "
                     f"in {days_back}. Membership ends on the day it is approved.")
    request_id = "R-" + ctx.ticket["ticket_id"].split("-")[-1]
    add_row(path, {
        "request_id": request_id, "ticket_id": ctx.ticket["ticket_id"], "customer_id": row["customer_id"],
        "amount_usd": f"{amount:.2f}", "charge_date": row["last_charge_date"], "status": status,
        "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    ctx.actions.append(f"refund request {request_id}")
    return {"result": {"request_id": request_id, "amount_usd": f"{amount:.2f}", "status": status, "what_happens_next": next_step},
            "show": f"{request_id} for {amount:.2f} USD: {status}.", "decided_by": "code"}


def send_access_link(ctx):
    if not ctx.verified:
        return _blocked("identity not verified, so nothing is sent.")
    row = ctx.customer
    if row["access"] == "active":
        return {"result": {"sent": False, "note": "Access is already active. No new link needed. Give the login steps."},
                "show": "Access is active. No link needed.", "decided_by": "code"}
    if row["access"] not in ("link_expired", "link_not_used"):
        return _blocked(f"access is '{row['access']}'. A person checks this.")
    path = ctx.out / "outbox" / "access-links.csv"
    for old in read_rows(path):
        if old["ticket_id"] == ctx.ticket["ticket_id"]:
            return {"result": {"sent": True, "note": "Already sent for this ticket. Not sent twice."},
                    "show": "Already sent for this ticket. Not sent twice.", "decided_by": "code"}
    add_row(path, {"ticket_id": ctx.ticket["ticket_id"], "customer_id": row["customer_id"], "sent_to": row["email"],
                   "valid_days": ACCESS_LINK_DAYS, "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    ctx.actions.append("new access link")
    return {"result": {"sent": True, "sent_to": row["email"], "from": ctx.settings.get("access_email_from", ""),
                       "arrives_within": "5 minutes", "works_for_days": ACCESS_LINK_DAYS},
            "show": f"New access link sent. It works for {ACCESS_LINK_DAYS} days.", "decided_by": "code"}


TOOLS = [
    {
        "name": "read_skill",
        "layer": "L5",
        "label": "Opened a skill",
        "description": "Open the skill (step-by-step procedure) for a ticket type. Do this first when a skill exists.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Skill name, for example refund."}},
            "required": ["name"],
            "additionalProperties": False,
        },
        "run": read_skill,
    },
    {
        "name": "check_refund_eligibility",
        "layer": "L5",
        "needs_verified": True,
        "label": "Checked the refund rule",
        "description": (
            "Apply the refund policy to the sender's last charge. Returns eligible yes or no, the reason and "
            "the policy line. The result is final for you: report it, never change it."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "run": check_refund_eligibility,
    },
    {
        "name": "open_refund_request",
        "layer": "L5",
        "needs_verified": True,
        "label": "Opened a refund request",
        "description": "Open a refund request for the sender's last charge. Only works after the rule said eligible.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "run": open_refund_request,
    },
    {
        "name": "send_access_link",
        "layer": "L5",
        "needs_verified": True,
        "label": "Sent a new access link",
        "description": "Send the sender a new access link if their link expired or was never used.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "run": send_access_link,
    },
]
