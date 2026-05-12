# Phase Task Definitions

Detailed task breakdowns for each phase of the code creation workflow.

## Phase 1: Requirements & Design

### Task 1.1: Extract UI Requirements
- **Skill:** screenshot-to-code
- **Input:** UI mockups, screenshots, or descriptions
- **Max Iterations:** 3
- **Promise:** `UI_SPECS_COMPLETE`
- **Criteria:** Component hierarchy documented, layout structure defined, responsive breakpoints specified

### Task 1.2: Generate Design Tokens
- **Skill:** color-palette-extractor
- **Input:** Previous handoff or brand assets
- **Max Iterations:** 2
- **Promise:** `DESIGN_TOKENS_COMPLETE`
- **Criteria:** Color palette exported, accessibility contrast verified, typography scale defined

### Task 1.3: Create Visual Assets
- **Skill:** canvas-design
- **Input:** Brand requirements
- **Max Iterations:** 3
- **Promise:** `VISUAL_ASSETS_COMPLETE`
- **Criteria:** Logo/icons created, brand guidelines documented
- **Skip if:** User has existing assets

---

## Phase 2: Architecture

### Task 2.1: Design Database Schema
- **Skill:** database-schema-designer
- **Input:** Data requirements, entity relationships
- **Max Iterations:** 3
- **Promise:** `SCHEMA_COMPLETE`
- **Criteria:** ERD generated, SQL/migrations created, indexes defined
- **Skip if:** No persistent data needed

### Task 2.2: Plan External Integrations
- **Skill:** mcp-builder
- **Input:** External API requirements
- **Max Iterations:** 4
- **Promise:** `INTEGRATIONS_PLANNED`
- **Criteria:** MCP server spec created, tool definitions documented
- **Skip if:** No external APIs needed

---

## Phase 3: Implementation

### Task 3.1: Build UI Components
- **Skill:** artifacts-builder
- **Input:** Design specs from Phase 1
- **Max Iterations:** 5
- **Promise:** `COMPONENTS_BUILT`
- **Criteria:** All components exist, responsive, state management implemented

### Task 3.2: Implement Business Logic
- **Skill:** artifacts-builder
- **Input:** Previous handoff
- **Max Iterations:** 5
- **Promise:** `LOGIC_IMPLEMENTED`
- **Criteria:** API integrations working, data flow complete, error handling

### Task 3.3: Convert Additional Screens
- **Skill:** screenshot-to-code
- **Input:** Additional mockups
- **Max Iterations:** 4
- **Promise:** `SCREENS_CONVERTED`
- **Criteria:** All screens implemented, consistent with design system

---

## Phase 4: Documentation

### Task 4.1: Document API
- **Skill:** api-documentation-writer
- **Input:** API routes file
- **Max Iterations:** 3
- **Promise:** `API_DOCS_COMPLETE`
- **Criteria:** All endpoints documented, examples included, OpenAPI spec generated

### Task 4.2: Create README
- **Skill:** technical-writer
- **Input:** PROJECT.md
- **Max Iterations:** 2
- **Promise:** `README_COMPLETE`
- **Criteria:** Installation instructions, quick start, configuration explained

### Task 4.3: Write User Guide
- **Skill:** technical-writer
- **Input:** Previous handoff
- **Max Iterations:** 3
- **Promise:** `USER_GUIDE_COMPLETE`
- **Criteria:** Feature documentation, screenshots, troubleshooting

---

## Phase 5: Testing & QA

### Task 5.1: Create Test Suite
- **Skill:** webapp-testing
- **Input:** App output directory
- **Max Iterations:** 4
- **Promise:** `TESTS_COMPLETE`
- **Criteria:** E2E tests for critical paths, component tests, CI configuration

### Task 5.2: Security Audit
- **Skill:** code-review-pro
- **Input:** Output directory
- **Max Iterations:** 3
- **Promise:** `SECURITY_AUDIT_COMPLETE`
- **Criteria:** No critical vulnerabilities, auth secure, input validation

### Task 5.3: Performance Optimization
- **Skill:** code-review-pro
- **Input:** Previous handoff
- **Max Iterations:** 3
- **Promise:** `OPTIMIZATION_COMPLETE`
- **Criteria:** Bundle size optimized, render performance verified, caching implemented
