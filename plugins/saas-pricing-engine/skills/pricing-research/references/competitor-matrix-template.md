# Competitor Pricing Matrix Template

Use this template to capture structured pricing data for each competitor.

## Per-Competitor Entry

```markdown
### [Competitor Name]
**URL**: [pricing page URL]
**Last Updated**: [date]
**Category**: Direct / Adjacent / API-only

#### Tiers

| Tier | Monthly Price | Annual Price | Value Metric | Key Limits |
|------|--------------|--------------|--------------|------------|
| Free | $0 | $0 | — | [limits] |
| Starter | $X | $X | per seat/per X | [limits] |
| Pro | $X | $X | per seat/per X | [limits] |
| Enterprise | Contact | Contact | custom | [limits] |

#### Feature Gating
| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| [Feature 1] | Y/N | Y/N | Y/N | Y/N |
| [Feature 2] | Y/N | Y/N | Y/N | Y/N |

#### Value Metric Details
- **What they charge per**: [seats, API calls, assets, scans, etc.]
- **Why this metric works for them**: [explanation]
- **Upgrade triggers**: [what forces users to the next tier]

#### Pricing Page UX Notes
- Toggle type: [monthly/annual switch style]
- Recommended tier highlight: [which tier, how highlighted]
- Social proof: [logos, testimonials, case studies]
- CTA language: [exact button text per tier]
- FAQ topics: [what questions they address]

#### Review Intelligence
- G2 rating: [X.X/5, N reviews]
- Common price complaints: [themes]
- Common value praise: [themes]
- Switching-from mentions: [what tools people left]
- Switching-to mentions: [what tools people leave for]
```

## Aggregation Table

After capturing individual competitors, compile into a single comparison:

```markdown
## Market Pricing Overview

| Competitor | Lowest Paid | Mid Tier | Enterprise | Value Metric | Free Tier |
|-----------|-------------|----------|------------|--------------|-----------|
| [Name] | $X/mo | $X/mo | Contact | [metric] | Yes/No |
| [Name] | $X/mo | $X/mo | $X/mo | [metric] | Yes/No |

### Price Distribution
- **Floor**: $X/mo (lowest paid tier across all competitors)
- **Median**: $X/mo (mid-tier median)
- **Ceiling**: $X/mo (highest published price)
- **Enterprise range**: $X-$X/mo (where available)

### Value Metric Distribution
| Value Metric | # Competitors Using | Typical Range |
|-------------|-------------------|---------------|
| Per seat | X | $X-$X/seat/mo |
| Per API call | X | $X per 1K calls |
| Flat rate | X | $X-$X/mo |
| Usage-based | X | varies |
```

## Defense/Compliance Vertical Specifics

For STIGViewer and compliance tools, also capture:

```markdown
### Compliance-Specific Pricing Factors
- **FedRAMP certification premium**: [% above standard pricing]
- **IL4/IL5 hosting premium**: [additional cost]
- **GSA Schedule pricing**: [if listed]
- **Contract vehicle**: [SEWP, CIO-SP3, etc.]
- **Procurement-friendly features**: [PO acceptance, NET30/60, annual billing only]
- **Compliance certifications included**: [SOC2, FedRAMP, etc.]
```
