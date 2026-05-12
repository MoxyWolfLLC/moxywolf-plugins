# Feature Gating Matrix

Structured approach to deciding which features belong in which tier.

## The Gating Framework

For each feature, answer these questions:

### 1. Is this table stakes?
"Would removing this feature make the product no longer recognizable as [product category]?"

If YES → Include in **all tiers** (including free)

Examples for a compliance tool:
- View STIG checklists → table stakes
- Basic search → table stakes
- Export a single checklist → table stakes

### 2. Is this a differentiator?
"Does this feature make us distinctly better than alternatives?"

If YES → Include in **paid tiers** (starter and above)

Examples:
- Automated compliance scoring → differentiator
- Multi-framework mapping → differentiator
- Custom rule creation → differentiator

### 3. Is this a multiplier?
"Does this feature become more valuable as usage/team size grows?"

If YES → Include in **higher tiers** (pro and above)

Examples:
- Team collaboration features → multiplier
- Bulk operations → multiplier
- Advanced automation/workflows → multiplier
- API access → multiplier
- Custom integrations → multiplier

### 4. Is this an enterprise gate?
"Do large organizations require this for procurement/compliance/governance reasons?"

If YES → Include in **enterprise tier** only

Examples:
- SSO/SAML → enterprise gate
- SCIM provisioning → enterprise gate
- Audit logging → enterprise gate
- Data residency options → enterprise gate
- Custom SLAs → enterprise gate
- Dedicated support → enterprise gate
- Role-based access control (advanced) → enterprise gate

## Feature-Tier Matrix Template

```markdown
| Feature | Free | Starter | Pro | Enterprise | Gate Type |
|---------|------|---------|-----|------------|-----------|
| [Core feature 1] | Y | Y | Y | Y | Table stakes |
| [Core feature 2] | Y | Y | Y | Y | Table stakes |
| [Paid feature 1] | - | Y | Y | Y | Differentiator |
| [Paid feature 2] | - | Y | Y | Y | Differentiator |
| [Scale feature 1] | - | - | Y | Y | Multiplier |
| [Scale feature 2] | - | - | Y | Y | Multiplier |
| [Enterprise feat 1] | - | - | - | Y | Enterprise gate |
| [Enterprise feat 2] | - | - | - | Y | Enterprise gate |
```

## Limit-Based Gating (Alternative to Feature Gating)

Instead of removing features, limit their usage:

```markdown
| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| Assets managed | 5 | 50 | 500 | Unlimited |
| API calls/month | 100 | 10K | 100K | Unlimited |
| Team members | 1 | 5 | 25 | Unlimited |
| Reports/month | 3 | 20 | Unlimited | Unlimited |
| Data retention | 30 days | 1 year | 3 years | Custom |
| Support | Community | Email | Priority | Dedicated |
```

**When to use limits vs. feature gates:**
- Use **limits** when the feature itself is valuable at any tier but scales with commitment
- Use **feature gates** when the feature represents a distinct use case or buyer need
- Combine both for maximum flexibility

## The "Upgrade Trigger" Test

For each tier boundary, identify the natural trigger that pushes a customer to upgrade:

- **Free → Starter**: "I need to manage more than 5 assets" or "I need team access"
- **Starter → Pro**: "I need automation" or "I need API access" or "My team grew past 5"
- **Pro → Enterprise**: "I need SSO" or "I need a custom SLA" or "I need 100+ seats"

If you can't articulate a clear upgrade trigger at each boundary, the gating is wrong. Every tier boundary should have a moment where the customer says "I've outgrown this tier."

## Anti-Patterns to Avoid

1. **Gating basic functionality**: Don't put search, export, or basic reporting behind a paywall. It feels punitive.
2. **Too many gates**: If your comparison table has 50 rows, it's overwhelming. Aim for 8-12 differentiating features across tiers.
3. **Security features as upsell**: Basic security (2FA, encryption at rest) should be in every tier. Advanced security (SSO, audit logs, SCIM) can be enterprise.
4. **Support as the only differentiator**: If the only difference between tiers is support level, you need better feature gating.
5. **Hiding the value**: The feature that makes your product special shouldn't be in the enterprise tier. It should be in Starter or Pro where most customers can access it.
