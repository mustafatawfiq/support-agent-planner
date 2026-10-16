---
name: upsell
description: Questions about a bigger plan, or switching plans.
use_when: The customer asks what a bigger plan adds, what it costs, or how to switch.
do_not_use_when: The customer wants to cancel or pay less (use billing).
---
# Skill: upsell

1. Call `find_customer` so you know the plan they have now.
2. Call `search_knowledge` for the plans and how switching works.
3. Answer from the help files only: what the bigger plan adds, its price, and how to switch.
   Do not work out a price yourself. The switch page shows the exact amount before they pay.
4. A team, company or bulk deal (more than one person) is a sales lead: call `hand_off_to_person` so a
   person replies. Answer the rest of the message.
5. Do not offer discounts.
6. Reply with ticket type `upsell`.
