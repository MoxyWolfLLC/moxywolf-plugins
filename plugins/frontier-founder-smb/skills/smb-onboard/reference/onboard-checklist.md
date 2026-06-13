# Onboard checklist — FFSMB

## Connector priority matrix

Map the owner's stated top headache to the first two connectors to wire up.

| Top headache | Connect first | Connect second | Why |
|---|---|---|---|
| Money / cash / "am I making enough" | QuickBooks | Stripe | Cash position + revenue in one view |
| Customers / sales / "need more business" | Clarify | Stripe | Pipeline + what's actually closing |
| Getting paid / "people owe me" | Stripe | QuickBooks | Invoices + reconciliation |
| Scheduling / inbox overload | Gmail | Google Calendar | Triage + booking |
| Organized / "everything's a mess" | Clarify | QuickBooks | Customers + books, the two systems of record |

Connect **one at a time**. Never ask the owner to authenticate two simultaneously.

## Connector-to-recipe (the first "aha" run)

| First connector | Run this recipe | Proves |
|---|---|---|
| QuickBooks | `/month-heads-up` | "It knows my cash position" |
| Stripe | `/sales-brief` | "It sees what's selling" |
| Clarify | `/call-list` | "It tells me who to call today" |
| Gmail | `/monday-brief` | "It triaged my week" |

## The five interview questions

Ask one at a time, conversationally. Wait for the full answer before the next.

1. **Industry / what you do** — "In a sentence, what does your business do?"
2. **Size** — "Just you, or do you have a team? Roughly how many customers?"
3. **Top three headaches** — "What are the three things that eat your time or worry you most?"
4. **Tools you already run** — "What do you use today for money, customers, and email?"
5. **What 'a good week' looks like** — "When a week goes well, what happened?"

Compress to 1, 3, 4 only if the owner is pressed for time. Never fewer than three.

## Business-context storage format

Write under the heading `## Business context` in the Cowork session memory directory:

```markdown
## Business context
- Industry: {one line}
- Size: {solo / team of N}; {~N customers}
- Top headaches: {1}, {2}, {3}
- Tools: CRM={Clarify/other}, Payments={Stripe/other}, Accounting={QuickBooks/other}, Email={Gmail/other}
- A good week: {their words}
- Weekly check-in: {phrase}, {day}
- Onboarded: {YYYY-MM-DD}
```

Show the draft and get explicit approval before writing. If a `## Business context` block already exists, show current vs. proposed and update only changed fields.
