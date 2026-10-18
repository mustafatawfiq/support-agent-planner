# Phase 3: connect the help desk and the customer data

The tests never need a connection: they use the made-up tickets and customers in the folder. A connection
is for later, when the agent works on real messages as drafts. Build it now, try it read only, and stop
there. If they want to skip this phase for now, write "Open: connect the help desk" and go to phase 4.

## What to connect

| What | Where in the folder | What it does |
|---|---|---|
| Help desk or inbox (L1) | `fetch_new_messages` and `save_draft` in `support-agent/tools/l1_channel.py` | Reads new messages. Puts a reply back as a draft or an internal note. Never sends. |
| Customer data (L4) | `fetch_customer` in `support-agent/tools/l4_customer_data.py` | Finds one customer by the sender's email. Reads only. |

Each function says in its comment what it must return. Keep those shapes, so the rest of the code works
unchanged.

## How

1. Ask which help desk or inbox they use (from the plan, L1) and where the customer record lives (L4).
2. Find that tool's official API documentation. Ask them for the link, or read it yourself if you can browse.
   Never guess an address, a field name or a permission. If you cannot find it, say so and ask.
3. Tell them which key they need, with the least access that works: read messages and write drafts or
   internal notes for the help desk; read customers for the customer data. Never a key that can send,
   refund or delete.
4. Tell them the line to add to `.env` (for example `HELPDESK_API_KEY=`). They paste the value themselves.
   The code reads it with `helpers.env_value("HELPDESK_API_KEY")`. Never put a key in code or in chat.
5. Write the functions. Return only the fields the agent needs, with the same column names as
   `inbox/tickets.csv` and `data/customers.csv`. Leave out every field the plan says it must never see.
6. Show them the change in plain words: what it reads, what it writes, what it never does. Wait for a yes.
7. Try it read only, on very little, after their yes:
   - `./start.sh pull --limit 2` reads 2 new messages into `support-agent/inbox/live.csv` and prints the
     subjects. Real messages stay there. They never go into the tests.
   - `./start.sh lookup name@their-domain` looks up one customer they choose and prints the fields the agent gets.
   Read the result with them. Fix anything wrong.
8. Do not run the agent on real messages yet, and do not call `save_draft` on a real ticket. That comes after
   the tests pass, when they ask for it, in the go-live step (`go-live.md`).

## Their own system with no API

If messages arrive in a shared inbox, connect to that inbox (for example with its API or IMAP), read only.
If the customer record is a sheet, an export to `data/customers-live.csv` can be the first version, read by
`fetch_customer`. Never put real customers in `data/customers.csv`: that file is the made-up test copy. Say what
the choice means: an export goes out of date, so someone must refresh it, and it is real data on this computer.
