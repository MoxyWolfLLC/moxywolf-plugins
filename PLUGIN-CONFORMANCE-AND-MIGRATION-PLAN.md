# Plugin Conformance & Migration Plan

**Status:** active standing checklist · **Created:** 2026-06-17 · **Owner:** MoxyWolf
**Governing doc:** The MoxyWolf AI Governance Manifesto — SIGNED (`Taskade/OpenControls/08 – Go-to-Market/Positioning & Messaging/MoxyWolf-AI-Governance-Manifesto.md`)
**Enforced by:** [`CHARTER.md`](CHARTER.md) (active, 2026-06-22) — see "CHARTER clause" below.

This is the conformance standard every MoxyWolf plugin and skill is held to, and the migration plan for bringing the current fleet into line. New skills ship against the five tests below. Existing skills are migrated in the priority order at the bottom.

## Migration status — pass 1 complete (2026-06-17)

All 25 entries (24 plugins + the moxywolf-skills bundle) now carry a `GOVERNANCE.md` with a per-skill risk-tier table. (`editorial-forge` was missed in the first pass and added 2026-06-22 — `generate` tier, author-owned content with no publish/send.) Gap fixes applied this pass:

- **frontier-founder-smb** — Release Owner gate (named signer + initials/date + logged decision + override-rate watch) added before the irreversible action in 8 high-stakes skills: `invoice-chase`, `plan-payroll`, `handle-complaint`, `review-contract`, `run-campaign`, `campaign-creator`, `ticket-deflector`, `job-post-builder`.
- **team-kanban** — confirm-before-post checkpoint on the #general digest and the shared Canvas (and the setup intro post).
- **daily-ops** — confirm checkpoint before the fitness iMessage send and the calendar writes.
- **moxywolf-skills (bundle)** — provenance gate on `stigviewer-content-ecosystem`, `sorkin-dob-weekly-blog`, `blog-content-ecosystem`; outreach/comment skills marked draft-only (a named human sends).
- **gstack-execution** — no auto-push to a protected branch; a named human owns the merge.
- **github-repo-analyzer** — no PR/push/issue without explicit approval of the exact change.
- **obsidian-update** — named approver required on the external-send path.
- **composio** — downstream third-party toolkits inherit the fleet's risk tiers + Release-Owner gate.

Exemplars unchanged (reference patterns): `4d-blog-engine`, `research-pipeline`, `academic-pipeline`. The remaining low-risk plugins received tier declarations only.

EV-1 — DONE (2026-06-22): the shared gate decision log is wired. The eight high-stakes frontier-founder-smb gates now record each decision via `Taskade/_Shared Files/_gate-log/record_decision.py` (append-only `gate-decisions.jsonl`, one row per decision; the writer refuses a vague approver). `override_report.py` rolls the log up into override rate + median response time per skill and per tier, flagging `RUBBER-STAMP?` (override rate <10% on >=5 decisions) and `TOO-FAST?` (median response <20s). This is the data behind Test 4 and the manifesto's "watch the override rate" line.

---

## The CHARTER clause this enforces

> **Every skill declares a risk tier, and routes high-stakes (irreversible / customer-reaching / money-moving) actions through a named Release Owner who signs, with the decision logged.**

(One line for `CHARTER.md`. The rest of this document is how we check it.)

## The five tests

A plugin/skill is conformant when it passes every test that applies to it:

1. **Gate sized to stakes.** A human checkpoint exists before any high-stakes / irreversible action: sending email or messages, posting publicly, publishing, moving money (invoices, refunds, payroll), deleting data, writing to customer systems / CRM / DB / config, or e-signature.
2. **A named human signs.** High-tier output requires one *named* human to approve (not "the team," not a vague "the user"), and the approval is recorded.
3. **Provenance.** Claim-bearing or factual output carries source + date; no fabricated citations; unverifiable claims are flagged, not shipped.
4. **Anti-rubber-stamp.** The skill refuses to ship below a defined threshold, and the oversight itself is auditable (override rate, response time, or sampling) so a rubber-stamp pattern is detectable.
5. **Human above the loop.** No autonomous irreversible action. A named human owns the outcome regardless of how much was automated.

