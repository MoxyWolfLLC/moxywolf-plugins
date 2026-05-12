# Phase Task Definitions

Detailed task breakdowns for each phase of the code review workflow.

## Phase 1: Code Analysis

### Task 1.1: Security Analysis
- **Skill:** code-review-pro
- **Input:** Path to codebase root
- **Max Iterations:** 4
- **Promise:** `SECURITY_ANALYSIS_COMPLETE`
- **Criteria:** SQL injection checked, XSS checked, auth issues identified, dependencies scanned

### Task 1.2: Performance Analysis
- **Skill:** code-review-pro
- **Input:** Previous handoff
- **Max Iterations:** 3
- **Promise:** `PERFORMANCE_ANALYSIS_COMPLETE`
- **Criteria:** N+1 queries identified, memory leaks checked, inefficient algorithms flagged

### Task 1.3: Code Quality Review
- **Skill:** code-review-pro
- **Input:** Previous handoff
- **Max Iterations:** 3
- **Promise:** `CODE_QUALITY_COMPLETE`
- **Criteria:** DRY violations identified, complexity analyzed, error handling reviewed

### Task 1.4: Regex Pattern Audit
- **Skill:** regex-visual-debugger
- **Input:** Files containing regex patterns
- **Max Iterations:** 2
- **Promise:** `REGEX_AUDIT_COMPLETE`
- **Criteria:** Complex patterns explained, performance issues identified
- **Skip if:** No regex patterns found

---

## Phase 2: Documentation Audit

### Task 2.1: Documentation Gap Analysis
- **Skill:** technical-writer
- **Input:** README.md, docs/
- **Max Iterations:** 3
- **Promise:** `DOC_GAPS_IDENTIFIED`
- **Criteria:** Missing docs identified, outdated content flagged

### Task 2.2: API Documentation Review
- **Skill:** api-documentation-writer
- **Input:** api/, routes/, controllers/
- **Max Iterations:** 3
- **Promise:** `API_DOCS_AUDITED`
- **Criteria:** Undocumented endpoints listed, missing examples identified

### Task 2.3: Generate Missing Documentation
- **Skill:** technical-writer
- **Input:** Previous handoff
- **Max Iterations:** 4
- **Promise:** `DOCUMENTATION_GENERATED`
- **Criteria:** Critical gaps filled, README updated

---

## Phase 3: Architecture Review

### Task 3.1: Database Schema Analysis
- **Skill:** database-schema-designer
- **Input:** migrations/, schema/, models/
- **Max Iterations:** 3
- **Promise:** `SCHEMA_ANALYZED`
- **Criteria:** Normalization assessed, missing indexes identified

### Task 3.2: Schema Optimization Recommendations
- **Skill:** database-schema-designer
- **Input:** Previous handoff
- **Max Iterations:** 3
- **Promise:** `SCHEMA_OPTIMIZATIONS_COMPLETE`
- **Criteria:** Optimization SQL generated, migration scripts created

### Task 3.3: Architecture Diagram Generation
- **Skill:** technical-writer
- **Input:** Previous handoff
- **Max Iterations:** 2
- **Promise:** `ARCHITECTURE_DOCUMENTED`
- **Criteria:** System diagram created, data flow documented

---

## Phase 4: Testing & Validation

### Task 4.1: Test Coverage Analysis
- **Skill:** webapp-testing
- **Input:** tests/, __tests__/, spec/
- **Max Iterations:** 3
- **Promise:** `COVERAGE_ANALYZED`
- **Criteria:** Coverage percentage calculated, untested files identified

### Task 4.2: Create Critical Path Tests
- **Skill:** webapp-testing
- **Input:** Previous handoff
- **Max Iterations:** 4
- **Promise:** `CRITICAL_TESTS_CREATED`
- **Criteria:** Login/auth flow tested, core features tested

### Task 4.3: Run Test Suite
- **Skill:** webapp-testing
- **Input:** Previous handoff
- **Max Iterations:** 3
- **Promise:** `TESTS_EXECUTED`
- **Criteria:** All tests passing, screenshots captured

---

## Phase 5: UI/UX Review

### Task 5.1: Color Accessibility Audit
- **Skill:** color-palette-extractor
- **Input:** styles/, css/, tailwind.config.js
- **Max Iterations:** 2
- **Promise:** `ACCESSIBILITY_AUDITED`
- **Criteria:** WCAG contrast verified, color blindness simulation done

### Task 5.2: UI Consistency Check
- **Skill:** screenshot-to-code
- **Input:** src/components/
- **Max Iterations:** 3
- **Promise:** `UI_CONSISTENCY_CHECKED`
- **Criteria:** Component patterns identified, inconsistencies flagged

### Task 5.3: Generate UI Improvement Recommendations
- **Skill:** screenshot-to-code
- **Input:** Previous handoff
- **Max Iterations:** 3
- **Promise:** `UI_RECOMMENDATIONS_COMPLETE`
- **Criteria:** Improvement list prioritized, code examples provided
