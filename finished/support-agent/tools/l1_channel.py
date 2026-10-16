"""L1 Channel: what comes in, before the agent sees anything.

Plain code. Every reply that goes out carries a line saying an AI agent wrote it.
A message that arrives twice (same message id) is skipped. An automatic reply
(out of office, bounce) is skipped, so the agent never answers a robot and starts a loop.
"""
HOLDING_LABEL = "This is an automatic message."


def ai_label(settings):
    return f"This reply was written by {settings.get('business_name', 'our')}'s AI support agent."
AUTO_SUBJECTS = ("automatic reply", "auto:", "out of office", "undeliverable", "delivery status notification")


def check_incoming(ticket, all_tickets):
    """Returns (skip, reason). skip is True when the agent must not see this message."""
    earlier = [t for t in all_tickets
               if t["message_id"] == ticket["message_id"] and t["received_at"] < ticket["received_at"]]
    if ticket.get("message_id") and earlier:
        return True, f"Duplicate: the same message already came in as {earlier[0]['ticket_id']}. Skipped."
    flag = (ticket.get("auto_submitted") or "").strip().lower()
    if (flag and flag != "no") or ticket["subject"].strip().lower().startswith(AUTO_SUBJECTS):
        return True, "Automatic reply (out of office). Skipped, so the agent does not answer a robot."
    return False, "New customer message."
