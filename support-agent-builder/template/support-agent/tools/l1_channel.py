"""L1 Channel: what comes in, before the agent sees anything, and where replies go.

Plain code. Every reply that goes out carries a line saying an AI agent wrote it.
A message that arrives twice (same message id) is skipped. An automatic reply
(out of office, bounce) is skipped, so the agent never answers a robot and starts a loop.

The tests read inbox/tickets.csv. Your real help desk or inbox connects in the two functions at
the bottom, fetch_new_messages and save_draft. Until then they say "not connected".
"""
HOLDING_LABEL = "This is an automatic message."
AUTO_SUBJECTS = ("automatic reply", "auto:", "out of office", "undeliverable", "delivery status notification")
INBOX_COLUMNS = ["ticket_id", "received_at", "message_id", "from_name", "from_email", "subject", "message",
                 "auto_submitted"]


class NotConnected(RuntimeError):
    pass


def ai_label(settings):
    return f"This reply was written by {settings.get('business_name', 'our')}'s AI support agent."


def check_incoming(ticket, all_tickets):
    """Returns (skip, reason). skip is True when the agent must not see this message."""
    earlier = [t for t in all_tickets
               if t["message_id"] == ticket["message_id"] and t["received_at"] < ticket["received_at"]]
    if ticket.get("message_id") and earlier:
        return True, f"Duplicate: the same message already came in as {earlier[0]['ticket_id']}. Skipped."
    flag = (ticket.get("auto_submitted") or "").strip().lower()
    if (flag and flag != "no") or ticket["subject"].strip().lower().startswith(AUTO_SUBJECTS):
        return True, "Automatic reply (out of office or bounce). Skipped, so the agent does not answer a robot."
    return False, "New customer message."


# ---- Your help desk or inbox -------------------------------------------------------------
# Fill these in when you connect your help desk. Rules:
#   - Keys come from .env with helpers.env_value("NAME"). Never write a key in this file.
#   - fetch_new_messages only reads. It returns rows with the INBOX_COLUMNS above.
#   - save_draft never sends. It puts the reply in the help desk as a draft or an internal note
#     for a person. Sending on its own comes later, one ticket type at a time (send-rules.yaml).
#   - Test on one or two messages first, and read what came back.

def fetch_new_messages(limit=5):
    """Read up to `limit` new customer messages from the help desk. Returns a list of dicts."""
    raise NotConnected("The help desk is not connected yet. Ask your coding agent to connect it.")


def save_draft(ticket, reply_text, note_for_team=""):
    """Put a reply into the help desk as a draft or internal note. Never sends it to the customer."""
    raise NotConnected("The help desk is not connected yet, so the reply stays in outbox/replies.csv.")
