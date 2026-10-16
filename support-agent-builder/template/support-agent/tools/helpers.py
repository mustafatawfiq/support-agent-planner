"""Small shared helpers for the tools: read files, write rows, dates and masking.

Nothing here talks to the AI. It is plain code that gives the same answer every time.
"""
import csv
import re
from datetime import date, datetime
from pathlib import Path


def read_settings(path):
    """Read a simple settings file: "name: value" lines, "# notes", and "  - item" lists."""
    values, current_list = {}, None
    for raw in Path(path).read_text().splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and current_list is not None:
            values[current_list].append(line.strip()[2:].strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            if value == "":
                values[key], current_list = [], key
            else:
                values[key], current_list = value, None
    return values


def read_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(f)]


def add_row(path, row):
    """Append one row to a CSV file. Creates the file with a header the first time."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            writer.writeheader()
        writer.writerow(row)


def table_values(path):
    """Read the first "| Rule | Value |" table in a markdown file into a dict."""
    values = {}
    for line in Path(path).read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and line.strip().startswith("|") and not set(cells[0]) <= set("-: "):
            if cells[0].lower() in ("rule", "plan"):
                continue
            values[cells[0]] = cells[1]
    return values


def header_value(path, name):
    """Read "Name: value" from the top lines of a markdown file, for example the policy version."""
    for line in Path(path).read_text().splitlines()[:6]:
        for part in line.split("·"):
            if part.strip().lower().startswith(name.lower() + ":"):
                return part.split(":", 1)[1].strip()
    return ""


def first_number(text):
    match = re.search(r"\d+(\.\d+)?", text or "")
    return float(match.group()) if match else None


def to_date(text):
    return datetime.strptime(text, "%Y-%m-%d").date() if text else None


def date_words(d):
    return f"{d.day} {d.strftime('%B %Y')}" if d else ""


def today_from(settings):
    """The tests use test_date from settings.yaml as today, so date rules give the same answer every run."""
    return to_date(settings.get("test_date", "")) or date.today()


def ticket_types(folder):
    """The ticket types are the names in send-rules.yaml that are set to send or draft."""
    return [k for k, v in read_settings(Path(folder) / "send-rules.yaml").items()
            if isinstance(v, str) and v in ("send", "draft")]


def env_value(name):
    """A key or setting from the .env file next to start.sh, or from the environment. Never print it."""
    import os
    root = Path(__file__).resolve().parents[2]
    path = root / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                if key.strip() == name:
                    return value.strip().strip('"').strip("'")
    return os.environ.get(name, "")


def plan_name(plan_id):
    return plan_id.replace("_", " ").title() if plan_id else ""


def mask_email(text):
    return re.sub(r"\b([A-Za-z0-9])[A-Za-z0-9._%+-]*@", r"\1***@", text)
