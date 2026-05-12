# Value Metric Decision Tree

Walk through these questions to identify the best value metric for your product.

## Question 1: What does the customer actually value?

Think about the customer's perspective, not yours. The value metric should track with the *outcome* they care about.

- "I need to keep N systems compliant" → **per asset/system**
- "I need my team to collaborate on compliance" → **per seat**
- "I need to automate compliance checks" → **per scan/check or per API call**
- "I need a compliance platform for my org" → **per organization**
- "I need to serve content to my users" → **per content item or per API call**

## Question 2: How does usage naturally scale?

As customers get more value, what number goes up?

- More people use it → **per seat**
- More things are managed → **per asset/item**
- More operations are performed → **per API call/transaction**
- The organization grows → **per organization tier (S/M/L)**
- Nothing changes (same value at any scale) → **flat rate**

## Question 3: Can customers predict their cost?

Predictability matters enormously for B2B buyers who need budget approval.

| Metric | Predictability | Mitigation |
|--------|---------------|------------|
| Per seat | High | Seats are known and stable |
| Per asset | Medium-High | Asset count grows slowly, is knowable |
| Per API call | Low | Hard to predict usage; offer committed-use discounts |
| Flat rate | Very High | Fixed cost, no surprises |
| Per scan | Medium | Can estimate based on compliance cycle |
| Credit-based | Medium | Credits purchased upfront, usage varies |

If predictability is low, consider:
- Committed-use pricing (prepay for a volume, use what you need)
- Spending caps / alerts
- Tiered pricing with generous included quotas
- "Up to X" tiers instead of pure metering

## Question 4: Does it create perverse incentives?

Bad value metrics punish customers for using the product more:

- **Per seat** can discourage broad adoption ("let's share a login")
- **Per API call** can discourage integration and automation
- **Per query/search** can make users hesitate to explore
- **Per export** can feel punitive for basic functionality

Good value metrics scale with outcomes, not effort:

- **Per asset under management** — customer adds assets as their business grows
- **Per compliance framework** — customer adds frameworks as requirements expand
- **Per organization** with usage tiers — simple billing, scales with org size

## Question 5: What do competitors charge per?

If the entire market charges per seat, charging per API call requires extra justification. You CAN deviate from market convention, but you need a clear value story.

**Go with convention when**: The metric makes sense for your product too, and deviating would confuse buyers.

**Deviate when**: You have a fundamentally different value proposition that a different metric serves better, AND you can explain it clearly.

## Decision Matrix

Score each candidate metric 1-5 on these dimensions:

```
| Metric | Value Align | Predictable | Measurable | Growth-Friendly | Competitive | Simple | TOTAL |
|--------|-------------|-------------|------------|-----------------|-------------|--------|-------|
| [A]    |     /5      |     /5      |    /5      |       /5        |     /5      |   /5   |  /30  |
| [B]    |     /5      |     /5      |    /5      |       /5        |     /5      |   /5   |  /30  |
| [C]    |     /5      |     /5      |    /5      |       /5        |     /5      |   /5   |  /30  |
```

The highest score wins, but weight judgment over arithmetic — if a metric scores highest but has a fatal flaw in one dimension, it's not the answer.
