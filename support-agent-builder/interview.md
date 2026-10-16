# Phase 1: the interview

Interview the user in 9 short steps: where they are today, the seven layers of a support agent (L1 to L7),
and their first step this week. Then write their plan to `support-agent-plan.md`.

The seven layers:

1. Channel: where tickets come in and replies go out.
2. Agent: what kinds of tickets they get, and what the agent does with each.
3. Knowledge: where the answers live, and who keeps them current.
4. Customer data: who is writing, and do they own the account.
5. Actions and rules: what the agent may change, and the rules behind it.
6. Hand-off: when the agent stops, and who takes over.
7. Log and tests: how they know it works before it sends on its own.

## How to run the interview

- Ask about one step at a time. Put that step's questions in one message as a short numbered list. The user can answer in any order, in a few words.
- Under the questions, give 2 or 3 short examples from different businesses (an online course, a small online shop, a software tool). Keep each example to one line.
- After each answer, reply with one line that says what you noted, then go to the next step. Show progress, for example "Step 3 of 9".
- If an answer is unclear, ask one follow-up question at most. Then move on.
- "skip": write "Skipped" for that step and move on. "I don't know": write "Open:" and the thing they need to find out, and move on.
- Use the user's own words in the plan. Do not invent facts about their business, their tools or their numbers.
- Privacy: never ask for real customer names, emails, order numbers or account details. If the user pastes a real ticket, ask them to rewrite it without names first, and do not copy the private parts into the plan.
- Write in simple English and short sentences. No hype.
- Each step has one tip. Share it after the user answers, in one or two lines.

## The 9 steps

### Step 1 of 9: Where are you today?

Ask:

1. In one line, what does your business sell, and who writes to you?
2. Where do customer messages arrive? (email, a help desk, site chat, a form, a community, WhatsApp)
3. About how many messages a week?
4. Who answers them today, and about how many hours a week does it take?

Examples:

- "Online course. Students email about access and refunds. About 80 a week. I answer, 5 hours a week."
- "Small online shop. Help desk plus Instagram messages. About 200 a week. Two people part time."
- "Software tool. A form and a shared inbox. About 50 a week, mostly bug reports and billing."

### Step 2 of 9: L1 Channel, where tickets come in and replies go out

Ask:

1. Which one channel will the first version handle?
2. How does a new message reach your agent? (a help desk webhook, a shared inbox, a form)
3. Which messages must never get an automatic reply? (auto-replies, bounces, tickets a person already took, duplicates)

Examples:

- "Help desk. A webhook fires on each new ticket."
- "Shared inbox. A rule forwards new mail to the agent."
- "Website form. Each entry lands in a sheet the agent reads."

Tip: skip duplicates, auto-replies and tickets a person already took in plain code, before the agent sees them. This stops reply loops before any reply goes out.

### Step 3 of 9: L2 Agent, what kinds of tickets do you get?

Ask the user to list their 3 to 6 most common kinds of messages. For each kind:

1. A real example, rewritten with no names.
2. What should the agent do: send the reply on its own, write a draft for a person, or hand it off?
3. If it hands off, to whom?

Always add a last row yourself: "Other / not sure", with "Hand off".

Give each type a short name in lowercase, one or two words joined by a hyphen, for example `refund`, `login`
or `order-status`. Say the names back to them. These names become the ticket types in the agent folder.

Examples:

- "Can't log in. 'I paid but the course page won't open.' Send. Hand off to: me, if the check fails."
- "Refund request. 'I want my money back, it's not for me.' Hand off. To: the owner."
- "Where is my order. 'It's been 6 days and no tracking.' Draft."

Tip: one agent reads the whole ticket and opens one short instruction file per ticket type. A new ticket type is one new file, with no rewiring.

### Step 4 of 9: L3 Knowledge, where do the answers live?

Ask:

