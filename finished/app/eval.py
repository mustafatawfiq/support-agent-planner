"""L7 tests: run every sample ticket several times and check the outcome.

  python app/eval.py                       Haiku, 5 runs per ticket, all layers on
  python app/eval.py --model sonnet --runs 1
  python app/eval.py --tickets T-103,T-104

Checks per run: ticket type, tools that must and must not be called, the refund decision (also
recomputed here from the data, separately from the tool), hand-off, what happened to the reply
(sent, draft, person or skipped), words the reply must or must not contain, and no internal facts.
Each run writes to its own temporary folder, so runs never touch each other or the demo.
"""
import argparse
import html
import json
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import FOLDER, load_folder, run_ticket  # noqa: E402
from llm import DEMO_ROOT, LLM, spend_so_far  # noqa: E402

# Words that must never show up in a reply (lowercase words match any case).
NEVER_ANYWHERE = ["INTERNAL", "internal note", "customer id", "C-10"]


def split(cell):
    return [x.strip() for x in (cell or "").split(";") if x.strip()]


def reference_refund(folder, helpers, ticket):
    """The refund rule written a second time, on purpose, to check the tool."""
    customers = {r["email"].lower(): r for r in helpers.read_rows(folder / "data" / "customers.csv")}
    row = customers.get(ticket["from_email"].lower())
    if not row:
        return None
    text = (folder / "policies" / "refund-policy.md").read_text()
    window = int(re.search(r"Refund window, days after the charge \| (\d+)", text).group(1))
    limit = int(re.search(r"Refunds per member in 12 months \| (\d+)", text).group(1))
    days = (helpers.today_from(helpers.read_settings(folder / "settings.yaml")) - helpers.to_date(row["last_charge_date"])).days
    return "eligible" if days <= window and int(row["refunds_last_12_months"]) < limit else "not_eligible"


def check(case, t, folder, helpers):
    fails = []
    called = t.tools_called
    text = (t.reply or {}).get("text", "")
    kind = t.mode if t.mode == "skipped" else kit_hand_off.effective_type(t)
    if case["expect_type"] not in ("any", "") and kind != case["expect_type"]:
        fails.append(f"type {kind}, expected {case['expect_type']}")
    for name in split(case["must_call"]):
        if name not in called:
            fails.append(f"did not call {name}")
    for name in split(case["must_not_call"]):
        if name in called:
            fails.append(f"called {name}")
    decision = "none" if not t.refund_decision else ("eligible" if t.refund_decision["eligible"] else "not_eligible")
    if case["refund_decision"] not in ("any", "") and decision != case["refund_decision"]:
        fails.append(f"refund decision {decision}, expected {case['refund_decision']}")
    if t.refund_decision:
        ref = reference_refund(folder, helpers, t.ticket)
        if ref and ref != decision:
            fails.append(f"refund tool said {decision} but the rule says {ref}")
    handed = "hand_off_to_person" in called
    if case["hand_off_to_person"] == "yes" and not handed:
        fails.append("no hand-off")
    if case["hand_off_to_person"] == "no" and handed:
        fails.append("handed off")
    if t.mode not in split(case["delivery"]):
        fails.append(f"reply {t.mode}, expected {case['delivery']}")
    if t.mode != "skipped":
        if called.count("write_reply") != 1:
            fails.append(f"write_reply called {called.count('write_reply')} times")
        if case["reply_must_match"] and not re.search(case["reply_must_match"], text):
            fails.append(f"reply lacks /{case['reply_must_match']}/")
        if case["reply_must_not_match"] and re.search(case["reply_must_not_match"], text):
            fails.append(f"reply has /{case['reply_must_not_match']}/")
        low = text.lower()
        bad = [w for w in NEVER_ANYWHERE if (w.lower() in low if w.islower() else w in text)]
        if bad:
            fails.append("internal words: " + ", ".join(bad))
        note = (t.customer or {}).get("internal_note", "").lower()
        words = re.findall(r"[a-z0-9]+", note)
        plain = " ".join(re.findall(r"[a-z0-9]+", low))
        leaks = [" ".join(words[i:i + 4]) for i in range(len(words) - 3) if " ".join(words[i:i + 4]) in plain]
        if leaks:
            fails.append("internal note leaked: " + leaks[0])
    return fails


def one_run(case, i, llm, model):
    with tempfile.TemporaryDirectory() as out:
        started = time.time()
        try:
            t = run_ticket(case["ticket_id"], 7, llm, model_key=model, folder=FOLDER, out=out)
        except Exception as exc:
            return {"ticket_id": case["ticket_id"], "run": i, "ok": False, "fails": [f"error: {exc}"], "cost": 0,
                    "seconds": round(time.time() - started, 1), "tools": [], "reply": "", "mode": "error"}
        fails = check(case, t, FOLDER, kit_helpers)
        return {"ticket_id": case["ticket_id"], "run": i, "ok": not fails, "fails": fails, "cost": round(t.cost, 5),
                "seconds": round(time.time() - started, 1), "tools": t.tools_called, "mode": t.mode,
                "sorted_first": bool(t.tools_called) and t.tools_called[0] == "sort_ticket",
                "skill_read": bool(t.skills_read),
                "tokens_in": t.tokens_in, "tokens_out": t.tokens_out, "calls": t.calls,
                "review_line_added_by_code": "you can ask a person to review it: " in (t.reply or {}).get("text", ""),
                "reply": (t.reply or {}).get("text", "")}


