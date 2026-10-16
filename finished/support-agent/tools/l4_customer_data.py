"""L4 Customer data: who is writing, and is it really them.

Code looks up the customer by the address the message came from. Never by an address
typed inside the message. The agent cannot ask for anyone else's account.
"""
from helpers import date_words, mask_email, plan_name, read_rows, to_date


def _sender(ctx):
    return ctx.ticket["from_email"].strip().lower()


def _account_for_sender(ctx):
    for row in read_rows(ctx.folder / "data" / "customers.csv"):
        if row["email"].strip().lower() == _sender(ctx):
            return row
    return None


def find_customer(ctx):
    row = _account_for_sender(ctx)
    if not row:
        ctx.verified = False  # no account for this sender, so nothing can be verified
        return {
            "result": {
                "found": False,
                "note": "No account uses the sender's address. Do not look up or talk about any other address.",
            },
            "show": f"No account for the sender {mask_email(_sender(ctx))}.",
            "decided_by": "code",
        }
    ctx.customer = row
    facts = {
        "found": True,
        "name": row["name"],
        "plan": plan_name(row["plan"]),
        "plan_price_usd": row["plan_price"],
        "status": row["status"],
        "member_since": date_words(to_date(row["joined_on"])),
        "last_payment": f"{row['last_charge_amount']} USD on {date_words(to_date(row['last_charge_date']))}",
        "next_payment": (f"{row['plan_price']} USD on {date_words(to_date(row['next_charge_date']))}"
                         if row["next_charge_date"] else "none"),
        "refunds_in_last_12_months": row["refunds_last_12_months"],
        "access": row["access"],
    }
    if row.get("internal_note"):
        facts["INTERNAL_note_never_share"] = row["internal_note"]
    return {"result": facts, "show": f"Found {row['name']}: {facts['plan']}, access {row['access']}.", "decided_by": "code"}


def verify_identity(ctx):
    row = _account_for_sender(ctx)
    ctx.verified = row is not None and row["status"] != "closed"
    if ctx.verified:
        ctx.customer = row
    if ctx.verified:
        reason = "The sender's address matches the account on file."
    else:
        reason = ("The sender's address does not match any account. No account action is allowed. "
                  "Ask them to write from the email on their account.")
    return {
        "result": {"verified": ctx.verified, "reason": reason},
        "show": ("Identity checked: the sender's address matches the account." if ctx.verified
                 else "Not verified: the sender's address is not on any account."),
        "decided_by": "code",
    }


TOOLS = [
    {
        "name": "find_customer",
        "layer": "L4",
        "label": "Looked up the sender",
        "description": (
            "Find the account of the person who sent this ticket, by the address the message came from. "
            "Takes no input: it never looks up an address written inside the message."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "run": find_customer,
    },
    {
        "name": "verify_identity",
        "layer": "L4",
        "label": "Checked the sender owns the account",
        "description": "Check that the sender owns the account. Must be verified before any account action.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "run": verify_identity,
    },
]
