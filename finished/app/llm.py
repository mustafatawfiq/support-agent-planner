"""The model connection: live, record or replay. Also the spend cap.

Live: the Anthropic SDK. Key order: ANTHROPIC_API_KEY (direct to Anthropic), then OPENROUTER_API_KEY
(OpenRouter's Anthropic-compatible endpoint), then KEY_COMMAND (a command that prints a key).
They come from the environment or the .env file next to start.sh. Keys stay in memory only:
they are never printed or written to disk.

Replay: plays back recorded model answers with no network. The tools still run for real, so the
screen shows the same steps as the recorded run.
"""
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import anthropic
from anthropic.types import Message

DEMO_ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "haiku": {"anthropic": "claude-haiku-5-5", "openrouter": "anthropic/claude-haiku-5.5", "price": (0.10, 0.50)},
    "sonnet": {"anthropic": "claude-sonnet-5-5", "openrouter": "anthropic/claude-sonnet-5.5", "price": (2.00, 10.00)},
}
SPEND_FILE = DEMO_ROOT / ".spend.json"
_lock = threading.Lock()


class SpendCapReached(RuntimeError):
    pass


class NoRecording(RuntimeError):
    pass


def _dotenv():
    values = {}
    path = DEMO_ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _key_from_command(command):
    """Optional: a command that prints a key (for example from a password manager). Never printed here."""
    for attempt in range(3):
        out = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=40)
        key = out.stdout.strip()
        if out.returncode == 0 and len(key) >= 20:
            return key
        time.sleep(2 + attempt * 3)
    raise RuntimeError("The key command did not return a key.")


def make_live_client():
    """Returns (client, provider, key_source). key_source names where the key came from, never the key."""
    env = {**_dotenv(), **os.environ}
    if env.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"]), "anthropic", "ANTHROPIC_API_KEY"
    if env.get("OPENROUTER_API_KEY"):
        key, source = env["OPENROUTER_API_KEY"], "OPENROUTER_API_KEY"
    elif env.get("KEY_COMMAND"):
        key, source = _key_from_command(env["KEY_COMMAND"]), "KEY_COMMAND (OpenRouter)"
    else:
        raise RuntimeError("No key for live runs. Put ANTHROPIC_API_KEY=... (or OPENROUTER_API_KEY=...) in the .env "
                           "file next to start.sh. Recorded runs work without a key.")
    client = anthropic.Anthropic(base_url="https://openrouter.ai/api", auth_token=key, api_key=None)
    return client, "openrouter", source


def spend_so_far():
    if SPEND_FILE.exists():
        return json.loads(SPEND_FILE.read_text())
    return {"total_usd": 0.0, "calls": 0}


def _add_spend(cost):
    with _lock:
        data = spend_so_far()
        data["total_usd"] = round(data["total_usd"] + cost, 6)
        data["calls"] += 1
        SPEND_FILE.write_text(json.dumps(data))


def cost_of(model_key, usage):
    price_in, price_out = MODELS[model_key]["price"]
    tokens_in = (usage.input_tokens or 0) + (usage.cache_creation_input_tokens or 0) * 1.25 \
        + (usage.cache_read_input_tokens or 0) * 0.1
    return tokens_in * price_in / 1e6 + (usage.output_tokens or 0) * price_out / 1e6


def _plain(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def request_key(model_key, kwargs):
    """A fingerprint of the full request. Replay only plays an answer recorded for the same request."""
    body = {"model": model_key, **{k: _plain(v) for k, v in kwargs.items() if k not in ("timeout",)}}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


class LLM:
    """mode: live, record (live, and save each answer for replay) or replay (no network)."""

    def __init__(self, mode="live", replay_dir=None, speed=1.0, timeout=30, retries=1, match="strict"):
        self.mode = mode
        self.replay_dir = Path(replay_dir or DEMO_ROOT / "replay" / "recordings")
        self.speed = speed
        self.match = match
        self.cap = float(os.environ.get("SPEND_CAP_USD", "3"))
        self.client = self.provider = self.key_source = None
        if mode in ("live", "record"):
            client, self.provider, self.key_source = make_live_client()
            self.client = client.with_options(timeout=float(timeout), max_retries=int(retries))

    def describe(self):
        if self.mode == "replay":
            return "recorded run: saved model answers, the code runs for real"
        return f"{self.mode} via {self.provider} (key from {self.key_source})"

    def model_id(self, model_key):
        return MODELS[model_key]["anthropic"] if self.provider != "openrouter" else MODELS[model_key]["openrouter"]

    def recording_path(self, run_key, model_key):
        return self.replay_dir / f"{run_key}-{model_key}.json"

    def has_recording(self, run_key, model_key):
        return self.recording_path(run_key, model_key).exists()

    # One run = one ticket at one layer setting.
    def start_run(self, run_key, model_key):
        run = {"key": run_key, "model": model_key, "i": 0, "saved": [], "notes": []}
        if self.mode == "replay":
            path = self.recording_path(run_key, model_key)
            if not path.exists():
                raise NoRecording(f"No recording for {run_key} with {model_key}. Record it first (app/record.py).")
            run["recorded"] = json.loads(path.read_text())
        return run

    def finish_run(self, run, ok):
        if self.mode == "record" and ok:
            self.replay_dir.mkdir(parents=True, exist_ok=True)
            self.recording_path(run["key"], run["model"]).write_text(json.dumps(run["saved"], indent=1))

    def create(self, run, **kwargs):
        """Returns (response, cost, request_id)."""
        model_key = run["model"]
        key = request_key(model_key, kwargs)
        if self.mode == "replay":
            steps = run["recorded"]
            step = next((s for s in steps if s.get("request_key") == key), None)
            if step is None and self.match == "order" and run["i"] < len(steps):
                step = steps[run["i"]]
                run["notes"].append("Recording used by order: the files changed since it was recorded.")
            if step is None:
                raise NoRecording(
                    "The recording does not match this request. Something changed since it was recorded "
                    "(instructions, skills, tools, data, layers or model). Record again with app/record.py.")
            run["i"] += 1
            time.sleep(min(step.get("latency", 1.0), 4.0) * self.speed)
            response = Message.model_validate(step["response"])
            return response, 0.0, step.get("request_id", "")
        if spend_so_far()["total_usd"] >= self.cap:
            raise SpendCapReached(f"Spend cap of {self.cap:.2f} USD reached. Stopped.")
        started = time.time()
        response = self.client.messages.create(model=self.model_id(model_key), **kwargs)
        latency = time.time() - started
        cost = cost_of(model_key, response.usage)
        _add_spend(cost)
        request_id = getattr(response, "_request_id", None) or response.id
        if self.mode == "record":
            run["saved"].append({"request_key": key, "response": response.to_dict(), "latency": round(latency, 2),
                                 "request_id": request_id})
        return response, cost, request_id
