---
name: cos
description: "Hand an ask to the Chief of Staff: it routes the ask to the right department agents, runs them, checks what they return, and brings back the result, a proposal or a decision memo. Use for any business ask that belongs to finance, people, IT, security, the PMO, operations, strategy, customer experience, sales or marketing. Usage: /cos <ask>"
---

# /cos

1. Load `chief-of-staff:chief-of-staff` and follow its reading order. If the context card is missing, stop the work, write the log entry (step 7) with outcome `escalated (context card missing)`, and say so.
2. Classify the ask against the roster. Name the departments and the reason for each, or name the non-department route from "What the ten don't cover." If an ask spans a settled overlap, apply the ruling in "Where the lines fall." For a mixed ask, name the lead and the contributors.
3. Write the success criteria: the two to four things a good answer has to settle, each stated so it can be checked.
4. Dispatch. Send independent departments in parallel. Each gets the context card's path, the ask, the criteria, the authorized scope and the evidence you already hold.
5. Check each result against the return contract, then against the criteria. That's nine fields for sales-department and marketing-department, and four for the rest. If a result touches identity, secrets, customer data or an outside integration, send it to security. Until security has answered, the sensitive action is blocked.
6. Act on the authority table and the Release Owner Gate. Do autonomous actions. Show proposals and wait. Turn escalations and pending approvals into a decision memo and stop acting.
7. Append the decision-log entry. This step runs on every exit, including a stop at step 1 and an escalation at step 6. Stopping ends the work, not the record.
8. Report as the manual says: the outcome first, then the counts, then what was and wasn't checked.
