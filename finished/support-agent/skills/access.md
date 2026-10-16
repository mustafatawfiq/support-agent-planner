---
name: access
description: The customer paid but cannot get in, or a link does not work.
use_when: The customer cannot log in, cannot reach the members area, or a link expired.
do_not_use_when: A video or page inside the members area does not work (use other and hand off).
---
# Skill: access

1. Call `find_customer` and `verify_identity`. If the sender is not verified, ask them to write from
   the email on their account. Do not send anything.
2. Look at the access status from `find_customer`.
   - "link_expired" or "link_not_used": call `send_access_link`. Tell them a new link is on its way,
     from which address, and how long it works.
   - "active": the account works. Give the login steps from the help file.
   - "ended" or anything else: call `hand_off_to_person`. A person checks it.
3. Call `search_knowledge` for the login steps, and name the help page.
4. Reply with ticket type `access`.
