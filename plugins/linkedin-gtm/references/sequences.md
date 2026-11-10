# Sequences

A sequence is a plan for one person, not an automation. Each step is still its own batch item, approved on the day it goes out. The ledger item's `sequence` field records which sequence and step it is, for example `{"name": "prospect", "step": "day_4"}`, so the CRM export and the follow-up check can find it.

## Partner (Lane A, only once released)

| Step | When | Action | Notes |
|---|---|---|---|
| day_0 | first | comment on one of their posts | the comment has to stand on its own |
| connect | day 1 to 2 | connection request with a note tied to their work | under 200 characters |
| on_accept | when accepted | thank them, then one question about their roadmap | partner tone, asking for their ideas |
| day_4 | 4 days after on_accept | share a relevant resource, no ask | a real resource Dorian has, not a pitch deck |
| day_10 | 10 days after on_accept | final, low-pressure follow-up | then stop |

## Prospect (Lane B)

| Step | When | Action |
|---|---|---|
| signal | first | an engagement signal (they posted, commented, viewed) and Dorian engaged with it |
| connect | after the signal | connection request with a context note |
| on_accept | when accepted | value-first DM that references the signal |
| day_4 | 4 days later | follow-up |
| day_10 | 10 days later | close the loop, then stop |

## Inbound (Lane D)

| Step | When | Action |
|---|---|---|
| accept | same day | accept the invitation (or ignore it, with a reason) |
| thank_qualify | within 24 hours | thank-you plus one qualifying question |
| score | ongoing | engaged commenters on Dorian's posts are scored as warm leads |

## Stop conditions

Stop the sequence and draft nothing further when any of these is true:

- they replied (any reply moves them to inbox triage, see `li-inbox-triage`),
- they said "not interested", no, or stop (add to suppression),
- the day_10 step went out,
- they're in an active email sequence for the same campaign,
- a send came back `target_blocked`.

`send_linkedin_message` takes `stop_if_replied_after`: set it to the time of the last outbound message in the thread so a reply that lands between approval and send cancels the follow-up on the server side too.

## Finding who is due

Each morning, li-signals lists who's due a step: newly accepted connections (from `get_my_latest_linkedin_connection_requests` state and `get_my_latest_linkedin_conversations`), and people whose last step was 4 or 10 days ago (from earlier ledgers' executed items with a `sequence` field, cross-checked against the CRM). Due is a candidate for the batch, not a send.

## Withdrawals

Wednesday hygiene: requests pending over 21 days become `withdraw` items. A withdrawn request can't be resent to the same person for 21 days, so withdraw only when the lane no longer wants that connection soon.
