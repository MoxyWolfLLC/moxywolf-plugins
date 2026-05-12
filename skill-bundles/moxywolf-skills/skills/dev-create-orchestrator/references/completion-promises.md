# Completion Promises Reference

All skills must emit these promises for Ralph Loop tracking.

## Design Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| screenshot-to-code | `UI_SPECS_COMPLETE` | Component specs extracted |
| screenshot-to-code | `SCREENS_CONVERTED` | All screens converted to code |
| color-palette-extractor | `DESIGN_TOKENS_COMPLETE` | Palette exported |
| canvas-design | `VISUAL_ASSETS_COMPLETE` | Assets exported |

## Architecture Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| database-schema-designer | `SCHEMA_COMPLETE` | Schema designed |
| mcp-builder | `INTEGRATIONS_PLANNED` | MCP spec complete |

## Implementation Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| artifacts-builder | `COMPONENTS_BUILT` | React components done |
| artifacts-builder | `LOGIC_IMPLEMENTED` | Business logic complete |

## Documentation Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| api-documentation-writer | `API_DOCS_COMPLETE` | OpenAPI spec generated |
| technical-writer | `README_COMPLETE` | README created |
| technical-writer | `USER_GUIDE_COMPLETE` | User guide done |

## Testing Skills

| Skill | Promise | Emitted When |
|-------|---------|--------------|
| webapp-testing | `TESTS_COMPLETE` | Test suite created |
| code-review-pro | `SECURITY_AUDIT_COMPLETE` | Security audit done |
| code-review-pro | `OPTIMIZATION_COMPLETE` | Optimizations documented |
