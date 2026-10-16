#!/bin/bash
# One command for your support agent.
#   ./start.sh check            check the folder for blanks and mistakes (free, no model)
#   ./start.sh test             run every test ticket 5 times and check the results (calls your model, costs a little)
#   ./start.sh test --model sonnet       the same test set on another model (models are listed in app/llm.py)
#   ./start.sh test --runs 1 --tickets T-0003    fewer runs while you fix one ticket
#   ./start.sh ticket T-0003    run one ticket in the terminal and show every step (calls your model)
#   ./start.sh pull --limit 3   read 3 new messages from your help desk, once it is connected (read only)
#   ./start.sh lookup name@example.com   look up one customer in your connected customer data (read only)
set -e
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python
else
  echo "First run: setting up Python (about one minute)..."
  python3 -m venv .venv && .venv/bin/pip install -q anthropic
  PY=.venv/bin/python
fi
case "${1:-}" in
  check)  shift; "$PY" app/check.py "$@" ;;
  test)   shift; "$PY" app/eval.py "$@" ;;
  ticket) shift; "$PY" app/run.py "$@" ;;
  pull|lookup) "$PY" app/connections.py "$@" ;;
  *)      sed -n '2,9p' "$0" | sed 's/^# //' ;;
esac
