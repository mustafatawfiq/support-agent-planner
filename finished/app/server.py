"""The demo page server (L1 Channel for the room). Standard library only.

  python app/server.py                   default run mode from settings.yaml (recorded or live)
  python app/server.py --mode live
  python app/server.py --record          live runs are also saved as recordings
Every run is either a RECORDED RUN (saved model answers, the code runs for real) or LIVE.
The screen always says which.
"""
import argparse
import json
import sys
import threading
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from agent import FOLDER, LAYERS, load_folder, run_ticket  # noqa: E402
from llm import DEMO_ROOT, LLM, spend_so_far  # noqa: E402

UI = APP / "ui"
VIDEOS = DEMO_ROOT / "replay" / "videos"
RUNS, RUN_LOCK = {}, threading.Lock()
STATE = {"replay": None, "live": None, "live_error": "", "model": "haiku", "record": False}

# Which layer each part of the folder belongs to (shown in the folder view).
FOLDER_LAYERS = [
    ("inbox/", "L1"), ("outbox/", "L1"), ("tools/l1_channel.py", "L1"),
    ("instructions.md", "L2"), ("settings.yaml", "L2"), ("tools/l2_reply.py", "L2"), ("tools/helpers.py", "L2"),
    ("knowledge/", "L3"), ("policies/", "L3"), ("tools/l3_knowledge.py", "L3"),
    ("data/", "L4"), ("tools/l4_customer_data.py", "L4"),
    ("skills/", "L5"), ("tools/l5_actions_and_rules.py", "L5"),
    ("send-rules.yaml", "L6"), ("queue/", "L6"), ("tools/l6_hand_off.py", "L6"),
    ("log/", "L7"), ("tests/", "L7"), ("tools/l7_log.py", "L7"),
]
TREE_ORDER = ["instructions.md", "settings.yaml", "inbox", "knowledge", "policies", "data", "skills", "tools",
              "send-rules.yaml", "outbox", "queue", "log", "tests"]


def settings():
    return load_folder(FOLDER)["helpers"].read_settings(FOLDER / "settings.yaml")


def layer_of(rel):
    for prefix, layer in FOLDER_LAYERS:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return layer
    return "L2"


def folder_tree():
    items = []
    for path in FOLDER.rglob("*"):
        rel = path.relative_to(FOLDER).as_posix()
        if any(part.startswith((".", "__")) for part in rel.split("/")):
            continue
        items.append({"path": rel, "dir": path.is_dir(), "depth": rel.count("/"), "layer": layer_of(rel)})
    rank = {name: i for i, name in enumerate(TREE_ORDER)}
    return sorted(items, key=lambda i: (rank.get(i["path"].split("/")[0], 99), i["path"]))


def live_llm():
    if STATE["live"] is None:
        try:
            s = settings()
            STATE["live"] = LLM("record" if STATE["record"] else "live",
                                timeout=int(s.get("timeout_seconds", 30)), retries=int(s.get("retries", 1)))
        except Exception as exc:
            STATE["live_error"] = str(exc)
            raise
    return STATE["live"]


