"""Check the agent folder before you test it. Free: no model calls.

  python app/check.py

Finds blanks (____) left in files, template files still in place, skills that name tools that do not
exist, test rows that can never pass, and test rows that disagree with your own rules and send rules.
Problems must be fixed before a test run. Warnings are worth a look.
"""
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from agent import FOLDER, load_folder  # noqa: E402
from llm import MODELS  # noqa: E402

MADE_UP = re.compile(r"@([a-z0-9-]+\.)*example\.(com|org|net)$", re.I)  # test people only, never real addresses
TEMPLATE_FILES = ["knowledge/example-topic.md", "skills/your-ticket-type.md"]
TEST_COLUMNS = ["ticket_id", "scenario", "expect_type", "must_call", "must_not_call", "refund_decision",
                "hand_off_to_person", "delivery", "reply_must_match", "reply_must_not_match"]

problems, warnings = [], []


def problem(where, what):
    problems.append(f"{where}: {what}")


def warn(where, what):
    warnings.append(f"{where}: {what}")


def split(cell):
    return [x.strip() for x in (cell or "").split(";") if x.strip()]


def main():
    kit = load_folder(FOLDER)
    h, channel, tools = kit["helpers"], kit["channel"], kit["tools"]
    f = FOLDER
    settings = h.read_settings(f / "settings.yaml")
    rules = h.read_settings(f / "send-rules.yaml")
    types = h.ticket_types(f)

    # Blanks and template files
    files = ([f / "instructions.md", f / "settings.yaml", f / "send-rules.yaml", f / "data" / "customers.csv",
              f / "inbox" / "tickets.csv", f / "tests" / "expected.csv"]
             + sorted(f.glob("knowledge/*.md")) + sorted(f.glob("policies/*.md")) + sorted(f.glob("skills/*.md")))
    for path in files:
        rel = path.relative_to(f).as_posix()
        if rel in TEMPLATE_FILES:
            problem(rel, "template file still here. Use it as the pattern for your own files, then delete it.")
            continue
        if not path.exists():
            problem(rel, "missing.")
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if "____" in line:
                problem(f"{rel} line {n}", "a blank (____) is not filled: " + line.strip()[:90])

    # Settings
    if settings.get("model", "") not in MODELS:
        problem("settings.yaml", f"model '{settings.get('model', '')}' is not in app/llm.py ({', '.join(MODELS)}).")
    sign = settings.get("sign_off", "")
    if sign and "____" not in sign and sign.strip('"') not in (f / "instructions.md").read_text():
        warn("settings.yaml", f"sign_off '{sign}' is not the sign-off in instructions.md. Use the same one.")
    if not settings.get("test_date"):
        warn("settings.yaml", "test_date is empty, so date rules give a different answer each day. "
                              "Set it to a fixed date for the tests.")
    l5_actions = {n for n, t in tools.items() if t["layer"] == "L5" and n != "read_skill"}
    actions_on = settings.get("actions_on") or []
    for name in actions_on:
        if name not in l5_actions:
            problem("settings.yaml", f"actions_on lists '{name}', but tools/l5_actions_and_rules.py has no such action.")
    offered = {n for n in tools if n not in l5_actions or n in actions_on}

    # Send rules and ticket types
    if not types:
        problem("send-rules.yaml", "no ticket types (each type is a line like 'refund: draft').")
    if "other" not in types:
        warn("send-rules.yaml", "no 'other' type. Add 'other: draft' for anything that fits no type.")
    for kind in types:
        if rules[kind] == "send":
            warn("send-rules.yaml", f"'{kind}' is set to send. Do this only after every test run of that type passed.")
    domains = rules.get("allowed_link_domains") or []
    if not domains or any("your-domain" in d for d in domains):
        problem("send-rules.yaml", "allowed_link_domains still has the example. Put your own website.")
    table_types = set(re.findall(r"^\|\s*([a-z0-9][a-z0-9_-]*)\s*\|", (f / "instructions.md").read_text(), re.M)) - {"type"}
    for kind in types:
        if kind not in table_types:
            problem("instructions.md", f"the ticket type table has no row for '{kind}' (it is in send-rules.yaml).")
    for kind in table_types:
        if kind not in types:
            problem("send-rules.yaml", f"no line for '{kind}' (it is in the ticket type table in instructions.md).")

    # Skills
    for path in sorted(f.glob("skills/*.md")):
        rel = path.relative_to(f).as_posix()
        if rel in TEMPLATE_FILES:
            continue
        text = path.read_text()
        parts = text.split("---")
        head = {}
        if text.startswith("---") and len(parts) >= 3:
            head = {l.split(":", 1)[0].strip(): l.split(":", 1)[1].strip() for l in parts[1].splitlines() if ":" in l}
        for key in ("name", "description", "use_when", "do_not_use_when"):
            if not head.get(key):
                problem(rel, f"the top block has no '{key}:' line.")
        if head.get("name") and head["name"] != path.stem:
            problem(rel, f"name '{head['name']}' must match the file name '{path.stem}'.")
        if path.stem not in types:
            warn(rel, f"'{path.stem}' is not a ticket type in send-rules.yaml, so the agent opens it only by its name.")
        for name in sorted(set(re.findall(r"`([a-z][a-z0-9_]+)`", text))):
            if name in tools and name not in offered:
                problem(rel, f"uses `{name}`, but it is not under actions_on in settings.yaml.")
            elif name not in tools and "_" in name and name not in types:
                problem(rel, f"uses `{name}`, but no tool has that name.")

    # Knowledge
    knowledge = [p for p in sorted(f.glob("knowledge/*.md")) if p.relative_to(f).as_posix() not in TEMPLATE_FILES]
    if not knowledge:
        warn("knowledge/", "no help files yet. Without them the agent hands every question to a person.")
    for path in knowledge:
        lines = path.read_text().splitlines()
        rel = path.relative_to(f).as_posix()
        if not lines or not lines[0].startswith("# "):
            problem(rel, "the first line must be '# ' and the question.")
        top = " ".join(lines[:4])
        for key in ("Last checked:", "Owner:", "Link:"):
            if key not in top:
                problem(rel, f"no '{key}' in the line under the question.")

    # Customer data
    customers = h.read_rows(f / "data" / "customers.csv")
    cols = set(customers[0]) if customers else set()
    for col in ("customer_id", "name", "email", "status"):
        if customers and col not in cols:
            problem("data/customers.csv", f"no '{col}' column.")
    emails = [c.get("email", "").lower() for c in customers]
    if len(emails) != len(set(emails)):
        problem("data/customers.csv", "two customers have the same email.")
    for c in customers:
        if c.get("email") and not MADE_UP.search(c["email"]):
            warn("data/customers.csv", f"{c['email']} is not a made-up address. Rewrite it as name@example.com.")
    if "check_refund_eligibility" in actions_on:
        for col in ("last_purchase_date", "last_purchase_amount", "refunds_last_12_months"):
            if col not in cols:
                problem("data/customers.csv", f"the refund rule is on, but there is no '{col}' column.")
        values = h.table_values(f / "policies" / "refund-policy.md") if (f / "policies" / "refund-policy.md").exists() else {}
        if h.first_number(values.get("Refund window, days after the purchase")) is None:
            warn("policies/refund-policy.md", "the refund window has no number, so every refund goes to a person.")
    if "send_access_link" in actions_on and "access" not in cols:
        problem("data/customers.csv", "send_access_link is on, but there is no 'access' column.")

    # Inbox and tests
    tickets = h.read_rows(f / "inbox" / "tickets.csv")
    by_id = {t["ticket_id"]: t for t in tickets}
    if tickets and set(channel.INBOX_COLUMNS) - set(tickets[0]):
        problem("inbox/tickets.csv", "missing columns: " + ", ".join(sorted(set(channel.INBOX_COLUMNS) - set(tickets[0]))))
    if len(by_id) != len(tickets):
        problem("inbox/tickets.csv", "two tickets have the same ticket_id.")
    if len(tickets) < 20:
        warn("inbox/tickets.csv", f"{len(tickets)} tickets. Aim for 20 past tickets.")
    for t in tickets:
        if t.get("from_email") and not MADE_UP.search(t["from_email"]):
            warn("inbox/tickets.csv", f"{t['ticket_id']} comes from {t['from_email']}, which is not a made-up address. "
                                     "Rewrite the sender as a new name and name@example.com.")
    cases = h.read_rows(f / "tests" / "expected.csv")
    if cases and set(TEST_COLUMNS) - set(cases[0]):
        problem("tests/expected.csv", "missing columns: " + ", ".join(sorted(set(TEST_COLUMNS) - set(cases[0]))))
        cases = []
    tested = {c["ticket_id"] for c in cases}
    for t in tickets:
        if t["ticket_id"] not in tested:
            warn("tests/expected.csv", f"no test row for {t['ticket_id']}.")
    by_email = {c.get("email", "").lower(): c for c in customers}
    for c in cases:
        where = f"tests/expected.csv {c['ticket_id']}"
        t = by_id.get(c["ticket_id"])
        if not t:
            problem(where, "no ticket with this id in inbox/tickets.csv.")
            continue
        if c["expect_type"] not in types + ["other", "any", "skipped", ""]:
            problem(where, f"type '{c['expect_type']}' is not in send-rules.yaml.")
        for name in split(c["must_call"]) + split(c["must_not_call"]):
            if name not in tools:
                problem(where, f"'{name}' is not a tool.")
            elif name in split(c["must_call"]) and name not in offered:
                problem(where, f"must call '{name}', but it is not under actions_on in settings.yaml.")
        if c["refund_decision"] not in ("eligible", "not_eligible", "none", "any", ""):
            problem(where, "refund_decision must be eligible, not_eligible, none or any.")
        hand = c.get("hand_off_to_person", "")
        if hand not in ("yes", "no", "any", ""):
            problem(where, "hand_off_to_person must be yes, no or any.")
        delivery = split(c["delivery"])
        if not delivery or set(delivery) - {"send", "draft", "person", "skipped"}:
            problem(where, "delivery must be send, draft, person or skipped (several: draft;person).")
        for col in ("reply_must_match", "reply_must_not_match"):
            try:
                re.compile(c.get(col, ""))
            except re.error as exc:
                problem(where, f"{col} is not a valid pattern: {exc}")

        # Does the row agree with the code?
        skip, _ = channel.check_incoming(t, tickets)
        if skip and delivery != ["skipped"]:
            problem(where, "L1 skips this message (duplicate or automatic reply), so delivery must be skipped.")
        if not skip and "skipped" in delivery:
            problem(where, "delivery says skipped, but L1 does not skip this message.")
        if skip:
            continue
        sender = by_email.get(t["from_email"].lower())
        verified = sender is not None and sender.get("status", "").lower() not in ("closed", "deleted", "banned")
        gated = [n for n in split(c["must_call"]) if tools.get(n, {}).get("needs_verified")]
        if gated and not verified:
            problem(where, f"must call {', '.join(gated)}, but the sender is not a verified customer, "
                           "so that tool is never offered.")
        if hand == "yes" and "person" not in delivery:
            problem(where, "a ticket handed to a person always ends as person.")
        if not verified and "verify_identity" in split(c["must_call"]) and "person" not in delivery:
            problem(where, "the sender will not verify, so the code sends it to a person. Add person to delivery.")
        kind = c["expect_type"]
        if kind in types and hand != "yes" and verified and "person" not in delivery:
            rule = rules[kind]
            if rule == "draft" and "send" in delivery and "draft" not in delivery:
                problem(where, f"expects send, but '{kind}' is set to draft in send-rules.yaml.")
            if rule == "send" and delivery == ["draft"]:
                warn(where, f"expects draft, but '{kind}' is set to send. A reply that passes the checks is sent.")
        if c["refund_decision"] in ("eligible", "not_eligible") and sender:
            expected = refund_rule(h, f, settings, sender)
            if expected and expected != c["refund_decision"]:
                problem(where, f"expects {c['refund_decision']}, but the refund policy and this customer's data say "
                               f"{expected} on test_date {settings.get('test_date') or 'today'}.")

    # Keys
    for path in list((FOLDER.parent / "app").glob("*.py")) + list((f / "tools").glob("*.py")):
        if re.search(r"sk-(ant|or)-[A-Za-z0-9_-]{10,}", path.read_text()):
            problem(path.name, "looks like it has an API key written in it. Keys go in .env only.")
    if (FOLDER.parent / ".env").exists():
        ignore = FOLDER.parent / ".gitignore"
        if not ignore.exists() or ".env" not in ignore.read_text().split():
            problem(".gitignore", "add .env, so your key is never shared.")

    print(f"Checked {len(tickets)} tickets, {len(cases)} test rows, {len(knowledge)} help files, "
          f"{len([p for p in f.glob('skills/*.md') if p.relative_to(f).as_posix() not in TEMPLATE_FILES])} skills.")
    for title, items in (("Problems (fix these before a test run)", problems), ("Warnings", warnings)):
        print(f"\n{title}: {len(items)}")
        for line in items:
            print("  - " + line)
    sys.exit(1 if problems else 0)


def refund_rule(h, f, settings, row):
    """The refund rule written a second time, on purpose, to check the test rows."""
    values = h.table_values(f / "policies" / "refund-policy.md")
    window = h.first_number(values.get("Refund window, days after the purchase"))
    limit_text = values.get("Refunds per customer in 12 months", "")
    limit = h.first_number(limit_text)
    if limit is None and "no limit" in limit_text.lower():
        limit = 10 ** 6
    if window is None or limit is None or not row.get("last_purchase_date"):
        return None
    plans_text = values.get("Plans or products that can be refunded", "all").strip()
    plans = [] if plans_text.lower() in ("", "all") else [x.strip().lower() for x in plans_text.split(",") if x.strip()]
    if plans and (row.get("plan") or row.get("product") or "").strip().lower() not in plans:
        return "not_eligible"
    days = (h.today_from(settings) - h.to_date(row["last_purchase_date"])).days
    used = int(h.first_number(row.get("refunds_last_12_months")) or 0)
    return "eligible" if days <= window and used < limit else "not_eligible"


if __name__ == "__main__":
    main()
