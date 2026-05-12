# Willingness-to-Pay Research Frameworks

Structured survey instruments and analysis methodologies for pricing research.

## Van Westendorp Price Sensitivity Meter (PSM)

### The Survey

Ask each respondent these four questions about your product (after showing them the feature set):

1. **Too Expensive**: "At what monthly price would [Product] be so expensive that you would NOT consider buying it, regardless of its quality?"
2. **Expensive but Acceptable**: "At what monthly price would you consider [Product] to be expensive, but you would still consider buying it?"
3. **Good Value**: "At what monthly price would you consider [Product] to be a bargain — a great buy for the money?"
4. **Too Cheap**: "At what monthly price would [Product] be so cheap that you would question its quality and not consider it?"

### How to Administer
- **Sample size**: Minimum 100 respondents for reliable curves; 200+ preferred
- **Respondent profile**: Must match your ICP; screen for decision-making authority and budget
- **Context**: Show the product/feature set before asking price questions
- **Format**: Open-ended dollar amount (not multiple choice — you want their number, not your anchors)
- **Validation**: Too Expensive > Expensive > Good Value > Too Cheap (flag and exclude inverted responses)

### Analysis
Plot cumulative distribution curves for each question. The intersections reveal:

- **Point of Marginal Cheapness (PMC)**: "Too Cheap" crosses "Expensive" — below this, you lose credibility
- **Point of Marginal Expensiveness (PME)**: "Too Expensive" crosses "Good Value" — above this, you lose too many buyers
- **Optimal Price Point (OPP)**: "Too Cheap" crosses "Too Expensive" — minimum price resistance
- **Indifference Price Point (IDP)**: "Expensive" crosses "Good Value" — the price most respondents see as "fair"

**Acceptable Price Range**: PMC to PME. Your price should fall within this band.

### For SaaS/API Products
Adapt the questions per value metric:
- "At what price per seat per month..."
- "At what price per 10,000 API calls..."
- "At what annual subscription price..."

Run separate PSMs for each candidate value metric to compare.

## Gabor-Granger Direct Pricing

### The Survey

Show a price point and ask: "Would you subscribe to [Product] at $X/month?"

Start at a mid-range price and adjust:
- If YES → increase price in the next question
- If NO → decrease price in the next question

Typical sequence (5-7 price points):
$19/mo → $29/mo → $49/mo → $79/mo → $99/mo → $149/mo → $199/mo

### How to Administer
- **Sample size**: 50-100 per segment minimum
- **Format**: Yes/No at each price point (no "maybe")
- **Order**: Randomize starting price across respondents to avoid anchoring bias
- **Context**: Show specific tier/feature set being priced

### Analysis
Calculate acceptance rate at each price point. Plot the demand curve.

- **Revenue-maximizing price**: Price × Acceptance Rate = Revenue. Find the maximum.
- **Volume-maximizing price**: Lowest price with acceptable margin
- **Profit-maximizing price**: (Price - Cost) × Acceptance Rate = Profit. Find the maximum.

## Conjoint Analysis (Feature-Price Tradeoffs)

### When to Use
When you need to understand which features justify which price premiums. More complex to design and analyze but reveals the deepest insights.

### Survey Design
Create choice cards with 3-4 options, each combining:
- Feature bundle (which features are included)
- Price point
- Brand (if testing against competitors)

Respondents choose their preferred option from each card. Across 8-12 cards, statistical analysis reveals the implicit value of each feature and price sensitivity.

### Simplified Version for Small Teams
If full conjoint is too heavy, use a **MaxDiff** (best-worst scaling):

Show 4-5 features at a time. Ask:
- "Which of these features is MOST important to you?"
- "Which is LEAST important?"

Repeat across 6-8 sets. This ranks features by perceived value without the full conjoint apparatus.

### Analysis Outputs
- **Part-worth utilities** for each feature and price level
- **Willingness-to-pay** for individual features
- **Optimal bundle** at each price point
- **Market simulator** — predict share at different price/feature combinations

## Quick-and-Dirty Pricing Research (No Budget for Formal Surveys)

### Method 1: Customer Interview Protocol
Interview 10-15 current users or prospects:

1. "What are you currently paying for [competitor/alternative]?"
2. "If this product didn't exist, what would you do instead? How much would that cost?"
3. "What's the most valuable thing this product does for you? What would it cost to do that manually?"
4. "If I told you the price was $X/month, what's your gut reaction?"
5. "At what price would you say 'that's too much' and look for alternatives?"

### Method 2: Pricing Page A/B Test
Show different prices to different visitors and measure:
- Click-through to signup/trial
- Trial-to-paid conversion
- Revenue per visitor

Requires enough traffic for statistical significance (typically 1,000+ visitors per variant).

### Method 3: Anchor-and-Adjust in Sales Calls
During demos or sales calls, mention a price and observe the reaction:
- No reaction → probably could charge more
- Slight hesitation → in the right range
- Sticker shock → too high, but probe for their expected range
- Enthusiasm → definitely underpriced
