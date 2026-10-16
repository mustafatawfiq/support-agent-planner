---
name: refund
description: The customer asks for money back.
use_when: ____
do_not_use_when: ____
---
# Skill: refund

1. Call `find_customer` and `verify_identity`. If the sender is not verified, stop. Ask them to write from
   the email on their account.
2. If the customer gives a special reason or asks for an exception, call `hand_off_to_person`. A person decides.
3. Call `check_refund_eligibility`. The tool applies the policy. Do not decide yourself.
4. Eligible: call `open_refund_request`, then say what happens next.
5. Not eligible: give the reason and the policy line, and say how to ask a person to review it.
