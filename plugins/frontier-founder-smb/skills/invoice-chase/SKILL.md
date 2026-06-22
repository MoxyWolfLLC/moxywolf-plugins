---
name: invoice-chase
version: 0.2.0
description: >
  Drafts overdue-invoice reminder emails from QuickBooks and Stripe data,
  matched to each customer's payment history and tone (gentle for good customers,
  firm for repeat late payers). Sends via Stripe with owner approval;
  non-Stripe invoices queue as mail drafts. Use when the user asks
  "who owes me money," mentions overdue invoices, or wants to follow up
  on unpaid invoices.
---

# Invoice Chase

## Quick start

Pull the AR aging report, score each customer by payment history, draft a tone-matched reminder for each overdue invoice, and present them to the owner. Nothing sends until the owner says so.

```
User: "who owes me money"
→ Pull AR aging from QuickBooks
→ Cross-reference Stripe settlements (last 14 days)
→ Score each customer: good-payer / occasionally-late / repeat-late
→ Draft tone-matched reminders
→ Show summary table + drafts. Wait for "send these."
```

## Setup (first run only)

Ask the owner two questions before running for the first time:

1. **Mail connector**: "Do you use Gmail or Apple Mail for drafts?" — store the answer; use it for all non-Stripe draft queuing.
2. **Stripe**: "Do you use Stripe for invoicing? I can include Stripe invoices in the overdue sweep." — if yes, pull Stripe overdue invoices alongside QuickBooks.

Do not ask again on subsequent runs.

## Workflow

1. **Pull overdue receivables.** Query QuickBooks AR aging for all invoices more than 1 day past due. If Stripe is enabled (owner confirmed at setup), also pull Stripe overdue invoices.

2. **Cross-reference payment history.** For each overdue customer, query Stripe for settled transactions using these parameters:
   - `transaction_status: S` (settled only — filters out pending and denied transactions that inflate result size and increase rate-limit risk)
   - Date window: **last 7 days** ending today (not 14 or 30 — wider windows are the primary cause of Stripe 429 rate limit errors)

   **If Stripe returns a 429 rate limit error:**
   - Retry once immediately with a **3-day window** instead.
   - If the retry also returns 429, skip the Stripe cross-reference entirely for this run. Flag all customers in the batch as "Stripe unavailable — verify manually" in the summary table. Proceed to scoring using QuickBooks history only. Do not silently drop the caveat.

   If a customer shows a settled payment within the query window, flag as "possibly paid — verify" and exclude from the draft queue.

3. **Score each customer.** Read [reference/tone-matching.md](reference/tone-matching.md) for scoring logic. Result: `good-payer`, `occasionally-late`, or `repeat-late`.

4. **Draft reminder emails.** One email per customer — consolidate multiple overdue invoices into one email. Match tone to score. See [reference/examples/gentle-reminder.md](reference/examples/gentle-reminder.md) and [reference/examples/firm-reminder.md](reference/examples/firm-reminder.md).

5. **Present drafts to owner.** Show a summary table first:

   | Customer | Amount Due | Days Late | Tone | Send via |
   |---|---|---|---|---|
   | Acme Corp | $1,200 | 18 days | Gentle | Stripe |
   | Smith LLC | $450 | 47 days | Firm | Gmail draft |

   Then show each draft email in full. Wait for owner to say "send these" or approve individually.

6. **Send or queue — only after the Release Owner gate clears.**

   **Release Owner gate (high-stakes).** Before sending the invoice reminder, present the exact content and the recipient, amount, or target, then stop. Do not proceed until one named human approves with their initials and the date. Record the decision to the shared gate log: run `python3 "Taskade/_Shared Files/_gate-log/record_decision.py" --skill frontier-founder-smb:invoice-chase --tier high-stakes --action "<summary>" --target "<recipient/amount/target>" --decision signed|stopped|overridden|edited --approver "<named human>" --requested-at <ISO-8601>` (one row per decision; never edit past rows). Roll up override rate and response time anytime with `override_report.py`. Never auto-approve, and never sign on the owner's behalf. Watch the override rate over time; a low override rate signals rubber-stamping.

   - Stripe invoices: send the reminder via Stripe.
   - Non-Stripe invoices: queue as a draft in the owner's configured mail app.
   - Never send without explicit approval.

7. **Report what happened.** List what was sent, what was queued as draft, and what was flagged (possibly paid, excluded).

## Approval gates

- **Never send or queue a draft without explicit owner approval.** Present all drafts first; wait for the go-ahead.
- **Never include a customer who paid in the last 14 days.** Flag as "possibly paid — verify" instead.
- **Never send to a customer not in the QuickBooks AR report** (or Stripe, if enabled). No reminders from memory alone.
- **One approval covers one batch.** Adding a customer or changing a draft after approval starts a new round.

## Reference

- [reference/tone-matching.md](reference/tone-matching.md) — scoring logic, tone guidelines, subject line formulas
- [reference/gotchas.md](reference/gotchas.md) — known failure modes
- [reference/examples/gentle-reminder.md](reference/examples/gentle-reminder.md) — good-payer email example
- [reference/examples/firm-reminder.md](reference/examples/firm-reminder.md) — repeat-late-payer email example
