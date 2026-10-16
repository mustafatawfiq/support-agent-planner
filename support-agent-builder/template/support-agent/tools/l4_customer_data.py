"""L4 Customer data: who is writing, and is it really them.

Code looks up the customer by the address the message came from. Never by an address
typed inside the message. The agent cannot ask for anyone else's account.

The tests read data/customers.csv, a test copy with made-up people. Your real customer data
connects in fetch_customer at the bottom. Until then it says "not connected".
Columns: customer_id, name, email and status are needed. Add the columns your business needs.
The agent never sees customer_id, internal_note (shown to it as INTERNAL) or the columns listed
under never_show_fields in settings.yaml.
"""
import re

from helpers import date_words, mask_email, read_rows, to_date

# An account with one of these statuses cannot be verified. A cancelled plan still has an owner, so it is not here.
CLOSED = ("closed", "deleted", "banned")


class NotConnected(RuntimeError):
    pass


def _sender(ctx):
    return ctx.ticket["from_email"].strip().lower()


def _account_for_sender(ctx):
    if getattr(ctx, "live", False):
        return fetch_customer(_sender(ctx))
    for row in read_rows(ctx.folder / "data" / "customers.csv"):
        if row.get("email", "").strip().lower() == _sender(ctx):
            return row
    return None


def _shown(value):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return date_words(to_date(value))
    return value


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
    hidden = {"customer_id", "internal_note", "email"} | set(ctx.settings.get("never_show_fields") or [])
    facts = {"found": True, **{k: _shown(v) for k, v in row.items() if k not in hidden}}
    if row.get("internal_note"):
        facts["INTERNAL_note_never_share"] = row["internal_note"]
    return {"result": facts, "show": f"Found {row.get('name', 'the customer')}, status {row.get('status', '')}.",
            "decided_by": "code"}


def verify_identity(ctx):
    row = _account_for_sender(ctx)
    ctx.verified = row is not None and row.get("status", "").strip().lower() not in CLOSED
    if ctx.verified:
        ctx.customer = row
        reason = "The sender's address matches the account on file."
    elif row is not None:
        reason = "The account is closed. No account action is allowed. A person checks it."
    else:
        reason = ("The sender's address does not match any account. No account action is allowed. "
                  "Ask them to write from the email on their account.")
    return {
        "result": {"verified": ctx.verified, "reason": reason},
        "show": ("Identity checked: the sender's address matches the account." if ctx.verified
                 else "Not verified: " + reason),
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


# ---- Your real customer data -------------------------------------------------------------
# Fill this in when you connect your customer data (billing tool, CRM, shop, your own database).
# Rules: read only; keys from .env with helpers.env_value("NAME"); return only the fields the
# agent needs, with the same column names as data/customers.csv; return None if no account
# uses this address.

def fetch_customer(email):
    raise NotConnected("Customer data is not connected yet. The tests use data/customers.csv.")
