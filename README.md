# Support agent kit

A head start from the Customer Support Agents room at AIS Live, 18 October 2026.

One skill plans and builds a first support agent for your own business, with you, in an empty folder. It
builds the agent in the same seven layers as the session: Channel, Agent, Knowledge, Customer data,
Actions and rules, Hand-off, Log and tests.

## What you need

- A Mac or Linux computer.
- Python 3.9 or newer.
- Claude Code, or another coding agent that can read a skill file and run commands.
- A model API key in a file called `.env`, when you test your agent. The finished example needs no key.

## What is inside

| File or folder | What it is |
|---|---|
| `support-agent-builder/` | The skill. `SKILL.md` and its guides interview you, plan the agent, and build it from the tested template in `template/`. |
| `finished/` | A finished agent for a made-up business, with recorded runs you can watch for free. |
| `PROMPTS.md` | What to say to your coding agent: the opening prompt and three for later. |

## First, see it work

```
cd finished
./start.sh
```

Then open http://127.0.0.1:8765 in Chrome or Edge. The page plays recorded runs, so it needs no key and costs
nothing. The first run sets up Python, which takes about one minute. Or send your coding agent prompt 0 from
`PROMPTS.md`.

## Build your own

1. Make an empty folder, for example `my-support-agent`, and copy the `support-agent-builder` folder into it.
2. Open Claude Code in that folder and send:

   ```
   Use the support-agent-builder skill in this folder to plan and build my support agent.
   ```

3. Talk with it. It works in five phases, and tells you where you are:
   1. **Plan.** It interviews you in 9 short steps and writes `support-agent-plan.md`.
   2. **Build.** It copies the template and fills it from your plan, layer by layer. Every ticket type starts
      as a draft. `./start.sh check` finds blanks and mistakes, for free.
   3. **Connect.** It helps you connect your help desk or inbox and your customer data, read only. Your keys go in
      `.env`, never in the code. It shows each change before anything runs on real messages.
   4. **Test set.** It turns 20 of your past tickets into test tickets with made-up names, each with the right
      outcome you confirm.
   5. **Test and choose the model.** It explains the tests and how to compare models, and runs them only when
      you say yes, because they cost money.

To use the skill in any folder, copy `support-agent-builder` into `~/.claude/skills/` as well.

## Test it, and keep testing

- `./start.sh test` runs every test ticket 5 times, because the same ticket can get a different answer on
  another run. You see how many runs passed for each ticket.
- Each fail is a missing knowledge file, a missing skill step or a missing rule. Fix that piece, then test again.
- `./start.sh test --model sonnet` runs the same test set on another model. Pick the model by the results:
  runs passed, cost and time per ticket.
- It never ends. New models, new prices and new kinds of tickets come. Run the test set again on every change,
  and add every wrong answer to it.
- A ticket type may send on its own only when every run of it passes. Every other type stays a draft for a
  person to read and send.

## Where each layer lives in your folder

| Layer | Files in `support-agent/` |
|---|---|
| L1 Channel | `inbox/tickets.csv`, `tools/l1_channel.py` |
| L2 Agent | `settings.yaml`, `instructions.md` |
| L3 Knowledge | `knowledge/`, `policies/` |
| L4 Customer data | `data/customers.csv`, `tools/l4_customer_data.py` |
| L5 Actions and rules | `skills/`, `tools/l5_actions_and_rules.py` |
| L6 Hand-off | `send-rules.yaml`, `tools/l6_hand_off.py` |
| L7 Log and tests | `tests/expected.csv`, `tools/l7_log.py`, and `log/` once it has run |

## Good to know

- Nothing is sent to customers. Every ticket type starts as a draft, and the help desk connection reads
  messages and saves drafts only.
- The skill never makes up facts about your business. When it needs an answer, a price or a rule, it asks you.
  What you do not know yet goes on a list of open items, and the agent hands that topic to a person.
- Never put real customer names, emails or order numbers in the test files. The skill rewrites them.
- Keep your `.env` file to yourself. Do not share it or add it to a repository.
- The finished example is a made-up business. Its names, emails, prices and policy are all made up.
