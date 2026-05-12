# Completion Promises Reference

All skills must emit these promises for Ralph Loop tracking.

## Code Analysis Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| code-review-pro | `SECURITY_ANALYSIS_COMPLETE` | Security scan finished |
| code-review-pro | `PERFORMANCE_ANALYSIS_COMPLETE` | Performance analysis done |
| code-review-pro | `CODE_QUALITY_COMPLETE` | Quality metrics generated |
| regex-visual-debugger | `REGEX_AUDIT_COMPLETE` | All patterns analyzed |

## Documentation Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| technical-writer | `DOC_GAPS_IDENTIFIED` | Gap analysis complete |
| technical-writer | `DOCUMENTATION_GENERATED` | Missing docs created |
| technical-writer | `ARCHITECTURE_DOCUMENTED` | Diagrams created |
| api-documentation-writer | `API_DOCS_AUDITED` | Endpoint audit complete |

## Architecture Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| database-schema-designer | `SCHEMA_ANALYZED` | Schema analysis complete |
| database-schema-designer | `SCHEMA_OPTIMIZATIONS_COMPLETE` | Optimization SQL ready |

## Testing Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| webapp-testing | `COVERAGE_ANALYZED` | Coverage report generated |
| webapp-testing | `CRITICAL_TESTS_CREATED` | Critical path tests written |
| webapp-testing | `TESTS_EXECUTED` | All tests run |

## UI/UX Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| color-palette-extractor | `ACCESSIBILITY_AUDITED` | WCAG report generated |
| screenshot-to-code | `UI_CONSISTENCY_CHECKED` | Consistency report done |
| screenshot-to-code | `UI_RECOMMENDATIONS_COMPLETE` | Recommendations documented |
