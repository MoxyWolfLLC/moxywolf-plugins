---
description: Interactively design a tier structure from scratch
argument-hint: [product-name]
---

Walk through an interactive tier design session that produces a complete, implementable tier architecture.

1. Read the pricing-modeler skill at `${CLAUDE_PLUGIN_ROOT}/skills/pricing-modeler/SKILL.md` and the feature gating matrix at `${CLAUDE_PLUGIN_ROOT}/skills/pricing-modeler/references/feature-gating-matrix.md` for framework context.

2. If a product name is provided in $ARGUMENTS, use it. Otherwise ask for:
   - Product name
   - Product category (SaaS, API, hybrid)
   - Target market (SMB, mid-market, enterprise, developer)

3. Guide the user through each decision point, using AskUserQuestion for structured input:

   **Step 1: Value Metric Selection**
   Present 3-4 candidate value metrics based on the product type. For each, explain pros/cons. Ask the user to pick one (or suggest their own).

   **Step 2: Tier Count and Names**
   Recommend a tier structure (typically Free + 3 paid tiers). Propose tier names that fit the product's brand voice. Get confirmation.

   **Step 3: Feature Gating**
   For each major feature area, ask: "Which tier should this live in?"
   Categorize features as: table stakes, differentiator, multiplier, or enterprise gate.
   Build the feature-by-tier matrix interactively.

   **Step 4: Price Points**
   Based on any available competitive data and the value metric, propose price points for each tier. Present the rationale. Get confirmation or adjustments.

   **Step 5: Limits and Quotas**
   For usage-based dimensions, propose limits per tier. Ensure each tier boundary has a clear upgrade trigger.

   **Step 6: API Pricing (if applicable)**
   If the product includes an API, design the API pricing layer — included quotas, overage rates, standalone API plans.

4. Compile the complete tier architecture into a structured document:

   ```
   # Tier Architecture: [Product Name]

   ## Value Metric: [selected metric]

   ## Tier Summary
   | | Free | [Tier 1] | [Tier 2] | Enterprise |
   |---|---|---|---|---|
   | Price (monthly) | $0 | $X | $X | Custom |
   | Price (annual) | $0 | $X | $X | Custom |
   | [Value metric] limit | X | X | X | Unlimited |
   | Seats | 1 | X | X | Unlimited |

   ## Feature Matrix
   [Complete feature-by-tier table]

   ## Upgrade Triggers
   [What pushes users from each tier to the next]

   ## API Pricing (if applicable)
   [API-specific pricing details]
   ```

5. Save to `tier-architecture-[product]-[date].md` in the current working directory.