def grid_page(summary):
    rows = "".join(
        f"<tr><td>{html.escape(s['scenario'])}</td><td>{s['ticket_id']}</td>"
        f"<td>{''.join('<span class=ok>&#9632;</span>' if r else '<span class=no>&#9632;</span>' for r in s['run_results'])}</td>"
        f"<td class={'ok' if s['passed'] == s['runs'] else 'no'}>{s['passed']} of {s['runs']}</td></tr>"
        for s in summary["scenarios"])
    return f"""<!doctype html><meta charset=utf-8><title>Test grid</title>
<style>body{{font:19px/1.35 -apple-system,Segoe UI,sans-serif;margin:28px 40px;color:#1c1c1e;background:#f4f3ef}}
h1{{font-size:30px;margin:0 0 16px}}
table{{border-collapse:collapse;background:#fff;border-radius:12px}}td,th{{padding:6px 18px;border-bottom:1px solid #e2e0da;text-align:left}}
.ok{{color:#0f7d60;font-weight:700}}.no{{color:#b4235a;font-weight:700}}span{{font-size:22px;margin-right:3px}}
.fine{{color:#66666b;font-size:17px;margin-top:14px}}</style>
<h1>Tests: every sample ticket, {summary['runs_per_ticket']} runs each</h1>
<table><tr><th>Scenario</th><th>Ticket</th><th>Runs</th><th>Passed</th></tr>{rows}</table>
<p class=fine>{html.escape(summary['model'])} · all layers on · {html.escape(summary['run_at'])} UTC · made-up data.
A ticket type may send alone only if it passes every run.</p>"""


def main():
    global kit_helpers, kit_hand_off
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku", choices=["haiku", "sonnet"])
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--tickets", default="")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-save", action="store_true", help="do not update tests/results-latest.json")
    ap.add_argument("--grid-only", action="store_true", help="rebuild tests/test-grid.html from the last saved results")
    a = ap.parse_args()
    if a.grid_only:
        summary = json.loads((FOLDER / "tests" / "results-latest.json").read_text())
        (FOLDER / "tests" / "test-grid.html").write_text(grid_page(summary))
        print("Rebuilt tests/test-grid.html")
        return
    kit = load_folder(FOLDER)
    kit_helpers, kit_hand_off = kit["helpers"], kit["hand_off"]
    cases = kit_helpers.read_rows(FOLDER / "tests" / "expected.csv")
    if a.tickets:
        cases = [c for c in cases if c["ticket_id"] in a.tickets.split(",")]
    settings = kit_helpers.read_settings(FOLDER / "settings.yaml")
    llm = LLM("live", timeout=int(settings.get("timeout_seconds", 30)) * 2, retries=1)
    spend_before = spend_so_far()["total_usd"]
    print(f"Testing {len(cases)} tickets x {a.runs} runs with {a.model} ({llm.describe()})")
    jobs = [(c, i) for c in cases for i in range(a.runs)]
    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(lambda job: one_run(job[0], job[1], llm, a.model), jobs))

    scenarios = []
    for c in cases:
        rs = [r for r in results if r["ticket_id"] == c["ticket_id"]]
        fails = {}
        for r in rs:
            for f in r["fails"]:
                fails[f] = fails.get(f, 0) + 1
        scenarios.append({"ticket_id": c["ticket_id"], "scenario": c["scenario"], "type": c["expect_type"],
                          "runs": len(rs), "passed": sum(r["ok"] for r in rs), "run_results": [r["ok"] for r in rs],
                          "fails": fails, "avg_cost": round(sum(r["cost"] for r in rs) / len(rs), 5),
                          "avg_seconds": round(sum(r["seconds"] for r in rs) / len(rs), 1),
                          "sorted_first": sum(r.get("sorted_first", False) for r in rs),
                          "skill_read": sum(r.get("skill_read", False) for r in rs),
                          "review_line_added_by_code": sum(r.get("review_line_added_by_code", False) for r in rs),
                          "avg_tokens_in": round(sum(r.get("tokens_in", 0) for r in rs) / len(rs)),
                          "avg_tokens_out": round(sum(r.get("tokens_out", 0) for r in rs) / len(rs)),
                          "avg_model_calls": round(sum(r.get("calls", 0) for r in rs) / len(rs), 1)})
    types = {}
    for s in scenarios:
        if s["type"] not in ("any", "skipped"):
            types.setdefault(s["type"], {"passed_all": True})
            types[s["type"]]["passed_all"] &= s["passed"] == s["runs"]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    model_id = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}[a.model]
    summary = {"run_at": stamp, "model": model_id, "runs_per_ticket": a.runs, "scenarios": scenarios, "types": types,
               "spend_usd": round(spend_so_far()["total_usd"] - spend_before, 4)}

    print(f"\n{'Ticket':7} {'Scenario':40} Passed   Avg cost  Avg sec  Failures")
    for s in scenarios:
        print(f"{s['ticket_id']:7} {s['scenario'][:40]:40} {s['passed']} of {s['runs']}   {s['avg_cost']:.4f}    {s['avg_seconds']:5.1f}   "
              + "; ".join(f"{k} (x{v})" for k, v in s["fails"].items()))
    print(f"\nSpend for this test run (own estimate): {summary['spend_usd']:.4f} USD")

    evals = DEMO_ROOT / "evals"
    evals.mkdir(exist_ok=True)
    name = f"results-{a.model}-{stamp.replace(' ', '-').replace(':', '')}"
    (evals / f"{name}.json").write_text(json.dumps({**summary, "results": results}, indent=1))
    if not a.no_save:
        (FOLDER / "tests" / "results-latest.json").write_text(json.dumps(summary, indent=1))
        (FOLDER / "tests" / "test-grid.html").write_text(grid_page(summary))
    print(f"Saved evals/{name}.json" + ("" if a.no_save else " and tests/results-latest.json, tests/test-grid.html"))


if __name__ == "__main__":
    main()
