# After phase 5: go live

Read this before the go-live step. It comes after phase 5, and only when they want it. It is not a sixth phase:
say "After phase 5: go live", never "Phase 6 of 5". If phase 3 was skipped, do `connect.md` first.

Open the step with this line, in these words:

> Now I help you go live: first on your own computer, then where it can run all day.

The step has four parts. Tell them where they are, for example "Go live, part 1 of 4: your own computer".

## 1. Your own computer first

The agent runs on new tickets on their computer, and every reply stays a draft.

1. Add a listener: the part that starts the agent on each new ticket. There are two ways:
   - **An inbox check.** It looks for new messages every few minutes, with `fetch_new_messages`. On a laptop this
     is the simplest way.
   - **A webhook.** Their help desk calls the listener on each new ticket. A webhook needs an address the help
     desk can reach, so it fits a server better than a laptop.
2. Write the listener as one new file, for example `app/listen.py`. It reads new messages, runs each one through
   the same agent code that `./start.sh ticket` uses, and puts the reply back with `save_draft`. Do not change
   the tested code.
3. Check `support-agent/send-rules.yaml`: every type is `draft`.
4. Each ticket calls their model, so this costs money. Say how often it checks and about what a day of tickets
   costs, from the cost per ticket in their test runs. Wait for a yes, then start it.
5. Look at the drafts with them for a while, every day. When they fix a draft, the fix goes into the right file
   (`knowledge/`, `policies/` or `skills/`), and the ticket goes into the test set, rewritten (see `tests.md`).
   Then run `./start.sh check`, and the tests when they say yes.

## 2. A couple of questions: where it runs

Ask one at a time, in these words. Skip a question when the plan already answers it.

1. "Does your help desk have webhooks, or should the agent check the inbox every few minutes?"
2. "About how many tickets do you get a day?"
3. "Must the customer data stay in one country, or on machines you control?"
4. "Do you want to look after a small server yourself, or have a host run it for you?"

Then say: "There are lots of options." Recommend the simplest one that fits their answers, and say why in one
line. Start from the kit's own app. Explain only the option you recommend, unless they ask about the others.

| Option | What it is | It fits when |
|---|---|---|
| The kit's app on a small cloud server (a VPS), for example Hetzner or DigitalOcean | The app in this folder, on a server they look after | They are fine looking after a small server |
| The kit's app on an app host, for example Railway or Render | The same app; the host runs the machine | They want a host to run it |
| Managed Agents | Anthropic runs the agent for them. Their tools still run on their side. It is still in beta, and it is not for health or other regulated data. | Only when they ask for it, and it means moving the skills and tools over |
| The Agent SDK on machines they control | Claude Code's agent tools, on their own machines | The agent must run on machines they control. It is the most work: you must shut off everything a customer should never reach. |

- The number of tickets a day sets how often the inbox check runs, and the spend cap (part 3).
- If the data must stay in one country: say plainly that the model is called over the internet, wherever the agent
  runs. Do not promise where the model provider keeps data. Point them to the provider's own terms, and write it as
  "Open:" in the plan.
- Never name a price. Prices change; they check them on the host's own page.

## 3. Help them set it up

Go step by step. Before each change, show it in plain words and wait for a yes. These rules always hold:

- **An API key, never a subscription login.** The agent serves their customers, so it runs on an API key.
- **The key stays on the server, in its `.env`.** Or in the host's own secret settings: the app reads both. They
  paste the value themselves. Never put the key in code, in chat or in a repository.
- **A spend cap.** The app stops live runs when the total reaches `SPEND_CAP_USD`, and a ticket that costs more
  than `max_cost_per_ticket_usd` in `settings.yaml` goes to a person. The app reads `SPEND_CAP_USD` from the
  environment, not from `.env`: set it in the host's settings, or in the command that starts the listener. Set both
  caps with them, from their number of tickets and the cost per ticket in their test runs. Never raise a cap
  without their yes.

Then:

1. Copy the folder to the server or the host, without `.env`. They create `.env` there, or the host's secret
   settings, and paste the keys.
2. If they use a webhook, point the help desk's webhook to the listener's address on the server.
3. Try it on very little: `./start.sh pull --limit 2` reads 2 messages, then one ticket goes through as a draft.
   Read the result with them.
4. Then start the listener, and stop it on the computer, so only one runs.

## 4. It starts in stage 1

- Every type stays `draft`. A person reads each draft and sends it.
- Their fixes go into the files, and the tickets go into the test set, as in part 1.
- A type switches to `send` only after every test run of it passes, and only when they ask. Even then, the checks
  in `send-rules.yaml` run on each reply, and a reply that fails a check stays a draft.
- Nothing goes live and nothing costs money without their yes.

## When the step is done

Say in two or three lines what runs where and what is open. Their next step: read the drafts every day for a while.
