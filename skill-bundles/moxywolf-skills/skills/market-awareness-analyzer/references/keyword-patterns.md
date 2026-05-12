# Keyword Generation Patterns

## Stage 2: Problem-Aware Keywords

People at this stage feel pain but don't know solutions exist.

### Patterns
- "why [symptom]"
- "how to fix [problem]"
- "what causes [pain]"
- "[problem] taking forever"
- "frustrated with [pain point]"
- "[consequence] keeps happening"
- "help with [symptom]"

### From PR/FAQ Elements
- Extract symptoms from problem statement
- Extract consequences from problem statement
- Use buyer/user daily pain points

### Examples
```
Problem: "STIG compliance is time-consuming and error-prone"

Generated Stage 2 keywords:
- "why is STIG compliance so slow"
- "STIG audit taking forever"
- "failed STIG audit"
- "manual STIG checklist errors"
- "how to speed up ATO process"
```

## Stage 3: Solution-Aware Keywords

People at this stage know solutions exist but are shopping categories.

### Patterns
- "best [solution category]"
- "[solution type] tools"
- "[solution category] software"
- "tools for [outcome]"
- "how to automate [process]"
- "[solution type] comparison"
- "alternatives to [manual method]"

### From PR/FAQ Elements
- Extract solution category from solution description
- Extract outcome from benefits
- Extract differentiators for comparison queries

### Examples
```
Solution: "Automated STIG compliance scanning and remediation"

Generated Stage 3 keywords:
- "best STIG automation tools"
- "compliance automation software"
- "STIG scanning tools comparison"
- "automated compliance checklist"
- "RMF automation solutions"
```

## Stage 4: Product-Aware Keywords

People at this stage know your product and are evaluating.

### Patterns
- "[product name] vs [competitor]"
- "[product name] review"
- "[product name] pricing"
- "[product name] alternatives"
- "is [product name] worth it"
- "[product name] for [specific use case]"

### From PR/FAQ Elements
- Use product name directly
- Combine with competitors mentioned in FAQ
- Combine with specific use cases from benefits

### Examples
```
Product: STIGViewer

Generated Stage 4 keywords:
- "STIGViewer vs SCAP"
- "STIGViewer review"
- "STIGViewer pricing"
- "STIGViewer for AWS"
- "STIGViewer alternatives"
```

## Keyword Validation Criteria

After generating, validate each keyword:

| Criterion | Check |
|-----------|-------|
| Searchable | Would someone type this in Google? |
| Specific | Not too broad or generic? |
| Intent-aligned | Matches the awareness stage? |
| Actionable | Can you create content for this? |

## Volume Priority

When search tools return volume signals:

1. High volume + low competition = Priority target
2. High volume + high competition = Require differentiation
3. Low volume + high intent = Niche opportunities
4. Low volume + low intent = Skip unless strategic
