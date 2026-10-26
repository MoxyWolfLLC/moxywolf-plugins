# Expansion rules

Expansion is where a question bank turns into the model talking to itself. These rules keep it honest.

1. **Draft only where `bank.py report` shows a gap**: a persona with few or no questions, a question blocked on `requires_input`, a REST-only route nobody asks about, or a capability the inventory found that no question uses.
2. **Label honestly.**
   - A child of an existing question is `generated` with `evidence.parent`.
   - A new question drawn from a persona doc is `hypothesis`, with `source` and `source_line`.
   - Never use `observed` or `reported` for anything Claude wrote.
   - If the source doc says its quotes are unvalidated, do not lift them as customer words.
3. **Every draft gets** `review_status: "draft"` and `evidence.authored_by: "claude (draft)"`.
4. **Synthetic inputs use real identifiers.** Take rule ids, control ids and slugs from fixtures or samples in the repo, so a failure means the product is wrong and not the test. Say in `evidence.note` what is real and what was assigned.
5. **Write the `why` from the user's side**, meaning what goes wrong for them if this fails. "Tests the triage tool" is not a why.
6. **Discovery drafts name no tools.** If you are confident about the tool, write a strict question and justify it.
7. **Boundary questions** set `must_refuse` and a rubric that says what a good refusal offers instead.
8. **Do not chain.** A generated question may not be the parent of another generated question.
9. **Stay under the cap.** Generated questions can be at most 3 times the persona's other questions.
10. **Gap questions test the inventory's own claims.** If an older inventory calls something a gap and the capability map now shows a tool for it, draft a question that checks whether the gap has closed.
