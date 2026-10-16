"""L5 Actions and rules: skills, business rules, and the tools that change things.

Only the actions listed under actions_on in settings.yaml are offered to the agent.
Tools marked needs_verified are not offered until the L4 identity check passes.

Rules are code. The refund rule reads its numbers from policies/refund-policy.md, so the policy
text and the rule cannot drift apart. The agent never decides eligibility or exceptions.
Every action checks its own conditions and is safe to call twice.
Nothing here moves money or changes an account: actions write a row for a person, or for your
real system once you connect it.

To add an action: write one function like the ones below, add it to TOOLS with needs_verified,
add its name under actions_on in settings.yaml, name it in a skill, and add a test row for it.
"""
from datetime import datetime

from helpers import add_row, date_words, first_number, header_value, read_rows, table_values, to_date, today_from

POLICY = "policies/refund-policy.md"


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
    window = first_number(rules.get("Refund window, days after the purchase"))
    per_year_text = rules.get("Refunds per customer in 12 months", "")
    per_year = first_number(per_year_text)
    if per_year is None and "no limit" in per_year_text.lower():
        per_year = 10 ** 6
    if window is None or per_year is None:
        return _blocked("the refund policy has no numbers yet (policies/refund-policy.md), so a person must decide.")
    if not row.get("last_purchase_date"):
        return _blocked("no purchase date on the account, so a person must decide.")
    plans_text = rules.get("Plans or products that can be refunded", "all").strip()
    plans = [] if plans_text.lower() in ("", "all") else [x.strip().lower() for x in plans_text.split(",") if x.strip()]
    own_plan = (row.get("plan") or row.get("product") or "").strip()
    window, per_year = int(window), int(per_year)
    bought = to_date(row["last_purchase_date"])
    days = (today_from(ctx.settings) - bought).days
    used = int(first_number(row.get("refunds_last_12_months")) or 0)

    if plans and own_plan.lower() not in plans:
        eligible = False
        reason = f"Refunds are only for {plans_text}. This account has {own_plan or 'no plan on file'}."
        line = f"Refunds are only for {plans_text}."
    elif used >= per_year:
        eligible = False
        reason = f"This customer already had {used} refund(s) in the last 12 months. The limit is {per_year}."
        line = f"At most {per_year} refund(s) per customer in any 12 months."
    elif days > window:
        eligible = False
        reason = f"The last purchase was {days} days ago. Refunds are possible within {window} days."
        line = f"A refund is possible within {window} days of the purchase."
    else:
        eligible = True
        reason = f"The last purchase was {days} days ago, within the {window}-day window."
        line = f"A refund is possible within {window} days of the purchase."

    ctx.refund_decision = {"eligible": eligible, "amount": row.get("last_purchase_amount", ""), "reason": reason}
    return {
        "result": {
            "eligible": eligible,
            "purchase": f"{row.get('last_purchase_amount', '')} on {date_words(bought)}",
            "days_since_purchase": days,
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
        if old["customer_id"] == row["customer_id"] and old["purchase_date"] == row["last_purchase_date"]:
            ctx.actions.append(f"refund request {old['request_id']} (already open)")
            return {"result": {"request_id": old["request_id"], "status": old["status"], "note": "Already open. Not opened twice."},
                    "show": f"Already open: {old['request_id']}. Not opened twice.", "decided_by": "code"}
    days_back = table_values(ctx.folder / POLICY).get("Days until the money is back", "")
    if first_number(days_back) is None:
        days_back = "the time set in our refund policy"
    request_id = "R-" + ctx.ticket["ticket_id"].split("-")[-1]
    add_row(path, {
        "request_id": request_id, "ticket_id": ctx.ticket["ticket_id"], "customer_id": row["customer_id"],
        "amount": row.get("last_purchase_amount", ""), "purchase_date": row["last_purchase_date"],
        "status": "waiting for a person to approve", "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    ctx.actions.append(f"refund request {request_id}")
    next_step = (f"A person approves the request. Then the money is back in {days_back}.")
    return {"result": {"request_id": request_id, "status": "waiting for a person to approve", "what_happens_next": next_step},
            "show": f"{request_id}: waiting for a person to approve.", "decided_by": "code"}


def send_access_link(ctx):
    if not ctx.verified:
        return _blocked("identity not verified, so nothing is sent.")
    row = ctx.customer
    access = row.get("access", "")
    if access == "active":
        return {"result": {"sent": False, "note": "Access is already active. No new link needed. Give the login steps."},
                "show": "Access is active. No link needed.", "decided_by": "code"}
    if access not in ("link_expired", "link_not_used"):
        return _blocked(f"access is '{access}'. A person checks this.")
    days = int(first_number(ctx.settings.get("access_link_valid_days")) or 7)
    path = ctx.out / "outbox" / "access-links.csv"
    for old in read_rows(path):
        if old["ticket_id"] == ctx.ticket["ticket_id"]:
            return {"result": {"sent": True, "note": "Already sent for this ticket. Not sent twice."},
                    "show": "Already sent for this ticket. Not sent twice.", "decided_by": "code"}
    add_row(path, {"ticket_id": ctx.ticket["ticket_id"], "customer_id": row["customer_id"], "sent_to": row["email"],
                   "valid_days": days, "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    ctx.actions.append("new access link")
    return {"result": {"sent": True, "sent_to": row["email"], "from": ctx.settings.get("access_email_from", ""),
                       "works_for_days": days},
            "show": f"New access link sent. It works for {days} days.", "decided_by": "code"}


def open_request(ctx, what, details):
    """A request for a person to do or approve something the agent may not do alone."""
    if not ctx.verified:
        return _blocked("identity not verified, so no request is opened.")
    path = ctx.out / "queue" / "requests.csv"
    for old in read_rows(path):
        if old["ticket_id"] == ctx.ticket["ticket_id"] and old["what"] == what:
            return {"result": {"request_id": old["request_id"], "note": "Already open. Not opened twice."},
                    "show": f"Already open: {old['request_id']}.", "decided_by": "code"}
    request_id = "Q-" + ctx.ticket["ticket_id"].split("-")[-1] + "-" + str(len(read_rows(path)) + 1)
    add_row(path, {"request_id": request_id, "ticket_id": ctx.ticket["ticket_id"],
                   "customer_id": (ctx.customer or {}).get("customer_id", ""), "what": what, "details": details,
                   "status": "waiting for a person", "opened_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    ctx.actions.append(f"request {request_id}: {what}")
    return {"result": {"request_id": request_id, "status": "waiting for a person",
                       "what_happens_next": "A person from the team does it or replies."},
            "show": f"{request_id}: {what}, waiting for a person.", "decided_by": "code"}


TOOLS = [
    {
        "name": "read_skill",
        "layer": "L5",
        "label": "Opened a skill",
        "description": "Open the skill (step-by-step procedure) for a ticket type. Do this first when a skill exists.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Skill name, the same as the ticket type."}},
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
            "Apply the refund policy to the sender's last purchase. Returns eligible yes or no, the reason and "
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
        "description": "Open a refund request for a person to approve. Only works after the rule said eligible.",
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
    {
        "name": "open_request",
        "layer": "L5",
        "needs_verified": True,
        "label": "Opened a request for a person",
        "description": (
            "Open a request for a person to do or approve something you may not do alone, for example a plan "
            "change or a cancellation. Say what, and the details a person needs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "what": {"type": "string", "description": "The request in a few words, for example 'change plan'."},
                "details": {"type": "string", "description": "What the customer asked for, and what you checked."},
            },
            "required": ["what", "details"],
            "additionalProperties": False,
        },
        "run": open_request,
    },
]
