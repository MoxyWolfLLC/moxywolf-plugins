---
description: Scrape and analyze a competitor's pricing page
argument-hint: <competitor-url-or-name>
---

Deep-dive a single competitor's pricing structure and extract actionable intelligence.

1. Read the competitor matrix template at `${CLAUDE_PLUGIN_ROOT}/skills/pricing-research/references/competitor-matrix-template.md` for the capture format.

2. Take the competitor URL or name from $ARGUMENTS. If a name is provided without a URL, search for their pricing page.

3. Scrape and analyze the competitor's pricing page. Use Rube/Apify tools if available, otherwise use web search and browsing tools. Capture:
   - All tier names and published price points (monthly and annual)
   - Value metric (what they charge per)
   - Feature gating across tiers (what's in each tier)
   - Free tier details and limitations
   - Enterprise pricing approach (published vs. "Contact us")
   - Add-ons or premium features sold separately
   - Pricing page UX details (toggle design, recommended tier, CTAs, social proof)

4. Search for review intelligence:
   - G2 or Capterra rating and review count
   - Any reviews mentioning pricing, value, or cost
   - Reddit or forum discussions about their pricing

5. Deliver the analysis in the competitor matrix format, plus:
   - **Pricing strategy assessment**: Are they value-based, cost-plus, competitive, or penetration priced?
   - **Strengths**: What do they do well on their pricing page?
   - **Weaknesses**: Where are the gaps or opportunities?
   - **Implications for us**: How should this inform our pricing decisions?

Save the output to `competitor-scan-[name]-[date].md` in the current working directory.
