"""Record the model's answers for every ticket, so the room can run without the network.

  python app/record.py                      all tickets, layers L2 to L7, Haiku
  python app/record.py --tickets T-104 --layers 5,7 --model sonnet
  python app/record.py --check              replay every recording and confirm it still matches the files

A recording only plays back for the exact same request. If instructions, skills, tools, data or
layers change, record again. The tools are never recorded: they always run for real.
"""
import argparse
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import FOLDER, load_folder, run_ticket  # noqa: E402
from llm import LLM, spend_so_far  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickets", default="")
    ap.add_argument("--layers", default="2,3,4,5,6,7")
    ap.add_argument("--model", default="haiku", choices=["haiku", "sonnet"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    kit = load_folder(FOLDER)
    helpers = kit["helpers"]
    settings = helpers.read_settings(FOLDER / "settings.yaml")
    tickets = [r for r in helpers.read_rows(FOLDER / "inbox" / "tickets.csv")
               if not kit["channel"].check_incoming(r, helpers.read_rows(FOLDER / "inbox" / "tickets.csv"))[0]]
    if a.tickets:
        tickets = [t for t in tickets if t["ticket_id"] in a.tickets.split(",")]
    layers = [int(x) for x in a.layers.split(",")]
    mode = "replay" if a.check else "record"
    llm = LLM(mode, speed=0, timeout=int(settings.get("timeout_seconds", 30)) * 2, retries=1)
    before = spend_so_far()["total_usd"]

    def job(item):
        ticket, n = item
        with tempfile.TemporaryDirectory() as out:
            try:
                t = run_ticket(ticket["ticket_id"], n, llm, model_key=a.model, folder=FOLDER, out=out)
                return f"{ticket['ticket_id']} L{n}: {t.mode}, {len(t.tools_called)} tool calls"
            except Exception as exc:
                return f"{ticket['ticket_id']} L{n}: FAILED {exc}"

    with ThreadPoolExecutor(a.workers) as pool:
        lines = list(pool.map(job, [(t, n) for t in tickets for n in layers]))
    print("\n".join(lines))
    failed = [l for l in lines if "FAILED" in l]
    print(f"\n{len(lines) - len(failed)} of {len(lines)} ok. Spend: {spend_so_far()['total_usd'] - before:.4f} USD")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
