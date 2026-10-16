---
name: refund
description: The customer asks for money back.
use_when: The customer asks for a refund or for money back on a charge.
do_not_use_when: The customer only wants to cancel or stop renewal (use billing). A charge they do not recognise (billing).
---
# Skill: refund

1. Call `find_customer` and `verify_identity`.
   If the sender is not verified, stop here. Ask them to write from the email on their account.
   Do not say whether any other address has an account. Call `hand_off_to_person` if you have it.
2. If the customer gives a special reason (forgot to cancel, illness, an emergency, any request for an
   exception), do not decide anything. Call `hand_off_to_person` with a summary. Tell the customer a
   person will review it within one working day.
3. Call `check_refund_eligibility`. The tool applies the refund policy. Do not decide yourself.
4. If the tool says eligible: call `open_refund_request`. Tell the customer what the tool says happens
   next and how long it takes.
5. If the tool says not eligible: give the reason in plain words and quote the policy line.
   Tell them how to turn off renewal so they are not charged again.
   Tell them they can ask a person to review the decision at https://kitebridge.example/review.
6. Reply with ticket type `refund`. Name the refund policy as a source.