## Risk tiers (declare one per skill)

Add a `risk_tier` to each skill's frontmatter:

| Tier | Meaning | Gate required |
|---|---|---|
| `read-only` | Reads/reports only; no writes, no sends | None (declare tier) |
| `generate` | Produces local artifacts (files, drafts) that don't auto-ship | None; provenance if claim-bearing (Test 3) |
| `side-effectful-gated` | Can send/post/write, but only behind a confirm checkpoint | Tests 1, 5 |
| `high-stakes` | Money, e-signature, public broadcast, customer-reaching, deletion | All five tests; named Release Owner + logged sign-off |

## Per-plugin conformance table

Legend — **EXEMPLAR** (already embodies the manifesto), **NEEDS CHANGE** (real risk surface + a gap), **LOW-RISK** (declare tier, little/no other change).

| Plugin | Risk surface | Current state | Verdict | Change required (test) |
|---|---|---|---|---|
| **4d-blog-engine** | Publishes to GitHub repos; posts LinkedIn (personal + Company Pages); Slack #general nudge | Nonce-bound 5-stage Release Owner Gate; preflight + BLOCKING reviewer + 100-pt rubric + iteration cap; never auto-signs; stops before every irreversible publish; verified bibliography | EXEMPLAR | None. Reference pattern for the fleet (Tests 1,2,4,5). |
| **research-pipeline** | Writes citations/libraries to Supabase; produces content | 4-layer citation-verifier (CrossRef/DataCite/arXiv/Semantic Scholar); catches hallucinated refs | EXEMPLAR | None. Canonical Test 3. Other content plugins must call it. |
| **academic-pipeline** | Generates articles + bibliographies | "Never invent citation data"; missing fields flagged `n.d.` | EXEMPLAR | None. Models Test 3. |
| **frontier-founder-smb** | **Highest non-blog surface:** Stripe, QuickBooks (invoices/payroll/refunds), DocuSign, Gmail sends, Clarify CRM | Pervasive "owner approves" / "drafts only" / "never auto-send" / "never sign the envelope" | NEEDS CHANGE | Approver is a vague "owner" with no record — fails **Test 2** + **Test 4**. Add named signer + logged decision + override-rate on `invoice-chase`, `plan-payroll`, `handle-complaint` (refunds), `review-contract` (e-sign), `run-campaign`, `campaign-creator`. |
| **team-kanban** | Auto-sends daily digest to Slack #general; writes shared Canvas | New-task creation approval-gated, but the #general digest + Canvas write are auto | NEEDS CHANGE | Public broadcast with no pre-send checkpoint fails **Test 1**. Show-digest-then-confirm before posting to #general / first Canvas publish. |
| **daily-ops** | Fitness mode auto-creates Calendar event + auto-sends iMessage; writes tasks to Drive/vault | Standup/triage writes confirm-gated; fitness Steps 6/7 ungated | NEEDS CHANGE | Ungated message send + external write fails **Test 1** (low stakes, self-directed). Confirm workout + recipient before calendar create + iMessage. |
| **obsidian-update** | Vault writes; harvests Slack Canvas; queues external sends | "Present for approval before writing"; "queue for approval before sending externally" | NEEDS CHANGE (minor) | Mostly gated. Name the approver on the external-send path (**Test 2**); declare tier. |
| **gstack-execution** | Code writes: commit, push, prepare PR; QA fixes | Ship pipeline stops on CRITICAL; commits offered not forced; adversarial codex-review | NEEDS CHANGE (minor) | Add explicit "no auto-push to protected branch / a named human owns the merge" (**Tests 2,5**). |
| **github-repo-analyzer** | `create_pr`, `create_issue`, `push_file` via GitHub MCP | `suggest-fixes` is one-at-a-time HITL; verify-fix read-only | NEEDS CHANGE (minor) | State "never open a PR / push without explicit approval" on the write capabilities (**Tests 1,5**). |
| **moxywolf-skills** (bundle) | LinkedIn comment drafting in logged-in browser; outreach skills produce ready-to-send msgs; content-ecosystem skills produce publishable content | linkedin-thought-leadership confirms before drafting + skips already-commented; outreach drafts-only; content carries bracketed citations | NEEDS CHANGE (minor) | (a) "ready-to-send" outreach must state human-sends-it; (b) `stigviewer-content-ecosystem`, `sorkin-dob-weekly-blog`, `blog-content-ecosystem` should route citations through research-pipeline's verifier (**Tests 3,5**). |
| **board-deck** | None (reads LivePlan/GA4/Taskade/GitHub/Gmail; generates deck) | Read-only ingestion + generation; presents, doesn't send | LOW-RISK | Declare tier; optional provenance footnotes on stat slides (Test 3). |
| **analytics** | None — read-only GA4 | "Read-only"; creds from env | LOW-RISK | Declare tier. |
| **council** | API spend; writes deliberation memory to vault | Advisory; decision-support not action | LOW-RISK | Declare tier (advisory / no irreversible external action). |
| **product-orchestrator** | Writes decision records + charter to vault; routes to execution skills | Advisory; the execution skills carry the risk | LOW-RISK | Declare tier. |
| **document-analysis / markitdown** | Local file → Markdown | Per-file isolation; idempotent manifest | LOW-RISK | Declare tier. |
| **bibtex-builder** | Builds/enriches .bib | "Never invent citation data" | LOW-RISK | Declare tier. |
| **graphify** | Builds graph; writes exports to vault | Sandbox-safe; env key | LOW-RISK | Declare tier. |
| **editorial-forge** | Author-owned content + authorship record | No publish/send | LOW-RISK | Declare tier. |
| **saas-frontend-designer** | Generates UI code (local) | Generate/audit/polish; no deploy | LOW-RISK | Declare tier. |
| **saas-pricing-engine** | Pricing research/models/copy; scrapes competitor pages | Research + generation; no publish | LOW-RISK | Declare tier; provenance on competitor-scan stats (Test 3, minor). |
| **dev-infrastructure-skills** | Reference docs | Knowledge only | LOW-RISK | Declare tier. |
| **vtt-to-text** | VTT → text (local) | Pure transform | LOW-RISK | Declare tier. |
| **composio** | Sets up Composio MCP connector | Setup/teaching; native MCPs first | LOW-RISK | Declare tier; add "downstream toolkits inherit this fleet's gate rules." |
| **project-init** | Mounts folders; writes Project Instructions/handoff; refreshes READMEs | Strong stale-reminder verification; scaffolding writes | LOW-RISK | Declare tier. |
| **frontier-founder** | Converts draft → blog post saved into FrontierFounder repo (file write, no push) | Defers AEO to 4d canonical; produces file | LOW-RISK | Declare tier; if it gains a publish step, route through 4d's Release Owner Gate. |

