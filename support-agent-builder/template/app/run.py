"""Run one ticket in the terminal.

  python app/run.py T-103                 all layers, live
  python app/run.py T-103 --layers 3      only L1 to L3
  python app/run.py T-103 --mode replay   the recorded run, no network
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import run_ticket  # noqa: E402
from llm import LLM  # noqa: E402


def show(event):
    if event["kind"] == "usage":
        return
    who = event.get("by", "")
    tag = f"[{event.get('layer', '')} {who}]".ljust(14)
    if event["kind"] == "reply":
        print(f"{tag} REPLY ({event['mode']}, type {event['ticket_type']}):\n{event['text']}\n  sources: {event['sources']}\n  note: {event['note']}")
    elif event["kind"] == "delivery":
        print(f"{tag} {event['title']}: {event['show']}")
        for c in event.get("checks", []):
            print(f"{'':14}   {'PASS' if c['ok'] else 'FAIL'} {c['name']}: {c['detail']}")
    else:
        extra = f" {event.get('input')}" if event.get("input") not in (None, "", "{}") else ""
        print(f"{tag} {event.get('title', event['kind'])}{extra} -> {event.get('show', '')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ticket")
    ap.add_argument("--layers", type=int, default=7)
    ap.add_argument("--model", default=None)
    ap.add_argument("--mode", default="live", choices=["live", "record", "replay"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    llm = LLM(a.mode)
    print(f"Model connection: {llm.describe()}")
    t = run_ticket(a.ticket, a.layers, llm, model_key=a.model, out=a.out, on_event=show)
    print(f"Cost: {t.cost:.5f} USD")
