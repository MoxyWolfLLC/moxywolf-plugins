---
read_when: "synergy-cite-run (and synergy-run for the connect-note mechanics) load this before any email or LinkedIn send. The send-discipline rules are non-negotiable; they were paid for in real truncated sends."
status: canonical
---

# Outreach channels — email and the LinkedIn send discipline

Two channels. The citation center leads with **email**, then a LinkedIn **connection note**. The post center uses only the LinkedIn mechanics in Part 2. Every send is human-gated; the plugin never auto-sends.

## Part 1 — Email (Mailtrap, "we cited you")

### Structure (the order matters)

1. **Their bibliographic reference first.** Open with the work of theirs we cited, in full reference form. The email is about them.
2. **How we used it.** The section of our paper and the claim their work supports.
3. **Our paper, once.** Name our paper a single time, with the link/DOI. Don't center ourselves; the first drafts that mentioned our paper twice read as a pitch and were corrected. (memory: feedback_citation_outreach_email_structure)

Voice: no em-dashes, contractions, typographer's quotes, no sales ask. The contribution is the citation, never a request.

### Sending

- **Mailtrap** (`mcp__Mailtrap__send-email`) sends as **dorianc@moxywolf.com** over the DNS-verified moxywolf.com domain. Pass `from` and `to` as plain **strings**, not objects.
- **BCC dorianc@moxywolf.com on every send** so it lands in the sent box. (memory: feedback_bcc_dorian_on_outreach_sends)
- The Gmail connector is **draft-only** and can't send; don't reach for it to send.
- Approve the batch text before sending. Log each send to the registry (Email Sent + date).

## Part 2 — LinkedIn connection note (the send discipline)

This is the expensive lesson. On 2026-06-24, 5 of 10 notes shipped truncated because of a focus race. The rules below are the fix that holds.

### Typing the note (the truncation fix)

- **Click the field and type in SEPARATE calls, never batched.** Batching the field-click and the type into one browser action races the composer's focus and silently drops the first 10-25 characters.
- After typing, **zoom the field and read the first AND last line.** A plain screenshot is not enough; the composer scrolls and hides a clipped opening. Only Send after the zoom confirms the note starts and ends correctly.
- Reliable sequence: open the connect dialog -> click "Add a note" -> click the text field (own call) -> type the note (own call) -> zoom-verify start and end -> Send -> confirm "Pending".

### Button geography by degree

- **2nd-degree:** a direct **Connect** button on the profile.
- **3rd-degree:** Connect is hidden under the **More (...)** menu.
- **High-follower / creator profiles:** **Follow** is the primary button; Connect is under **More (...)**.
- Confirm every send by the button flipping to **"Pending"** (or the "Invitation sent to <name>" toast).

### The email-verification gate

Some high-profile profiles gate the connect on the member's email ("To verify this member knows you, please enter their email"). Enter the **enriched work email we already hold** (we'd already emailed them there), then "Add a note," then the note, then Send. Don't guess an email; only use one we already have on file.

### Hook-free notes

Connection notes **acknowledge the citation and connect, nothing more.** No "if you connect I'll send the doc" promise. (The first 10 sent on 2026-06-24 carried that hook and still owe an accept-reply; everything after is hook-free.) Keep notes <=300 characters; the registry's draft column enforces the limit.

### Two hard "don'ts"

- **Never withdraw a bad pending invite to re-send a corrected one.** Withdrawing triggers a ~3-week resend lockout. To fix a garbled note, wait for the accept and send a clean correcting DM (messaging unlocks on accept).
- **Non-connections can't be free-messaged.** The Message button on a 2nd/3rd-degree profile routes to paid Sales Navigator InMail, not a regular DM. Regular messaging unlocks only when they accept.

(memory: feedback_linkedin_connect_send_gotchas)

## Part 3 — Sequencing the two channels

Email first (it's the substantive thank-you), then the LinkedIn connect a beat later. The connect note can reference the email ("just emailed you...") when the person was emailed, so the two channels reinforce rather than duplicate. Honor the same daily LinkedIn ceiling as the post center (~20-25 connects/day, ~100/week; see `cadence-and-guardrails.md`).
