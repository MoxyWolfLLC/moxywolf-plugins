# SaaS Pricing Engine

End-to-end pricing research, modeling, and copywriting for SaaS products and API gateways. Built for MoxyWolf's STIGViewer and content API products, but applicable to any B2B SaaS pricing workflow.

## Components

### Skills (3)

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **pricing-research** | Competitive intelligence, market benchmarks, WTP research design | First — before any pricing decisions |
| **pricing-modeler** | Tier architecture, value metrics, price points, revenue projections | After research is complete |
| **pricing-copywriter** | Pricing page copy, FAQs, comparison tables, pricing communications | After model is defined |

### Commands (3)

| Command | Purpose |
|---------|---------|
| `/price-check <product> <price>` | Quick sanity check a price point against market data |
| `/competitor-scan <url-or-name>` | Deep-dive a single competitor's pricing structure |
| `/tier-builder [product]` | Interactive tier design session from scratch |

## Recommended Workflow

1. **Research first**: Run `pricing-research` or `/competitor-scan` to gather market intelligence
2. **Model second**: Use `pricing-modeler` or `/tier-builder` to design your tier structure
3. **Copy third**: Use `pricing-copywriter` to create customer-facing pricing content
4. **Validate**: Use `/price-check` anytime to gut-check specific price points

## Reference Materials

Each skill includes detailed reference files:

- **Competitor matrix template** — structured format for capturing competitor pricing data
- **API pricing patterns** — common models for API/developer tool pricing
- **WTP frameworks** — Van Westendorp, Gabor-Granger, and conjoint analysis survey instruments
- **Value metric decision tree** — guided flow for selecting what to charge per
- **Feature gating matrix** — framework for deciding what goes in each tier
- **API revenue model** — spreadsheet-ready formulas for API revenue projection
- **Pricing FAQ templates** — copy-ready FAQ entries by category
- **Compliance copy patterns** — defense/gov-specific language and tone guidance

## STIGViewer Context

This plugin includes specialized guidance for pricing compliance/GRC SaaS tools in the defense vertical, including:

- STIG/CMMC compliance tool competitive benchmarks
- Government procurement-friendly pricing structures
- Defense contractor buyer psychology
- FedRAMP/IL-level pricing premiums
- GSA Schedule and contract vehicle considerations
