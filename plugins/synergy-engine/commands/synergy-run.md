---
description: Run the comment-first cycle on due/approved targets via Claude in Chrome — like + comment (+ cite + connect), human-gated, logged to the tracker.
argument-hint: "[N targets, default 5]"
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, mcp__Claude_in_Chrome__tabs_context_mcp, mcp__Claude_in_Chrome__navigate, mcp__Claude_in_Chrome__computer, mcp__Claude_in_Chrome__read_page, mcp__Claude_in_Chrome__get_page_text, mcp__Claude_in_Chrome__find]
---

# /synergy-engine:synergy-run — execute the cycle

Engage the due/approved targets in the user's own logged-in browser. **The plugin never auto-posts** — every public action is gated on an explicit OK. Read `references/cadence-and-guardrails.md` in full before the first action.

## STEP 1 — Load config + select targets

Read `synergy-engine-config.md` and the tracker. Select up to N **due** targets (default 5; see the due rule in `references/tracker-schema.md`), preferring High synergy. Honor the cadence cap — if the user has already commented heavily today, do fewer.

## STEP 2 — Confirm the batch

Show the selected targets, each with its path (A / B / cite-then-tell), the drafted comment, and the connect/DM note. Get one approval on the batch text (or per-target edits) before touching the browser.

## STEP 3 — Per target, run the cycle (Chrome)

For each target, in the user's logged-in LinkedIn:

1. **Navigate** to the post; screenshot to confirm it's current and uncommented.
2. **Like** by clicking the thumb (NOT the avatar+caret — that's the identity selector; see the hazard note). Verify the count incremented.
3. **Comment.** Find the comment editor (find → click ref), confirm focus (screenshot for the cursor/border), type the drafted comment. Verify it's in the box. **Confirm the composer actor is the intended person**, not a Company Page. Then submit and verify the posted comment shows the right name.
4. **Path A / cite-then-tell:** if the path edits live content (an `/answers` page), do that edit first, confirm it's live, THEN comment with the link.
5. **DM/connect:** per cadence, the connect note waits 2-3 days. If due now and the target isn't a connection, send a connection request with a <=300-char note that names the commented post (no URL — the comment carries it). Email-gated connects are skipped (the like+comment is the touch); InMail is the alternative.

Between each, re-verify the composer identity and space the actions out.

## STEP 4 — Log every action

After each target, write to the tracker: Liked, Commented + date, Comment summary, Cited URL (Path A), Connect status, Status (`Engaged` / `Pending accept`), Next Action, Next Action Date. The tracker is the dedupe and the queue — keep it current.

## STEP 5 — Report

Summarize what posted (per target), what's pending (connects awaiting accept), and what's still queued. Note any target that was email-gated or already-commented and skipped.
