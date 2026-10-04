# Goal run: vault-review-list-2

- Outcome: running
- Approved in PR #154 by review 5408767881 at c04aa04b830e, tree 7f5e59c5fd46
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-opus-5
- Goal branch: goal/vault-review-list-2 from 890a6fd3f556
- Spend: $0 across {}; 2 counted calls

## Items

1. Add the list command - merged
2. Name list in /session-review - merged

## Goal tests at the last merged head

- `tests/test_list.py::List.test_lists_each_published_review` (outcome): passed
- `tests/test_list.py::List.test_never_lists_a_changed_publication_as_verified` (invariant): passed

## Digests and escalations

1. 2026-10-04T23:44:55+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: the empty-folder message now goes to standard output with exit 2 while a missing path is refused on standard error with exit 2; a caller can't tell those two apart by exit code alone
   Against the brief: 1 of 2 items merged; 2 of 2 goal tests passing; spend $0, 1 counted calls
2. 2026-10-04T23:50:45+00:00 digest
   Item 2 merged
   Close calls: none
   Least sure of: the doc assumes every project keeps its vault reviews under 11-Knowledge/session-records/
   Against the brief: 2 of 2 items merged; 2 of 2 goal tests passing; spend $0, 2 counted calls
