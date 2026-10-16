"""Try your connections. Read only: nothing is sent and no model is called.

  python app/connections.py pull --limit 3        read up to 3 new messages from your help desk into inbox/live.csv
  python app/connections.py lookup name@your.com  look up one customer in your real customer data

Both need the code in tools/l1_channel.py (fetch_new_messages) and tools/l4_customer_data.py
(fetch_customer), and the keys in .env. Real messages stay on this computer, in inbox/live.csv.
They never go into the tests: the tests use made-up tickets only.
"""
import argparse
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from agent import FOLDER, load_folder  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pull")
    p.add_argument("--limit", type=int, default=3)
    q = sub.add_parser("lookup")
    q.add_argument("email")
    a = ap.parse_args()
    kit = load_folder(FOLDER)
    helpers = kit["helpers"]
    if a.cmd == "pull":
        rows = kit["channel"].fetch_new_messages(limit=a.limit)
        path = FOLDER / "inbox" / "live.csv"
        known = {r["ticket_id"] for r in helpers.read_rows(path)}
        new = [r for r in rows if r["ticket_id"] not in known]
        for r in new:
            helpers.add_row(path, {c: r.get(c, "") for c in kit["channel"].INBOX_COLUMNS})
        print(f"Read {len(rows)} messages, {len(new)} new, saved in inbox/live.csv:")
        for r in new:
            print(f"  {r['ticket_id']}  {helpers.mask_email(r.get('from_email', ''))}  {r.get('subject', '')[:60]}")
    else:
        import l4_customer_data
        row = l4_customer_data.fetch_customer(a.email.strip().lower())
        if not row:
            print("No customer with that email.")
            return
        print("Found a customer. Fields the agent gets:")
        hidden = {"internal_note"} | set(helpers.read_settings(FOLDER / "settings.yaml").get("never_show_fields") or [])
        for k, v in row.items():
            print(f"  {k}: {'(hidden from the agent)' if k in hidden else v}")


if __name__ == "__main__":
    main()
