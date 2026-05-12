# Code Review Checklist

Structured checklist for `/gstack-review`. Two passes: critical (blocking) and informational.

## Pass 1: Critical (Blocking)

These findings block merge. Each needs a specific file:line reference and a concrete fix.

### SQL Safety
- [ ] No raw SQL with string interpolation from user input
- [ ] Parameterized queries used for all dynamic values
- [ ] ORM methods used correctly (no `.raw()` or `.execute()` with interpolation)
- [ ] Database migrations are reversible

### Race Conditions
- [ ] No concurrent state mutation without locks/transactions
- [ ] Read-modify-write cycles are atomic
- [ ] Optimistic concurrency control where appropriate
- [ ] Background job idempotency (safe to retry)

### LLM Trust Boundaries
- [ ] User input never flows into system prompts
- [ ] LLM output is sanitized before rendering as HTML
- [ ] Tool/function call results from LLMs are validated before execution
- [ ] AI API keys are not hardcoded

### Auth & Access Control
- [ ] New routes have appropriate auth middleware
- [ ] Authorization checks cover horizontal access (user A can't access user B's data)
- [ ] Admin routes require elevated permissions
- [ ] Token validation is present on all protected endpoints

### Data Safety
- [ ] Destructive operations require confirmation
- [ ] Cascade deletes are intentional and documented
- [ ] Data migrations preserve existing data
- [ ] No accidental data exposure in API responses (password hashes, internal IDs)

### Enum/Switch Completeness
- [ ] Switch/match statements handle all cases
- [ ] Default/else cases are intentional, not a catch-all for bugs
- [ ] Type narrowing is exhaustive

## Pass 2: Informational (Non-Blocking)

These are improvements worth making but shouldn't block a merge.

### Code Quality
- [ ] No magic numbers (use named constants)
- [ ] No dead code introduced by the diff
- [ ] Functions are reasonably sized (< 50 lines is a good target)
- [ ] Variable names are descriptive
- [ ] No commented-out code checked in

### Side Effects
- [ ] Side effects happen where you'd expect (not in getters, renders, or pure functions)
- [ ] State mutations are explicit, not hidden
- [ ] External calls (APIs, DB, filesystem) are in clearly labeled service layers

### Error Handling
- [ ] Errors are caught and handled at appropriate levels
- [ ] Error messages are useful to the developer (not just "something went wrong")
- [ ] Failed operations don't leave system in inconsistent state
- [ ] Promises/async operations have error handling

### Testing
- [ ] Happy path has test coverage
- [ ] Error paths have test coverage
- [ ] Edge cases are covered (empty arrays, null values, boundary conditions)
- [ ] Test names describe the behavior being tested

### Performance
- [ ] No N+1 queries (batch/eager load where needed)
- [ ] No unnecessary re-renders (React: check memo/callback usage)
- [ ] Large lists use virtualization or pagination
- [ ] Images are optimized and lazy-loaded

### Accessibility
- [ ] Interactive elements have accessible labels
- [ ] Color is not the only way to convey information
- [ ] Keyboard navigation works for new UI elements
- [ ] Focus management is correct for modals/dialogs

### Frontend Specific
- [ ] No `console.log` statements left in production code
- [ ] Loading states are handled (no flash of empty content)
- [ ] Error states are handled (network failures, timeouts)
- [ ] Responsive design works at mobile/tablet/desktop
