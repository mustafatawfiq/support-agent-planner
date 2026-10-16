# Phase 2: build the agent folder

You copy a tested template and fill it from the plan. The code in `app/` and `support-agent/tools/` works
as it is. You fill the plain files: settings, instructions, knowledge, policies, data, skills, send rules.
Only write new code when the plan needs an action the template does not have (see step 7).

## 1. Copy the template

Copy everything inside `template/` (next to this file), including `.gitignore`, into the folder the user
opened you in. Do not overwrite a file that is already there: ask first. For example:

```
cp -Rn <this skill's folder>/template/. .
```

Then run `./start.sh check`. The first run sets up Python (about one minute). It lists every blank (`____`)
still to fill. You work through that list in the order below.

The folder, by layer:

| Layer | Files |
|---|---|
| L1 Channel | `support-agent/inbox/tickets.csv`, `support-agent/tools/l1_channel.py` |
| L2 Agent | `support-agent/settings.yaml`, `support-agent/instructions.md` |
| L3 Knowledge | `support-agent/knowledge/`, `support-agent/policies/` |
| L4 Customer data | `support-agent/data/customers.csv`, `support-agent/tools/l4_customer_data.py` |
| L5 Actions and rules | `support-agent/skills/`, `support-agent/tools/l5_actions_and_rules.py` |
| L6 Hand-off | `support-agent/send-rules.yaml`, `support-agent/tools/l6_hand_off.py` |
| L7 Log and tests | `support-agent/tests/expected.csv`, `support-agent/tools/l7_log.py`, and `log/` after a run |

Keys go in `.env` next to `start.sh`. It is in `.gitignore`, so it is never shared.

## 2. Ticket types: `send-rules.yaml` and `instructions.md` (L2, L6)

- In `send-rules.yaml`, replace `____: draft` with one line per ticket type from the plan, each set to `draft`.
  Keep `other: draft`. These lines are the list of ticket types the agent can pick.
- Set `allowed_link_domains` to their own website. If you do not know it, ask.
- In `instructions.md`, fill every blank from the plan: the business, what it sells and to whom, where
  customers write, the real reply time from L6, the tone, the sign-off, and the things the agent never does.
  The interview does not ask for the tone, the sign-off or the never-do list. Ask for them now, in one message,
  before you write them. You may offer an example; write only what they say.
  Add one row per ticket type to the table, with the same names as in `send-rules.yaml`, and keep `other`.

## 3. Settings: `settings.yaml` (L2, L4, L5)

- `business_name`, `sign_off` (the same as in `instructions.md`), `review_link` (where a customer asks a person to look again, from L6) and, only if the
  access link action is on, `access_email_from` and `access_link_valid_days`. Ask for any you do not have. Delete lines they do not need.
- `person_reply_time` and `person_reply_time_urgent`: what the customer hears when a person takes over, from L6,
  in their words (for example "within one working day"). If they have no faster lane for urgent tickets, both
  are the same. Never promise a faster time than they gave you.
- `model: haiku` to start. The model choice comes in phase 5.
- `test_date`: today's date. The tests use it as "today", so date rules give the same answer every run.
- `never_show_fields`: the fields from L4 the agent must never see, as a list (`  - field`). They must also be
  column names in `data/customers.csv`, or left out of it.
- `actions_on`: keep only the actions the plan needs, from this list:

| Action | Keep it when the plan has |
|---|---|
| `open_request` | anything the agent may not do alone: a plan change, a cancellation, an exception. A person does it. |
| `check_refund_eligibility` and `open_refund_request` | a refund rule with a window in days. The agent opens a request; a person approves. |
| `send_access_link` | a new login or access link when the old one expired or was never used |

## 4. Knowledge: `knowledge/` and `policies/` (L3)

- One file per question from the plan's top 10, named after the topic (for example `reset-password.md`).
  Follow `knowledge/example-topic.md`: the question as a customer asks it, then the line
  `Last checked: [date] · Owner: [name or role] · Link: [their page]`, then the answer.
- The answer is the one they already give, in their words. Ask them to paste it, or to give you the link to
  their help page and let you read it. Never write an answer from your own knowledge.
- A question with no answer yet: do not make a file. Add it to the open items. The agent hands it to a person.
- Delete `knowledge/example-topic.md` when you are done.
- Refunds: fill `policies/refund-policy.md` with their numbers in the table, and the rule in plain words. Keep
  the row names exactly as they are, because the refund tool reads them. If only some plans or products can be
  refunded, list them in the row "Plans or products that can be refunded", with the same names as in the `plan`
  or `product` column of `data/customers.csv`; otherwise leave it at "all". A number they do not know: write
  `Open` in its cell, and the tool sends every refund to a person until it has a number. No refunds at all:
  delete the file, the refund actions in `actions_on` and `skills/refund.md`.

## 5. Customer data: `data/customers.csv` (L4)

- This is a test copy with made-up people, never real ones. Keep the columns `customer_id`, `name`, `email`,
  `status` and `internal_note`.
- Keep `last_purchase_date`, `last_purchase_amount` and `refunds_last_12_months` if the refund rule is on.
  Keep `access` (values: `active`, `link_expired`, `link_not_used`, `ended`) if `send_access_link` is on.
- Add the columns for the fields the agent needs from L4, with simple names (for example `plan`,
  `order_status`, `tracking_link`). Delete columns they do not need.
- The rows come in phase 4, one made-up customer per test ticket. For now one made-up row is enough.

## 6. Skills: `skills/` (L5)

- One file per ticket type, except `other`, named after the type (`skills/login.md` for `login`). Follow
  `skills/your-ticket-type.md`: the top block (`name`, `description`, `use_when`, `do_not_use_when`), then
  the steps in order, from the plan's L2, L5 and L6 answers.
- Name each tool in backticks, exactly as it is called. The tools: `find_customer`, `verify_identity`,
  `search_knowledge`, `hand_off_to_person`, and the actions you kept in `actions_on`.
  The agent always starts with `sort_ticket` and `read_skill` and ends with `write_reply`, so a skill
  does not need to name those.
- Any account action comes after `find_customer` and `verify_identity`. Anything about money, an exception,
  anger or a legal threat goes to `hand_off_to_person`, as the plan says.
- `skills/refund.md` is a worked example. Keep and adapt it if they have refunds, or delete it.
- Delete `skills/your-ticket-type.md` when you are done.

## 7. A new action (only if the plan needs one)

If the plan has an action the list in step 3 does not cover, and it changes something (not just reading
a field, which `find_customer` already gives), add it to `tools/l5_actions_and_rules.py` the same way as
`open_request`: check `ctx.verified`, write one row for a person (or call their system, once connected),
do no harm if called twice, and add it to `TOOLS` with `needs_verified`. Add its name to `actions_on` and to
the skill that uses it. Show the user the new function in plain words before you go on.

## 8. Check and show

Run `./start.sh check` and fix every problem. A blank you cannot fill without a fact from them: ask them.
If they do not know, take it out of the file or write `Open`, and add it to the open items.

Then show them, in a short table, what is in each layer now, and what is still open. Every ticket type is
a draft. Ask if they want to go on to phase 3, connecting their help desk and customer data.