def state():
    kit = load_folder(FOLDER)
    helpers = kit["helpers"]
    s = settings()
    tickets = sorted(helpers.read_rows(FOLDER / "inbox" / "tickets.csv"), key=lambda r: r["received_at"])
    status = {}
    for row in helpers.read_rows(FOLDER / "outbox" / "replies.csv"):
        if row["type"] != "holding":
            status[row["ticket_id"]] = {"sent": "sent", "draft, waiting for a person": "draft"}.get(row["status"], "person")
    for t in tickets:
        t["status"] = status.get(t["ticket_id"], "new")
    log_path = FOLDER / "log" / "steps.jsonl"
    log = [json.loads(l) for l in log_path.read_text().splitlines()[-80:]] if log_path.exists() else []
    tests_path = FOLDER / "tests" / "results-latest.json"
    rec_dir = STATE["replay"].replay_dir
    return {
        "tickets": tickets,
        "layers": [{"id": i, "name": n, "group": g, "line": d} for i, n, g, d in LAYERS],
        "business_name": s.get("business_name", "Our"),
        "screen_note": s.get("screen_note", ""),
        "layers_on": int(s.get("layers_on", 7)),
        "run_mode": s.get("run_mode", "recorded"),
        "step_reveal": s.get("step_reveal", "manual"),
        "model": STATE["model"],
        "model_ids": {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"},
        "effort": s.get("effort", ""),
        "recordings": sorted(p.stem for p in rec_dir.glob("*.json")) if rec_dir.exists() else [],
        "live_error": STATE["live_error"],
        "videos": sorted(p.name for p in VIDEOS.glob("*.*")) if VIDEOS.exists() else [],
        "tree": folder_tree(),
        "queue": helpers.read_rows(FOLDER / "queue" / "people-queue.csv"),
        "refunds": helpers.read_rows(FOLDER / "queue" / "refund-requests.csv"),
        "send_rules": helpers.read_settings(FOLDER / "send-rules.yaml"),
        "log": log,
        "tests": json.loads(tests_path.read_text()) if tests_path.exists() else None,
        "spend": spend_so_far(),
    }


def start_run(ticket_id, layers, model, mode):
    run_id = uuid.uuid4().hex[:8]
    record = {"run_id": run_id, "events": [], "done": False, "error": None, "ticket_id": ticket_id, "layers": layers,
              "mode": "LIVE" if mode == "live" else "RECORDED RUN", "model": model}
    RUNS[run_id] = record

    def work():
        with RUN_LOCK:
            try:
                llm = live_llm() if mode == "live" else STATE["replay"]
                run_ticket(ticket_id, layers, llm, model_key=model, folder=FOLDER, on_event=record["events"].append)
            except Exception as exc:  # shown on the page, never hidden
                record["error"] = str(exc)
                traceback.print_exc()
            finally:
                record["done"] = True

    threading.Thread(target=work, daemon=True).start()
    return run_id


def set_send_rule(kind, mode):
    path = FOLDER / "send-rules.yaml"
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("#") and line.split(":")[0].strip() == kind:
            lines[i] = f"{kind}: {mode}"
    path.write_text("\n".join(lines) + "\n")


def reset():
    for sub, pattern in (("outbox", "*.csv"), ("queue", "*.csv"), ("log", "*.jsonl")):
        for p in (FOLDER / sub).glob(pattern):
            p.unlink()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body, kind="application/json", code=200):
        data = body if isinstance(body, bytes) else (json.dumps(body) if kind == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind + ("; charset=utf-8" if not kind.startswith("video") else ""))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path, kind):
        if not path.is_file():
            return self._send({"error": "not found"}, code=404)
        return self._send(path.read_bytes(), kind)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._file(UI / "index.html", "text/html")
        if url.path in ("/app.js", "/style.css"):
            return self._file(UI / url.path[1:], "text/javascript" if url.path.endswith("js") else "text/css")
        if url.path == "/tests/test-grid.html":
            return self._file(FOLDER / "tests" / "test-grid.html", "text/html")
        if url.path.startswith("/video/"):
            name = Path(url.path).name
            return self._file(VIDEOS / name, "video/mp4" if name.endswith("mp4") else "video/webm")
        if url.path == "/api/state":
            return self._send(state())
        if url.path == "/api/file":
            rel = parse_qs(url.query).get("path", [""])[0]
            target = (FOLDER / rel).resolve()
            if not str(target).startswith(str(FOLDER.resolve())) or not target.is_file():
                return self._send({"error": "not found"}, code=404)
            return self._send({"path": rel, "text": target.read_text(errors="replace")})
        if url.path.startswith("/api/run/"):
            run = RUNS.get(url.path.rsplit("/", 1)[1])
            return self._send(run or {"error": "unknown run"}, code=200 if run else 404)
        return self._send({"error": "not found"}, code=404)

    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(size) or b"{}")
        if self.path == "/api/run":
            if RUN_LOCK.locked():
                return self._send({"error": "A ticket is still running."}, code=409)
            mode = "live" if body.get("mode") == "live" else "recorded"
            return self._send({"run_id": start_run(body["ticket_id"], int(body["layers"]),
                                                   body.get("model") or STATE["model"], mode)})
        if self.path == "/api/model":
            STATE["model"] = body["model"] if body.get("model") in ("haiku", "sonnet") else "haiku"
            return self._send({"model": STATE["model"]})
        if self.path == "/api/send-rule":
            if body.get("mode") in ("send", "draft") and body.get("type"):
                set_send_rule(body["type"], body["mode"])
            return self._send({"ok": True})
        if self.path == "/api/reset":
            reset()
            return self._send({"ok": True})
        return self._send({"error": "not found"}, code=404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="live runs are also saved as recordings")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--speed", type=float, default=0.6, help="recorded runs: wait this share of the real model time")
    a = ap.parse_args()
    s = settings()
    STATE["record"] = a.record
    STATE["replay"] = LLM("replay", speed=a.speed)
    STATE["model"] = s.get("model", "haiku")
    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Support agent demo: {url}   default run: {s.get('run_mode', 'recorded')}   Stop with Ctrl+C.")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
