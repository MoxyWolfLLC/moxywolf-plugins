# Analyze Protocol

The consistency check `/product-analyze` runs after the task plan exists (Phase 2 of a sprint) and before execution (Phase 3). Concept-ported from spec-kit's `/speckit.analyze` (MIT); re-specified for MoxyWolf's PRD → architecture → task-plan → charter chain. This is DR-004's anticipated `/product-analyze`.

**Strictly read-only.** The command reads artifacts and prints a report. It never edits a file and never blocks work — it recommends, the user decides. Remediation runs only through separate commands the user explicitly approves.

## Artifacts (MoxyWolf ↔ spec-kit mapping)

| MoxyWolf artifact | spec-kit equivalent |
|---|---|
| `PRD-*.md` (requirements) | `spec.md` |
| PRD architecture section + arch `PD-*.md` / `DR-*.md` | `plan.md` |
| The `/product-sprint` Phase 2 task plan (or a saved task list) | `tasks.md` |
| `CHARTER.md` at project root | `constitution` |

Load whatever exists; note absences. If there's no task plan yet, say so — analyze is a pre-execution gate, so it needs the task list to check coverage. It can still run a partial pass (PRD ↔ architecture ↔ charter) and flag the missing task plan.

## Semantic models to build

- **Requirement inventory** — each functional/non-functional requirement from the PRD, with a stable key.
- **Architecture commitments** — the technology, boundary, and pattern decisions.
- **Task list** — each task, with any requirement it references (explicit ID or keyword inference).
- **Charter rule set** — the MUST/SHOULD principles and boundaries.

## Detection passes

- **A. Duplication** — near-duplicate requirements or tasks; overlapping scope stated twice.
- **B. Ambiguity** — vague or untestable requirements; acceptance criteria that can't be verified; undefined key terms.
- **C. Underspecification** — requirements with no detail to build against; NFRs named but unquantified.
- **D. Charter alignment** — any requirement, architecture decision, or task conflicting with a charter **MUST**. These are automatically **CRITICAL**. Resolve by changing the artifact, or amend the charter separately via `/project-charter` — never by silently reinterpreting a principle.
- **E. Coverage** — map each task to one or more requirements. Flag: requirements with **zero tasks** (uncovered), and tasks mapping to **no requirement** (unmapped / scope creep).
- **F. Inconsistency** — terminology drift across artifacts; a task or plan element contradicting the PRD; an architecture decision the tasks don't honor.

## Severity rubric

- **CRITICAL** — violates a charter MUST; a baseline-functionality requirement has zero coverage; a core artifact is missing.
- **HIGH** — duplicate or conflicting requirement; ambiguous security/performance attribute; an untestable acceptance criterion.
- **MEDIUM** — terminology drift; missing non-functional task coverage; an underspecified edge case.
- **LOW** — wording/style improvement; minor redundancy that doesn't affect execution order.

## Report format

Print a Markdown report (no file writes):

```
## Product Analysis Report — {product}

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | PRD §FR-3 / §FR-7 | Two overlapping requirements | Merge; keep the clearer |

### Coverage
| Requirement | Has task? | Task IDs | Notes |
|-------------|-----------|----------|-------|

### Charter alignment
{conflicts with CHARTER MUSTs, or "none"}

### Unmapped tasks
{tasks with no requirement, or "none"}

### Metrics
- Requirements: {N}   Tasks: {M}
- Coverage: {%} (requirements with ≥1 task)
- Ambiguity: {N}   Duplication: {N}   Critical: {N}
```

Use stable IDs prefixed by category initial (Duplication→D, Ambiguity→A, Underspecification→U, Charter→C, coveraGe→G, Inconsistency→I). Rerunning on unchanged artifacts should produce consistent IDs and counts.

## Next actions

- If CRITICAL issues exist: recommend resolving before execution, and name the fix command per finding — `/product-clarify` (ambiguity), `/product-scope` (scope/coverage), `/product-arch` (architecture conflict), or a manual task-plan edit.
- Charter conflicts: change the artifact, or amend the charter via `/project-charter` in a separate explicit step.
- Offer a remediation plan; the user must approve before any editing command runs. Analyze itself changes nothing.

## Scope boundary

Analyze checks the **planning artifacts against each other and the charter**, before build. Checking the **built implementation against the spec** after build is the paired DR-004 follow-on `/gstack-verify`, which lives on the gstack-execution side — out of scope for this command.
