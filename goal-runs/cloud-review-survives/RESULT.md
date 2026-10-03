# Goal run: cloud-review-survives

- Outcome: running
- Approved in PR #138 by review 5402633544 at e51166e247e0, tree 48daeabb4fcd
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-opus-5
- Goal branch: goal/cloud-review-survives from dfc4f04412ec
- Spend: $0 across {}; 2 counted calls

## Items

1. Add the read command - merged
2. Say how a cloud session's review reaches the vault - not built

## Goal tests at the last merged head

- `tests/test_read.py::Read.test_prints_the_published_review_after_staging_is_gone` (outcome): passed
- `tests/test_read.py::Read.test_never_prints_a_changed_publication` (invariant): passed

## Digests and escalations

1. 2026-10-03T21:32:47+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: read trusts publish's own hashes.sha256 and receipt, so anyone who can write the vault folder can rewrite both consistently; it proves the copy is whole and matches its own receipt, not who wrote it
   Against the brief: 1 of 2 items merged; 2 of 2 goal tests passing; spend $0, 2 counted calls