## Fleet-wide changes (the four moves)

1. **Declare a risk tier per skill** — universal, cheapest, do first. Makes Tests 1 and 5 checkable. ~half the fleet needs only this.
2. **Upgrade "ask the owner" → named signer + recorded decision on high-tier actions** (Tests 2 + 4). Biggest systemic gap. Port the 4d Release Owner pattern.
3. **Close the auto-broadcast holes** (Test 1): `team-kanban` #general digest, `daily-ops` fitness iMessage/calendar, `obsidian-update` external send.
4. **Make provenance a routed dependency, not a per-skill habit** (Test 3): claim-bearing publish paths call `research-pipeline` citation-verifier (or 4d's verified-bibliography step).

## Migration priority (highest risk surface × biggest gap)

1. **`frontier-founder-smb`** — money / e-sign / payroll with unnamed approvers.
2. **`team-kanban`** — auto Slack #general broadcast, no pre-send gate.
3. **`daily-ops`** (fitness) — ungated iMessage / calendar writes.
4. **`moxywolf-skills` content-ecosystem skills** — claims without routed provenance.
5. Minor: `gstack-execution`, `github-repo-analyzer`, `obsidian-update`, `composio`.

Copy from: **`4d-blog-engine`** (the gate), **`research-pipeline`** / **`academic-pipeline`** (provenance).

---

*Audit method: each plugin's `plugin.json` + skills/commands were read for side-effectful actions and existing gate/provenance language, then judged against the five tests. Re-run this audit whenever a plugin gains a new side-effectful capability.*
