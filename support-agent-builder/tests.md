# Phases 4 and 5: the test set, the tests and the model

## Phase 4: build the test set

The test set is 20 of their past tickets, rewritten, each with the right outcome. It is how they know the
agent works before it sends anything on its own, and how they compare models later.

### 1. Collect 20 past tickets

Ask them to paste 20 past messages, or to choose them from their help desk. A good mix:

- the common types, about in the share they arrive;
- a few hard ones: an angry customer, an exception ("my case is special"), a question the help files do not
  answer, a sender with no account, an automatic reply (out of office), and the same message sent twice.

If they cannot get 20 now, take what they have, write "Open: more test tickets", and go on.

### 2. Rewrite them

- Rewrite every ticket, even when they say the tickets are already anonymous: you cannot check that, and a
  real name in a test file is hard to take back. Give every sender a new made-up name and an `@example.com`
  address, and change any name inside the message to match. Take out order numbers, phone numbers and anything
  else private. Keep the meaning and the way people write, including mistakes and anger.
- Put them in `support-agent/inbox/tickets.csv`, one row each, with ids `T-0001`, `T-0002` and so on.
  `received_at` is a date and time near `test_date`. Every message gets its own `message_id`; a duplicate
  repeats the first one's id with a later time. An automatic reply has `yes` in `auto_submitted`.
- Make the customers in `support-agent/data/customers.csv` match: one made-up customer per sender, with the
  data that makes the story true. For example, a refund the customer should get has a `last_purchase_date`
  a few days before `test_date`; a late one is outside the window. A sender with no account has no row.
- Delete the example row (T-0001 from the template) if it is not one of theirs.

### 3. Write the right outcome for each

One row per ticket in `support-agent/tests/expected.csv`:

| Column | What to write |
|---|---|
| `ticket_id` | the ticket |
| `scenario` | a few words, for example "Refund, inside the window" |
| `expect_type` | the ticket type, or `skipped` for one L1 skips (a duplicate or an automatic reply) |
| `must_call` | the tools the agent must use, joined by `;`, for example `verify_identity;check_refund_eligibility` |
| `must_not_call` | tools it must not use, for example `open_refund_request` on a late refund |
| `refund_decision` | `eligible`, `not_eligible`, or `none` when no refund rule runs |
| `hand_off_to_person` | `yes` or `no` |
| `delivery` | what happens to the reply: `draft`, `person`, `send` or `skipped`; two allowed as `draft;person` |
| `reply_must_match` | optional: a word the reply must have, for example the link of the right help page |
| `reply_must_not_match` | optional: a word it must never have, for example a promise |

Propose the outcomes from the plan, then show them as a short table (ticket, what should happen) and ask them
to confirm or correct each one. The right outcome is theirs to decide, not yours.

### 4. Check

Run `./start.sh check` until it shows no problems. It also finds test rows that can never pass, for example a
refund outcome that does not match their own policy numbers, or `send` on a type that is still a draft.

## Phase 5: test, read the fails, choose the model

Explain this in plain words. Then ask if they want to run the tests now. A test run calls their model with
their key, so it costs money: say what it runs, and run it only after a yes. If they say not now, the
phase ends with the explanation.

### How the test works

- `./start.sh test` runs every test ticket 5 times. The same ticket can get a different answer on another
  run, so one good run proves little.
- Tickets that L1 skips (duplicates, automatic replies) never reach the model, so they cost nothing. Count only
  the others when you say how many runs a test makes.
- For each ticket it shows how many runs passed, for example "3 of 5", and why each fail failed. It saves
  a page, `support-agent/tests/test-grid.html`, and the full results in `evals/`.
- It needs a key in `.env`, for example `ANTHROPIC_API_KEY=`. They paste the value themselves.
- While they fix one ticket: `./start.sh test --tickets T-0004 --runs 5`. Then run the whole set again.

### Reading a fail

Each fail points to one missing piece. Explain each fail in one line, then fix that piece, not the test:

| The fail says | Usually missing |
|---|---|
| `type X, expected Y` | a clear line in the ticket type table in `instructions.md`, or in the skill's `use_when` |
| `did not call ...` or `called ...` | a skill step, or a step in the wrong order |
| `refund decision ...` | a rule: the numbers in the policy, or the customer data |
| `reply lacks ...` | a knowledge file, or the answer is not in it |
| `no hand-off` or `handed off` | a hand-off step in the skill, or a line in `instructions.md` |
| `internal words` | a "never" line in `instructions.md`, or a word in `never_in_replies` |
| `error: ...` | the code or the setup: read the message, fix it, and run the check |

### Switch on one type

When every run of every ticket of one type passes, that type may send on its own: set it to `send` in
`send-rules.yaml`, only when they ask. Every other type stays a draft for a person to read and send.

### The same test set on another model

- `./start.sh test --model sonnet` runs the same tickets on another model. The models are listed in
  `app/llm.py` (MODELS), with their names and prices. To add one, ask them for its exact model name and price
  from their provider's page, and add a line. Never guess a model name or a price.
- Compare, ticket by ticket: how many runs passed, the cost per ticket and the seconds per ticket. Pick the
  model that passes every run of the types they want to switch on, at a cost they accept.

### It never ends

- New models come out, prices change, and new kinds of tickets arrive. Run the same test set again when any
  of these change, and after every change to the files.
- Every wrong answer the agent gives in real use becomes a new test ticket, with the right outcome. The test
  set grows, and a fixed mistake stays fixed.
