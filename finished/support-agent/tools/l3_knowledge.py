"""L3 Knowledge: search the help files and policies.

Code finds the files. The agent decides what to use, and names the source in its reply.
If nothing matches, the tool says so, and the agent must not guess.
"""
import re
from pathlib import Path

from helpers import header_value

STOP = set("the and for you your are can how what when where with this that from have has not but our "
           "out get its was will does did into about any all too then there they them their i me my".split())


def _words(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w.rstrip("s") if len(w) > 4 else w for w in words if len(w) > 2 and w not in STOP]


def _files(ctx):
    return sorted(ctx.folder.glob("knowledge/*.md")) + sorted(ctx.folder.glob("policies/*.md"))


def search_knowledge(ctx, question):
    asked = set(_words(question))
    scored = []
    for path in _files(ctx):
        text = path.read_text()
        title = text.splitlines()[0].lstrip("# ").strip()
        title_words, body_words = set(_words(title)), _words(text)
        score = sum(3 for w in asked if w in title_words) + sum(1 for w in body_words if w in asked)
        if score:
            scored.append((score, path, title, text))
    scored.sort(key=lambda s: -s[0])
    top = scored[:3]
    if not top:
        return {
            "result": {"found": False, "note": "Nothing in the help files matches. Do not guess. A person can answer."},
            "show": "Nothing found in the help files.",
        }
    files = [{
        "file": str(path.relative_to(ctx.folder)),
        "title": title,
        "link": header_value(path, "Link"),
        "last_checked": header_value(path, "Last checked") or header_value(path, "Version"),
        "text": text,
    } for _, path, title, text in top]
    return {
        "result": {"found": True, "files": files},
        "show": f"Found {len(files)}: " + "; ".join(f["title"] for f in files),
    }


TOOLS = [
    {
        "name": "search_knowledge",
        "layer": "L3",
        "label": "Searched the help files",
        "description": (
            "Search the help files and policies. Returns up to 3 files with their text, link and last-checked "
            "date. Use only what the files say, and name the file or link in your reply."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "What you are looking for, in a few words."}},
            "required": ["question"],
            "additionalProperties": False,
        },
        "run": search_knowledge,
    }
]
