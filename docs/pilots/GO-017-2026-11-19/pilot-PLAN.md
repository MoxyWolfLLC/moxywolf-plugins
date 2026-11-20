# Assignment Extraction prototype (synthetic fixtures)

1. Reader and coverage
   - reader/read.py returns every bracket occurrence with its ID and source evidence as INTERFACE.md section 1 states
   - coverage reports missing, duplicate and unaccounted occurrences and reconciles on both fixtures
2. Decision engine and replay
   - engine/decide.py run applies ordered versioned rule cards to proposals and blind council votes, gated on measured reliability per outcome
   - engine/decide.py replay reproduces every disposition and reason from the record with zero model calls
   - Done is recorded only when the reader reconciles and every disposition is automatic
3. Read-only record and exception view
   - view/index.html shows each bracket, disposition, evidence and reliability, with no Confirm, Flag, Clear or Done controls
   - only a council exception offers adding evidence, which produces a new-run request and never alters the shown record
