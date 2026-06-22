# Frontier Founder SMB — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see
[../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests (gate sized to stakes; a named human signs; provenance;
anti-rubber-stamp; human above the loop).

The Frontier Founder SMB plugin is the highest non-blog risk surface in the
fleet — it touches Stripe, QuickBooks (invoices, payroll, refunds), DocuSign
e-signature, Gmail sends, and the Clarify CRM. Every skill declares a risk tier
below. The table is the declaration of record; risk tiers are **not** added to
per-skill frontmatter.

## Risk tiers

| Tier | Meaning | Gate required |
|---|---|---|
| `read-only` | Reads/reports only; no writes, no sends | None (declare tier) |
| `generate` | Produces local artifacts (files, drafts) that don't auto-ship | None; provenance if claim-bearing |
| `side-effectful-gated` | Can send/post/write, but only behind a confirm checkpoint | Confirm + human owns outcome |
| `high-stakes` | Money, e-signature, public broadcast, customer-reaching, deletion | All five tests; named Release Owner + logged sign-off |

## Skill conformance table

| Skill | risk_tier | gate / note |
|---|---|---|
| business-pulse | read-only | Cross-connector snapshot; reads QuickBooks/Stripe/Clarify/Calendar/Gmail and reports. No writes or sends. |
| call-list | side-effectful-gated | Ranks leads, drafts follow-ups, and blocks Calendar time; the calendar write and any send sit behind owner confirm. Drafts only otherwise. |
| campaign-creator | **high-stakes** | Customer-reaching campaign staged in Clarify. Release Owner gate added before Clarify staging — named human signs, decision logged, override rate watched. |
| cash-flow-snapshot | read-only | Reads AR/AP and fixed costs; produces a forecast XLSX + chat summary. No writes or sends. |
| close-month | generate | Reconciles QB vs processors and writes a P&L narrative + close packet (xlsx/PDF) locally. Reads + generates; no sends. |
| content-strategy | read-only | Analyzes sales data and produces a strategic content brief. Strategic output only — no calendars, assets, or sends. |
| contract-review | generate | Reads contracts from files/Gmail/DocuSign and outputs a marked-up redline DOCX. Read + generate only; never signs or modifies the envelope. |
| crm-cleanup | side-effectful-gated | Fixes stale deals, duplicate contacts, missing fields in Clarify — but only what the owner approves. CRM writes behind a confirm. |
| crm-maintenance | side-effectful-gated | Creates/updates Clarify contacts, deals, notes from email/calendar context. CRM writes behind a confirm. |
| customer-pulse | read-only | Aggregates Stripe disputes, Clarify feedback, email sentiment, pasted reviews into a themes report. Reads + reports. |
| customer-pulse-check | read-only | Synthesizes themes into a top-3 fixable issues list with drafted templates. Reads + reports; templates are drafts only. |
| friday-brief | read-only | End-of-week revenue/seller/win pulse. Reads + reports. |
| handle-complaint | **high-stakes** | Refund/credit path. Release Owner gate added before issuing a refund or credit — named human signs, decision logged, override rate watched. |
| invoice-chase | **high-stakes** | Sends overdue-invoice reminders via Stripe/mail (money-reaching). Release Owner gate added before send — named human signs, decision logged, override rate watched. |
| job-post-builder | **high-stakes** | Routes offer letters to DocuSign for e-signature (and a Gmail fallback send). Release Owner gate added before creating the DocuSign envelope — named human signs, decision logged, override rate watched. |
| lead-triage | side-effectful-gated | Scores Clarify leads, drafts follow-ups, blocks Calendar time. Drafts + calendar write behind owner confirm. |
| margin-analyzer | read-only | Unit-economics analysis and pricing-scenario data. Surfaces analysis only — does not recommend or set a price. |
| monday-brief | read-only | One-page Monday briefing (cash, sales, pipeline, week ahead). Reads + reports; optional post destination is owner-directed. |
| month-end-prep | generate | Reconciles QB vs Stripe, flags gaps, writes P&L narrative, exports close packet. Reads + generates; no sends. |
| month-heads-up | read-only | 25th-of-month 30-day cash outlook with flags. Reads + reports. |
| plan-payroll | **high-stakes** | Stages the payroll run and Stripe reminders (money). Release Owner gate added before staging payroll / sending reminders — named human signs, decision logged, override rate watched. |
| price-check | read-only | Margin-by-product table and pricing scenarios so the owner can decide. Surfaces data only; no price is set. |
| quarterly-review | generate | Generates a QBR narrative as a presentation-ready PDF/deck. Reads + generates; presents, doesn't send. |
| review-contract | **high-stakes** | E-signature path (DocuSign envelope). Release Owner gate added before sending for e-signature — named human signs, decision logged, override rate watched. |
| run-campaign | **high-stakes** | End-to-end campaign ending in a customer-reaching Clarify send. Release Owner gate added before the campaign send — named human signs, decision logged, override rate watched. |
| sales-brief | read-only | Top/bottom sellers, seasonality, and a content brief. Reads + reports. |
| smb-onboard | side-effectful-gated | Connects tools, runs a proof recipe, interviews the owner, and stores business context persistently. Writes stored context; setup actions are owner-driven. |
| smb-router | read-only | Front-door router; explains options and routes to the right skill. No side effects of its own — downstream skills carry the risk. |
| tax-prep | generate | Quarterly estimated tax calc or year-end 1099 prep into an accountant handoff packet. Reads + generates; no filing or send. |
| tax-season-organizer | generate | Organizes tax-season materials into a handoff packet. Reads + generates; no filing or send. |
| ticket-deflector | **high-stakes** | Can issue a Stripe refund (money). Release Owner gate added before issuing the refund — named human signs, decision logged, override rate watched. |

**Skills tiered: 31** (high-stakes: 8 — campaign-creator, handle-complaint, invoice-chase, job-post-builder, plan-payroll, review-contract, run-campaign, ticket-deflector; side-effectful-gated: 6; generate: 7; read-only: 10).

## Notes on this migration

- The Release Owner gate (named human signs with initials + date, decision
  recorded to the shared gate log via
  `Taskade/_Shared Files/_gate-log/record_decision.py` as
  action/approver/ISO-8601-timestamp/outcome, never auto-approve, never sign on
  the owner's behalf, watch the override rate) was inserted at the irreversible
  action point in eight skills:
  `invoice-chase`, `plan-payroll`, `handle-complaint` (refund path),
  `review-contract` (e-signature path), `run-campaign`, and `campaign-creator`.
- **`ticket-deflector` and `job-post-builder` now gated.** Both were first
  flagged as a follow-up; the Release Owner gate has since been added before the
  Stripe refund and before creating the DocuSign e-signature envelope,
  respectively. All eight high-stakes skills now carry the named-signer,
  logged-decision, override-rate gate.
