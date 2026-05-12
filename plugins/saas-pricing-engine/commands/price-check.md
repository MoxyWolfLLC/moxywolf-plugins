---
description: Quick-check a price point against market data
argument-hint: <product-name> <proposed-price>
---

Run a rapid pricing sanity check for the given product and proposed price point.

1. Read the pricing-research skill at `${CLAUDE_PLUGIN_ROOT}/skills/pricing-research/SKILL.md` for methodology context.

2. Take the product name and proposed price from $ARGUMENTS. If not provided, ask the user for:
   - Product or tier name
   - Proposed monthly price point
   - Value metric (per seat, per asset, per API call, etc.)

3. Conduct a quick competitive scan:
   - Search the web for 3-5 direct competitors' pricing pages
   - Extract their comparable tier price points
   - Identify the market price range (floor, median, ceiling)

4. Evaluate the proposed price against:
   - **Market positioning**: Where does this price fall relative to competitors? (below market, at market, premium, super-premium)
   - **Value metric alignment**: Is the value metric consistent with the market?
   - **Psychological pricing**: Does the number work psychologically? ($49 vs $50 vs $47)
   - **10x value test**: Can you articulate 10x the value at this price?
   - **Tier spacing**: If part of a tier structure, is the spacing between tiers 2-3x?

5. Deliver a concise verdict:
   - UNDERPRICED / WELL-POSITIONED / PREMIUM / OVERPRICED
   - Key evidence points (2-3 bullets)
   - Recommended adjustment if any
   - Confidence level (high/medium/low based on data quality)

Keep the output brief — this is a quick check, not a full research package.
