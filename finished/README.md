# Support agent demo: the finished example

A small support agent for a made-up online community, Kitebridge Academy. It answers support
tickets, built in seven layers. All names, emails, prices and policies are made up.

## Run it

```
./start.sh
```

This opens the demo page at http://127.0.0.1:8765. The first run sets up Python (about one minute).
It needs a Mac or Linux computer with Python 3.9 or newer. Open the page in Chrome or Edge.

- **Recorded run (R):** plays the saved model answers. No network and no key needed. The code (customer lookup,
  identity check, refund rule, send rules) still runs for real. The screen says RECORDED RUN.
- **Live (L):** calls Claude. Needs a key in a file called `.env` next to `start.sh`:
  `ANTHROPIC_API_KEY=...` (or `OPENROUTER_API_KEY=...`). The screen says LIVE.

Keys on the page: `N` next step, `R` recorded run, `L` live, `1` to `7` layers on, left and right arrows change
ticket, `F` the agent's folder, `Q` people queue, `S` send rules, `G` full log, `T` test results, `V` step video,
`A` show steps as they come, `Esc` close.

## The seven layers

| Layer | What it adds | Where it lives |
|---|---|---|
| L1 Channel | Tickets in, replies out. Skips duplicates and auto-replies. Labels replies as written by AI | `inbox/`, `outbox/`, `tools/l1_channel.py` |
| L2 Agent | Reads the ticket, picks a type, decides the next step, writes the reply | `instructions.md`, `settings.yaml`, `tools/l2_reply.py` |
| L3 Knowledge | Help answers and the refund policy, with the source named | `knowledge/`, `policies/`, `tools/l3_knowledge.py` |
| L4 Customer data | Finds who is writing, by the sender's address only. Identity check | `data/customers.csv`, `tools/l4_customer_data.py` |
| L5 Actions and rules | Skills, the refund rule in code, actions (refund request, new access link) | `skills/`, `tools/l5_actions_and_rules.py` |
| L6 Hand-off | Send rules per ticket type, checks before sending, people queue, holding reply | `send-rules.yaml`, `queue/`, `tools/l6_hand_off.py` |
| L7 Log and tests | One log line per step, sample tickets with the expected outcome | `log/`, `tests/`, `tools/l7_log.py` |

The agent decides: the ticket type, which skill to follow, which tool to call, and what to write.
Code decides: who the customer is, whether they own the account, refund eligibility, and whether a reply
is sent, kept as a draft, or goes to a person.

## Other commands

```
./start.sh test            run every sample ticket 5 times and check the results (live, costs a little)
./start.sh record          record every ticket again after you change a file (live, costs a little)
./start.sh ticket T-104    run one ticket in the terminal
```

A recording only plays back if nothing changed since it was made. After you change instructions, skills,
tools, data or the policy, run `./start.sh record`.

## Use your own data

Replace the files in `support-agent/data/`, `inbox/`, `knowledge/` and `policies/` with your own, keeping the
same columns. Then run `./start.sh test`, and `./start.sh record` for the recorded runs.
