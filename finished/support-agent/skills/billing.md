---
name: billing
description: Charges, payment dates, invoices, or the card on file.
use_when: Questions about payments, dates, amounts, invoices, the card, or turning off renewal.
do_not_use_when: The customer asks for money back (use refund).
---
# Skill: billing

1. Call `find_customer` and `verify_identity`. If the sender is not verified, answer only general
   questions from the help files. Do not share any account details.
2. Call `search_knowledge` for the how-to part of the question.
3. Answer with the customer's own facts from `find_customer`: plan, next payment date, amount.
   Write dates in words, for example "27 October 2026".
4. Give the steps from the help file and its link.
5. A charge the customer does not recognise, or a double charge: call `hand_off_to_person`. A person
   checks payments.
6. Reply with ticket type `billing`.
