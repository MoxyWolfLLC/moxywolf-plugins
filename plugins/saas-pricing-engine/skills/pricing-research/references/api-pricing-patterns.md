# API & Developer Tool Pricing Patterns

Common pricing models for API gateways and developer-facing content services.

## Model 1: Tiered Request Volume

The most common API pricing model. Fixed monthly price includes a request quota; overage billed per-request.

```
Free:       1,000 requests/month     $0
Starter:    50,000 requests/month    $29/mo
Pro:        500,000 requests/month   $99/mo
Scale:      5,000,000 requests/month $499/mo
Enterprise: Unlimited                Custom
```

**When it works**: High-volume, low-value-per-request APIs (data lookup, content delivery, search)
**Watch out for**: Unpredictable costs scare away developers; need clear overage pricing

## Model 2: Pay-Per-Request (Pure Usage)

No tiers. Pay only for what you use with volume discounts at thresholds.

```
First 10K requests:    $0.01 per request
10K - 100K:            $0.005 per request
100K - 1M:             $0.002 per request
1M+:                   $0.001 per request
```

**When it works**: APIs where usage varies wildly between customers; AWS-style infrastructure
**Watch out for**: Revenue unpredictability; hard to forecast; bill shock alienates small users

## Model 3: Flat Rate + API Access

SaaS platform with API as a feature of higher tiers, not a standalone product.

```
Starter:    Web app only                       $19/mo
Pro:        Web app + API (10K calls/mo)       $49/mo
Business:   Web app + API (100K calls/mo)      $149/mo
Enterprise: Web app + unlimited API            Custom
```

**When it works**: When the API extends a core SaaS product (not standalone)
**Watch out for**: Gating API behind higher tiers can frustrate developer users

## Model 4: Seat + Usage Hybrid

Per-seat pricing for the platform, usage-based for API/automation features.

```
Platform:   $15/seat/month (includes web app)
API calls:  $0.005 per call (billed monthly)
Automation: $0.02 per automated action
Storage:    $0.10 per GB/month
```

**When it works**: When different value streams need different metrics
**Watch out for**: Billing complexity; hard to predict monthly cost

## Model 5: Credit-Based

Customers buy credits; different operations consume different credit amounts.

```
100 credits:    $10   ($0.10/credit)
1,000 credits:  $80   ($0.08/credit)
10,000 credits: $500  ($0.05/credit)

Simple query: 1 credit
Complex query: 5 credits
Bulk export:  10 credits
```

**When it works**: APIs with operations of varying computational cost
**Watch out for**: Cognitive overhead for users; need clear credit-to-action mapping

## API Pricing Benchmarks by Vertical

### Security/Compliance APIs
- NVD API: Free (government), rate-limited
- Shodan: $59-$399/mo (enterprise custom)
- VirusTotal: Free tier + $X per premium query
- Qualys API: Bundled with platform ($2K-$20K/year)

### Content/Document APIs
- Contentful: $300/mo (Pro) includes API
- Sanity: Free tier + $99/mo, usage-based beyond
- Strapi Cloud: $29-$499/mo, API calls included per tier

### Developer Platforms
- Stripe: 2.9% + $0.30 per transaction
- Twilio: Pure per-message/per-minute
- SendGrid: Tiered volume (Free - $89.95/mo - custom)
- Algolia: Per-search-request + per-record pricing

## Key Design Decisions for API Pricing

### Rate Limiting Strategy
- **Hard limits**: Requests blocked after quota. Simple but frustrating.
- **Soft limits with overage**: Continue serving but charge overage. Better UX, revenue upside.
- **Throttling**: Slow down requests instead of blocking. Good for non-critical APIs.

### Authentication & Key Management
- Free tier: API key only, rate-limited
- Paid tiers: OAuth2, multiple keys, IP whitelisting
- Enterprise: SSO integration, key rotation policies, audit logs

### Developer Experience Pricing Signals
Developers evaluate APIs on:
1. **Free tier generosity** — can I build and test without paying?
2. **Pricing transparency** — can I estimate my bill before committing?
3. **Overage predictability** — will I get bill-shocked?
4. **Scale economics** — does per-unit cost decrease meaningfully at volume?
5. **No credit card for free tier** — reduces friction dramatically

### SLA-Based Pricing Tiers
For enterprise/compliance customers, SLAs justify premium pricing:
- **99.9% uptime**: Standard tier
- **99.95% uptime**: Premium (+25-50%)
- **99.99% uptime**: Enterprise (+100-200%)
- **Dedicated instance**: Custom pricing
