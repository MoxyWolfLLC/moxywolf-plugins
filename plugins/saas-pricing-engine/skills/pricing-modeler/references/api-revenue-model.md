# API Revenue Modeling Templates

Spreadsheet-ready formulas and models for projecting API gateway revenue.

## Model A: Tiered Volume Pricing

### Inputs
```
tier_1_price = Monthly price for Tier 1
tier_1_limit = API calls included in Tier 1
tier_2_price = Monthly price for Tier 2
tier_2_limit = API calls included in Tier 2
tier_3_price = Monthly price for Tier 3
tier_3_limit = API calls included in Tier 3
overage_rate = Price per additional API call beyond tier limit
```

### Customer Distribution Assumption
```
free_users = Total API users × 70%    (typical for developer APIs)
tier_1_users = Total API users × 15%
tier_2_users = Total API users × 10%
tier_3_users = Total API users × 4%
enterprise_users = Total API users × 1%
```

### Revenue Calculation
```
MRR = (tier_1_users × tier_1_price)
    + (tier_2_users × tier_2_price)
    + (tier_3_users × tier_3_price)
    + (enterprise_users × avg_enterprise_price)
    + overage_revenue

overage_revenue = SUM(users where calls > tier_limit) × (excess_calls × overage_rate)
```

### Growth Modeling
```
Month N users = Month (N-1) users × (1 + monthly_growth_rate)
Monthly growth rate (early stage): 10-20%
Monthly growth rate (scaling): 5-10%
Monthly growth rate (mature): 2-5%

Conversion rate free→paid: 2-5% (month over month of new signups)
Expansion rate (tier upgrades): 3-8% of paid users per month
Churn rate by tier:
  - Tier 1: 5-8% monthly
  - Tier 2: 3-5% monthly
  - Tier 3: 1-3% monthly
  - Enterprise: 0.5-1% monthly
```

## Model B: Pay-Per-Request

### Inputs
```
price_per_request = Blended average (accounting for volume discounts)
avg_requests_per_user_month = Average API calls per active user per month
cost_per_request = Infrastructure cost per API call
```

### Revenue Calculation
```
Monthly Revenue = active_users × avg_requests_per_user_month × price_per_request
Gross Margin = (price_per_request - cost_per_request) / price_per_request
```

### Key Metric: Revenue Per API Call
```
Track: Revenue / Total API Calls = Effective Price Per Call
This should stay within 50-200% of your target price per call.
If it drops below 50%, your volume discounts are too aggressive.
If it exceeds 200%, you may be over-charging low-volume users.
```

## Model C: SaaS + API Hybrid

### Inputs
```
saas_mrr = MRR from SaaS subscriptions (all tiers)
api_calls_included = API calls included per SaaS tier
api_overage_rate = Price per call beyond included quota
api_standalone_plans = MRR from API-only customers
```

### Revenue Calculation
```
Total MRR = saas_mrr + api_overage_revenue + api_standalone_mrr

api_overage_revenue = SUM across all SaaS customers:
  MAX(0, actual_calls - included_calls) × api_overage_rate
```

### Breakeven Analysis
```
API infrastructure cost per month = servers + bandwidth + monitoring + support
Breakeven API calls = API infrastructure cost / price_per_request
Current API calls = [actual usage]
Margin = (Current API calls × price_per_request) - API infrastructure cost
```

## Unit Economics Dashboard

Track these metrics monthly:

```
| Metric | Month 1 | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|---------|----------|
| Total API Users | | | | |
| Paid API Users | | | | |
| Free-to-Paid Rate | | | | |
| API MRR | | | | |
| Avg Revenue Per User | | | | |
| API Calls Served | | | | |
| Revenue Per 1K Calls | | | | |
| API Gross Margin | | | | |
| API CAC | | | | |
| API LTV | | | | |
| LTV:CAC Ratio | | | | |
```

Target LTV:CAC ratio: 3:1 minimum for sustainable growth.
