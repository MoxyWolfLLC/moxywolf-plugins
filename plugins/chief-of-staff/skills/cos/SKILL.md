---
name: cos
description: "Hand an ask to the Chief of Staff: it routes the ask to the right department agents, runs them, checks what they return, and brings back the result, a proposal or a decision memo. Use for any business ask that belongs to finance, people, IT, security, the PMO, operations, strategy or customer experience. Usage: /cos <ask>"
---

# /cos

1. Load `chief-of-staff:chief-of-staff` and follow its reading order. If the context card is missing, stop the work, write the log entry (step 7) with outcome `incomplete`, and say so.
2. Classify the ask against the roster. Name the departments and the reason for each, or name the non-department route from "What the eight don't cover." If an ask spans a settled overlap, apply the ruling in "Where the lines fall."
3. Write the success criteria: the two to four things a good answer has to settle.
4. Dispatch. Send independent departments in parallel. Each gets the context card's path, the ask and the criteria.
5. Check each result against the return contract, then against the criteria. If a result touches identity, secrets, customer data or an outside integration, send it to security.
6. Act on the authority table. Do autonomous actions. Show proposals and wait. Turn escalations into a decision memo and stop acting.
7. Append the decision-log entry. This step runs on every exit, including a stop at step 1 and an escalation at step 6. Stopping ends the work, not the record.
8. Report as the manual says: the outcome first, then the counts, then what was and wasn't checked.
