# What to say to your coding agent

Open Claude Code, or another coding agent, in the folder named in each prompt. Send one prompt at a time,
and read what it did before you send the next.

## Before you start: see it work

Prompt 0, see the finished example (open your coding agent in this kit folder):

```
Start ./start.sh inside the finished folder in the background, then give me the address of the page. It plays recorded runs, so it needs no API key. Ask me if anything is missing. Do not invent facts.
```

## Plan and build your agent

Make an empty folder and copy the `support-agent-builder` folder into it. Open your coding agent in that folder.

Prompt 1, plan and build with the skill:

```
Use the support-agent-builder skill in this folder to plan and build my support agent.
```

The skill interviews you one step at a time, writes `support-agent-plan.md`, builds the agent folder, helps you
connect your help desk and customer data, and builds your test set from 20 past tickets. It asks when it needs
a fact from you, and it asks before anything costs money.

## Later, in the same folder

Prompt 2, connect your help desk and customer data:

```
Connect my help desk (____) and my customer data (____), read only. Put the keys in .env, never in the code. Show me each change before you run it on real messages or real customers. Ask me if anything is missing. Do not invent facts.
```

Prompt 3, run the tests and fix one fail:

```
Run ./start.sh test and show me pass or fail for each ticket. For each fail, tell me in one line what is missing: a knowledge file, a skill step or a rule. Fix the first one, then run that ticket again 5 times. Ask me if anything is missing. Do not invent facts.
```

Prompt 4, the same test set on another model:

```
Run the same test set on another model with ./start.sh test --model sonnet. Compare it with the last run, ticket by ticket: runs passed, cost and seconds per ticket. Tell me which model you would pick for the types that pass every run, and why. Do not invent facts.
```

The tests call your model with your API key, so each run costs a little. Run them again after every change,
when a new model comes out, and when prices change. When the agent gets a real ticket wrong, add it to the
test set, rewritten without names, with the right outcome.

## After phase 5: go live

Prompt 5, the go-live step:

```
Use the go-live step of the support-agent-builder skill to take my agent live. Start on my computer, with every ticket type a draft. Ask me your questions one at a time, then help me set it up where it can run all day. Use an API key, never a subscription login, keep the key on the server, and keep the spend cap on. Show me each change before it runs on real messages. Do not invent facts.
```
