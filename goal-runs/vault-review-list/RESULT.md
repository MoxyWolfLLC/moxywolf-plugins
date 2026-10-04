# Goal run: vault-review-list

- Outcome: running
- Approved in PR #146 by review 5408208574 at 24d982674a40, tree de00460dc6b0
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-opus-5
- Goal branch: goal/vault-review-list from a2f356ae9524
- Spend: $0 across {}; 4 counted calls

## Items

1. Add the list command - merged
2. Name list in /session-review - merged

## Goal tests at the last merged head

- `tests/test_list.py::List.test_lists_each_published_review` (outcome): passed
- `tests/test_list.py::List.test_never_lists_a_changed_publication_as_verified` (invariant): passed

## Digests and escalations

1. 2026-10-04T21:45:06+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: list trusts each folder's own hashes.sha256 and receipt, as read does, so it proves a copy is whole and matches its receipt, not who wrote it; and folders are sorted by name, so a large vault lists in name order, not by date
   Against the brief: 1 of 2 items merged; 2 of 2 goal tests passing; spend $0, 3 counted calls
2. 2026-10-04T21:50:33+00:00 digest
   Item 2 merged
   Close calls: none
   Least sure of: the doc names the vault path as <the project's vault folder>/11-Knowledge/session-records/, which assumes every project keeps that folder layout
   Against the brief: 2 of 2 items merged; 2 of 2 goal tests passing; spend $0, 4 counted calls
