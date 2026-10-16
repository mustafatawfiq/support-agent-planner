# Your support agent

Built with the support-agent-builder skill. Your plan is in `support-agent-plan.md`.

| Command | What it does | Costs money |
|---|---|---|
| `./start.sh check` | Finds blanks and mistakes in the folder | No |
| `./start.sh test` | Runs every test ticket 5 times and shows what passed | Yes, on your key |
| `./start.sh test --model sonnet` | The same test set on another model | Yes, on your key |
| `./start.sh ticket T-0001` | Runs one ticket and shows every step | Yes, on your key |
| `./start.sh pull --limit 2` | Reads 2 new messages from your help desk, once connected | No model |
| `./start.sh lookup name@example.com` | Looks up one customer in your connected data | No model |

Your key goes in `.env` next to `start.sh`, for example `ANTHROPIC_API_KEY=...`. Never share that file.

Every ticket type starts as a draft in `support-agent/send-rules.yaml`. Switch a type to `send` only after
every test run of it passes.