1. Where do your answers live today? (help pages, old replies, a FAQ, someone's head)
2. Who keeps them up to date, and how often will someone check them?
3. Which 10 questions do you get most? For each, where is the answer you already give: a help page link, or
   text you can paste? (You collect the answers in phase 2. If they have no list yet, write "Open: collect top 10".)

Examples:

- "Half in our help pages, half in old email replies. I update them when something changes."
- "Mostly in my head. Nobody owns it yet."
- "A FAQ page plus a shared doc. Support lead checks it monthly."

Tip: start from the answers your team already sends. Give each answer one owner, a source and a date.

### Step 5 of 9: L4 Customer data, who is writing?

Ask:

1. Where is the customer record? (CRM, billing tool, a sheet)
2. How do you know the writer owns the account? (they write from the email on file, they are logged in, or you send a code to the email on file)
3. Which fields does the agent need?
4. Which fields should it never see?

Examples:

- "Billing tool. They must write from the email on file. Needs plan and join date. Never card details."
- "CRM plus a sheet of orders. Match on order email. Needs order status. Never home address."
- "Our own app database. They are logged in when they use the in-app chat."

Tip: run the identity check in code, before any account action. Give the agent only the fields it needs.

### Step 6 of 9: L5 Actions and rules, what can it do?

Ask:

1. Which actions could the agent take? (send a new access link, change a plan, open a refund request, resend an invoice)
2. For each action, what is the rule? Write it as "if ... then ...". For example: "If the purchase is less than __ days old and ..., then the refund is allowed."
3. Which actions should only create a request for a person to approve?

Examples:

- "Send a new access link. If the writer's email matches an active account, then send the link."
- "Refund. If the purchase is inside your refund window, then open a refund request. A person approves."
- "Change plan. Never alone. Always a request for a person."

Tip: rules go in code, and the agent calls them. An action run twice by mistake must do no harm. Anything with money: the agent opens a request, and a person approves.

For the refund rule, ask for the numbers: how many days after the purchase a refund is possible, and how many
refunds one customer may get in 12 months. If they do not know, write "Open:" for each.

### Step 7 of 9: L6 Hand-off, when does it stop, and who takes over?

Ask:

1. When must the agent stop? (an angry customer, a legal threat, a request for an exception, it is not sure, the identity check fails)
2. Who gets the ticket, where do they see it, and how fast do they answer?
3. What does the customer hear? For example: "A person will reply within one working day."
4. If the agent says no, how can the customer ask a person to look again?

Examples:

- "Stop on any refund, anger or legal word. Goes to me in the help desk. I answer the same day."
- "Stop when unsure. Goes to the shared inbox with a tag. Reply within one working day."
- "Customer can reply 'person' to reach the team."

Tip: give the person a short summary: who wrote, what they asked, and what the agent already checked. A ticket type sends on its own only after it passes its tests; everything else starts as a draft for a person.

### Step 8 of 9: L7 Log and tests, how will you know it works?

Ask:

1. Can you pick 20 past tickets, rewrite them without names, and write the right outcome for each? (They can do this later. Write "Open: build the test set" if so.)
2. How many times will you run each one? (Several runs, because the same ticket can get a different answer on another run.)
3. What will you log for each step? (the ticket, the type, the tools used, the decision, who sent the reply)

Examples:

- "I'll take 20 tickets from last month: 8 access, 6 refunds, 6 other."
- "Run each one 5 times before we change anything."
- "Log to a sheet: ticket, type, tools, decision, sent by."

Tip: a ticket type may send on its own only when it gets every run right.

### Step 9 of 9: Your first step this week

Ask:

1. What is one thing you will do this week?

Examples:

- "Collect my top 10 answers in one file."
- "Pull 20 past tickets and rewrite them without names."
- "Run 20 past tickets through the agent with sending turned off."

## Write the plan

When step 9 is done (or skipped), say you are writing the plan. Write it to `support-agent-plan.md` in this
folder. If that file already exists, ask before you replace it.

Use this template. Fill it with their answers, in their words. Keep "Skipped" and "Open:" lines as they are.
Remove the hints in brackets. Then show them the plan in a few lines and ask if anything is wrong.

```markdown
# Support agent plan: [business, in a few words]

Date: [today's date]

## Where you are today
- What you sell, and who writes to you:
- Where messages arrive:
- About how many a week:
- Who answers, and hours a week:

## L1 Channel
- First channel:
- How a new message reaches the agent:
- Never send an automatic reply to:

## L2 Agent: ticket types
| Ticket type | Example (rewritten, no names) | Send / draft / hand off | Hand off to |
|---|---|---|---|
| | | | |
| other | | Hand off | |

## L3 Knowledge
- Where the answers live today:
- Who keeps them up to date, and how often they are checked:
- Top 10 questions, and where each answer is:

## L4 Customer data
- Where the customer record is:
- How you know the writer owns the account:
- Fields the agent needs:
- Fields it must never see:

## L5 Actions and rules
| Action | Rule (if ... then ...) | Alone, or a request for a person |
|---|---|---|
| | | |

## L6 Hand-off
- The agent stops when:
- Who gets the ticket, where, and how fast:
- What the customer hears:
- How the customer asks a person to look again:

## L7 Log and tests
- Test set (20 past tickets, no names, right outcome for each):
- Runs per ticket:
- What you log for each step:

## Your first step this week
-

## Open items
- [every "Open:" line from above, one per line]
```

Note: "Send" in the ticket type table is where they want to end up. The agent you build starts with every
type as a draft, and a type sends on its own only after it passes every test run.
