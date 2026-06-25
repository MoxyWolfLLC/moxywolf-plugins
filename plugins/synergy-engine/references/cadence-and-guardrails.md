---
read_when: "synergy-run and synergy-schedule load this before any public action. These rules are non-negotiable."
status: canonical
---

# Cadence and guardrails

## Human-in-the-loop (hard rule)

The plugin **never auto-posts.** Every public action — like, comment, connection request, DM, reshare — and every live content edit (e.g. editing an `/answers` page) goes through an explicit human OK in the same session, through the user's own logged-in browser via Claude in Chrome. Show the exact text in the composer and confirm before the irreversible click. Reserve a final confirm for: comments, connects/DMs, and content-page edits.

## The "Post as" identity hazard

LinkedIn's identity selector (the avatar + caret, the "Comment / react / repost as" control) sits immediately left of the like button in the action bar. A stray click opens it, and selecting a Company Page silently switches the composer to "Comment as <Page>" — so the next comment posts as the wrong actor.

- Like by clicking the **thumb**, not the avatar+caret to its left. If a reaction fly-out opens, click "Like" in it.
- Before each comment, the composer should read the intended actor (e.g. "Add a comment…" as the person, not "Comment as <Page>"). If it drifted, open the identity selector, re-select the person, Save.
- After posting, verify the published comment shows the intended name.

## Comment-box focus quirk

The collapsed comment box often needs a deliberate focus click before it accepts typed text — click it, screenshot to confirm the focus border/cursor, then type. Using the editor's element reference (find → click ref) is more reliable than pixel clicks; re-find the ref if the page scrolled.

## Cadence numbers

- **<= 5 fresh targets per run** for the comment-first post centers. More than that in one sitting trips LinkedIn's velocity flags. If a day already had heavy commenting elsewhere, do fewer.
- **Comment same day; connect/DM 2-3 days later.** Firing a DM seconds after the comment looks automated and burns the warmth.
- **Don't re-comment on the same person within ~3 of their posts.** Once every few posts reads as genuine; every post reads as hovering.
- **Re-run the full discovery sweep each publishing cycle** to refresh who's posting on-theme.
- Spread a batch over a couple of sittings, with a random-ish time inside the window, so it never looks mechanical.

### Connection-request envelope (citation center + any connects)

LinkedIn's 2026 envelope for connection requests: **~100/week, ~20-25/day**, danger if outstanding unanswered invites exceed **~700**, and a ~1-week freeze on breach. The citation center sends connection notes in volume, so it honors the per-day ceiling; cap a citation run accordingly and count any connects already sent that day.

## Connection-note send discipline

The mechanics of typing and sending a LinkedIn connection note (the separate-click-then-type fix for the truncation bug, the mandatory zoom-verify of the note's start and end before Send, the 2nd/3rd/high-follower button geography, the email-verification gate, the withdraw lockout, and the "non-connections can't be free-messaged" rule) live in `references/outreach-channels.md` Part 2. Both `/synergy-cite-run` and `/synergy-run` (for its connect step) load it before sending. These are non-negotiable; they were paid for in real truncated sends.

## Voice

- No em-dashes. 80%+ contractions. Typographer's quotes where the surface allows.
- Practitioner register: the comment adds something a senior peer would forward. Reference the live thread (a commenter by name) to show you read it.
- No hype, no "Most people don't realize", no generic CTAs.
- Read the writer's voice profile if one is configured before drafting outreach copy.

## Citations

- **Verified only.** Never fabricate a work, a DOI, or an authorship. Verify author + title (web search / the source) before citing. Misattributing a paper to the wrong author is the failure this rule exists to prevent.
- Path A / cite-then-tell edits to live content stay inside any charter guardrails for that content (e.g. "evidence / due-diligence", never legal advice).

## Tracker discipline

The xlsx tracker is the source of truth for dedupe and the queue. Never engage a target already `Engaged` or `Ready for review` unless its Next Action Date is due. Log every action (Liked, Commented + date, Cited URL, Connect status, Status, Next Action, Next Action Date) immediately after it happens.

## Repo / content writes

If a run augments content in a Git repo, commit + push via sandbox `git` with the team PAT over a per-URL auth header (never echo the token), and verify the push with `ls-remote`. Live database content edits (e.g. Supabase `/answers`) are gated on the user's OK and go live immediately — sequence: edit → confirm live → then send the outreach that links to it.
