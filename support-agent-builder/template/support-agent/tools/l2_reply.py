"""L2 Agent: sort the ticket first, write the reply last.

The agent picks the type and writes the reply. It does not decide if the reply is sent.
The send rules decide that, in code (see l6_hand_off.py and send-rules.yaml).
The ticket types are the ones listed in send-rules.yaml.
"""
from pathlib import Path

from helpers import ticket_types

TICKET_TYPES = ticket_types(Path(__file__).resolve().parents[1]) or ["other"]
if "other" not in TICKET_TYPES:
    TICKET_TYPES.append("other")


def sort_ticket(ctx, ticket_type, reason):
    ctx.ticket_type = ticket_type if ticket_type in TICKET_TYPES else "other"
    return {"result": {"type": ctx.ticket_type}, "show": f"Type: {ctx.ticket_type}. {reason}"}


def write_reply(ctx, ticket_type, decision, reply, sources, note_for_team=""):
    ctx.reply = {
        "ticket_type": ticket_type if ticket_type in TICKET_TYPES else "other",
        "decision": decision if decision in ("answered", "needs_person") else "needs_person",
        "text": reply.strip(),
        "sources": [s for s in sources if s],
        "note_for_team": note_for_team.strip(),
    }
    said = "Answered" if ctx.reply["decision"] == "answered" else "A person must take it"
    count = len(ctx.reply["sources"])
    return {
        "result": {"saved": True, "next": "The ticket is finished. Stop here. Code now decides if this reply is "
                                          "sent, kept as a draft, or goes to a person."},
        "show": f"{said}. " + (f"{count} source{'s' if count != 1 else ''} named." if count else "No source named."),
    }


TOOLS = [
    {
        "name": "sort_ticket",
        "layer": "L2",
        "label": "Sorted the ticket",
        "description": "Your first step on every ticket: record the ticket type and one short reason.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_type": {"type": "string", "enum": TICKET_TYPES},
                "reason": {"type": "string", "description": "A few words: why this type."},
            },
            "required": ["ticket_type", "reason"],
            "additionalProperties": False,
        },
        "run": sort_ticket,
    },
    {
        "name": "write_reply",
        "layer": "L2",
        "label": "Wrote the reply",
        "description": (
            "Your last step on every ticket, called exactly once. Give the ticket type, your decision "
            "(answered, or needs_person when a person must take it), the reply to the customer, the sources "
            "you used, and a short note for the team. You do not decide if the reply is sent; code does."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_type": {"type": "string", "enum": TICKET_TYPES},
                "decision": {"type": "string", "enum": ["answered", "needs_person"]},
                "reply": {"type": "string", "description": "The message to the customer."},
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Help files, policies or links you used. Empty if none.",
                },
                "note_for_team": {"type": "string", "description": "One or two lines for the team. Never sent to the customer."},
            },
            "required": ["ticket_type", "decision", "reply", "sources", "note_for_team"],
            "additionalProperties": False,
        },
        "run": write_reply,
    },
]
