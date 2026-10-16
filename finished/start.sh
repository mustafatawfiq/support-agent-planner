#!/bin/bash
# One command for the support agent demo.
#   ./start.sh                 open the demo page (http://127.0.0.1:8765)
#   ./start.sh record          record every ticket again (live model calls, about 0.10 USD on Haiku)
#   ./start.sh test            run every sample ticket 5 times and check the results (about 0.10 USD on Haiku)
#   ./start.sh ticket T-104    run one ticket in the terminal (add --layers 5, --mode replay)
set -e
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python
elif [ -x ../.venv/bin/python ] && ../.venv/bin/python -c "import anthropic" 2>/dev/null; then PY=../.venv/bin/python
else
  echo "First run: setting up Python (one minute)..."
  python3 -m venv .venv && .venv/bin/pip install -q anthropic
  PY=.venv/bin/python
fi
case "${1:-}" in
  record) shift; "$PY" app/record.py "$@" && "$PY" app/record.py --check ;;
  test)   shift; "$PY" app/eval.py "$@" ;;
  ticket) shift; "$PY" app/run.py "$@" ;;
  *)      "$PY" app/server.py "$@" ;;
esac
