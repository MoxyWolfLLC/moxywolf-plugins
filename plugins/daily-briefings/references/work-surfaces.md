# Work surfaces — everywhere a dated obligation hides

The calendar is the smallest source of commitments a working person has. Most of what is actually owed lives somewhere else: a Jira ticket with a due date, a pull request that has been waiting eleven days, a social post scheduled to publish on Thursday, an invoice going overdue, a contract renewing, an envelope waiting on a signature, a decision record sitting at *proposed, pending sign-off*.

This file enumerates those surfaces. The commitment calendar sweeps the ones its config enables, and the rule from `source-discipline.md` governs every one of them: a dated obligation goes on the grid, an undated one goes to *Open loops*, and a surface that could not be read is reported as `not checked` rather than as quiet.

## How a surface is defined

Each entry below gives four things, and a surface is not implementable without all four:

- **the pull** — the tool call or query that gets the data
- **dated** — what from that surface earns a chip on the grid, and what date it uses
- **undated** — what from that surface belongs in *Open loops*
- **category** — which chip colour it takes

## Cost, and why surfaces are tiered

A full sweep across every surface below is a large number of calls, and a briefing that takes twenty minutes to build is a briefing that gets turned off. So surfaces are tiered in config:

- **`always`** — cheap, high-yield, run every time
- **`daily`** — run on the scheduled daily build, skipped on an ad-hoc `/commitment-calendar` unless asked
- **`weekly`** — run when the config says the day matches, otherwise reported as `not checked` with the reason `weekly surface, next on <day>`
- **`off`** — not run, reported as `not checked` with the reason `disabled in config`

**A skipped surface is always named in the footer.** Tiering is a cost decision, never a quiet one — the moment a skip becomes invisible, the grid starts lying by omission, which is the exact failure `source-discipline.md` exists to prevent.

Default tier for every surface is given in its row. `surfaces.<key>.tier` overrides it.

---

## Development & delivery

The largest source of dated work, and the one most likely to be silently behind.

### `jira` — the team board

- **pull** — `searchJiraIssuesUsingJql` on the configured project, scoped to the project's label from `surfaces.jira.labels`, `statusCategory != Done`. Two queries: one for `duedate <= <window end>`, one for issues assigned to the owner or awaiting them in a review state.
- **dated** — any issue with a `duedate` inside the window. Sprint boundaries if the board runs sprints. Chip title is the key plus a truncated summary; the key matters more than the prose because it is what you act on.
- **undated** — issues in a review state assigned to or reported by the owner: someone is blocked on them and there is no date saying when. Also anything in `Blocked`, with the blocker named if the link is there.
- **category** — Deadline for due-dated issues, Development for the rest.
- **tier** — `always`.
- **honesty note** — if the project's label returns zero issues, distinguish *the board has no tasks for this project* from *the board could not be read*. Both render as an empty section; only one is good news. Confirm the connector answered by checking that an unfiltered query returns something.

### `github` — repositories

- **pull** — per repo in `surfaces.github.repos`: `list_pull_requests` (open), `list_issues` (open), `list_releases`, and the milestones on each open issue.
- **dated** — milestone `due_on` inside the window. A release with a scheduled date. A PR whose branch is behind a dated freeze.
- **undated** — every open PR, with its age in days and its author, because an open PR is an obligation on somebody and the age is the whole signal. Split them: PRs authored by the owner (the owner owes a merge or a close) from PRs by others awaiting the owner's review (the owner owes a review). Also: open issues assigned to the owner, and any PR with a failing check.
- **category** — Development.
- **tier** — `always`.
- **age threshold** — `surfaces.github.stalePrDays`, default 7. A PR older than that gets called out rather than merely listed.

### `deployments` — hosting

- **pull** — `mcp__Vercel__list_deployments` for the configured projects, plus `get_domain_order` for domains the org holds.
- **dated** — **domain renewal and expiry dates.** These are hard, external, and expensive to miss, and they are exactly the class of obligation nothing else on this list will remind you about.
- **undated** — the most recent failed production deployment per project, with its error. A failed deploy is an open loop until someone looks at it.
- **category** — Deadline for renewals, Development for deploy failures.
- **tier** — `daily`.

### `database` — Supabase advisories

- **pull** — `mcp__Supabase__get_advisors` for security and performance on the configured projects.
- **dated** — nothing usually. A project scheduled to pause, if the plan has that, is a real date.
- **undated** — open security advisories, which belong in *Open loops* rather than being left to a dashboard nobody opens.
- **category** — Development.
- **tier** — `weekly`.
- **note** — the CRM pipeline's own health is a separate briefing, `/crm-sync-health`. Do not duplicate it here; if that briefing is enabled, reference its most recent result rather than re-running the query.

---

## Marketing & content

### `social` — scheduled posts

- **pull** — `mcp__Postiz__postsListTool` and `mcp__remote-devices__publora__list_posts` over the window.
- **dated** — every post scheduled to publish inside the window, at its publish time. **A scheduled post is a commitment**, and it is one of the few on this list that will execute itself whether or not the owner remembers — which makes seeing it in advance the entire point.
- **undated** — drafts that have been sitting unscheduled, with their age.
- **category** — Marketing.
- **tier** — `always`.
- **flag** — a post scheduled to publish during a travel span, or on a holiday, is worth surfacing. Not an error, but usually not intended either.

### `content-pipeline` — pieces in flight

- **pull** — the blog engine's state: in-progress pieces and their phase, per `surfaces.contentPipeline.paths`. A piece parked at a gate is the shape that matters.
- **dated** — a piece with a committed publish date. A recurring editorial slot, if the config declares one.
- **undated** — every piece in flight with its phase and how long it has been there. A draft stalled at a sign-off gate is an obligation on a named person, and naming both the piece and the gate is what unsticks it.
- **category** — Marketing.
- **tier** — `daily`.

### `outreach` — sequences and engagement queues

- **pull** — `mcp__Apollo_io__apollo_tasks_search` for tasks due in the window; the synergy tracker at `surfaces.outreach.trackerPath` for targets marked due or queued; `mcp__Clarify__get-campaigns` for campaigns with a send date.
- **dated** — Apollo tasks with a due date. Campaign send dates. Tracker rows whose follow-up date falls in the window.
- **undated** — queued engagement targets with no date, and sent outreach still awaiting a reply past the configured follow-up interval.
- **category** — Marketing.
- **tier** — `daily`.
- **note** — an outreach send is never scheduled by this briefing. It surfaces what is due and stops; sending stays behind whatever gate the outreach skill itself imposes.

### `events` — talks, webinars, podcasts

- **pull** — mostly the calendar, which already has them, plus the inbox sweep for confirmations that never got an invite.
- **dated** — the event, and separately **the deliverable deadline behind it**: slides due, a title and abstract due, a recording due. These are the deadlines most often missed, because the calendar holds the event and nothing holds the prep.
- **undated** — invitations accepted with no date fixed yet.
- **category** — Community & Events, with the deliverable as Deadline.
- **tier** — `always`, since it rides on the inbox sweep that runs anyway.

---

## Competition & search

Mostly not dated, and that is worth stating plainly rather than inventing dates to make it fit the grid. This domain contributes to *Open loops* far more than to the calendar.

### `search-visibility`

- **pull** — `mcp__Ahrefs__rank-tracker-overview` and `mcp__Ahrefs__site-audit-issues` for the configured projects; `mcp__Ahrefs__brand-radar-mentions-overview` if brand tracking is on.
- **dated** — a scheduled site-audit crawl, if one is configured. Little else here is a date.
- **undated** — new critical site-audit issues since the last briefing, and material rank movement on tracked terms. Both are *Open loops* entries, capped at the top few so the section stays readable.
- **category** — Marketing.
- **tier** — `weekly`.
- **honesty note** — rank movement is noisy over a two-week window. Report movement only past the threshold in `surfaces.searchVisibility.minRankDelta`, and say what the threshold was. A briefing that reports every wobble teaches its reader to skim it.

### `competitors`

- **pull** — the competitor set in `surfaces.competitors.watch`, checked for pricing-page and positioning changes since the last run.
- **dated** — a competitor's announced launch or event date, when one is known from the sweep.
- **undated** — detected changes worth a look.
- **category** — Marketing.
- **tier** — `weekly`.
- **note** — never assert a competitor change without the fetch date beside it. Provenance applies here exactly as it does everywhere else, and stale competitive intelligence presented as current is worse than none.

### `product-analytics`

- **pull** — `mcp__PostHog__exec` for running experiments and their planned end dates, and for feature flags staged to roll out.
- **dated** — **experiment end dates and staged rollout dates.** An experiment that quietly runs past its end is a decision nobody is making.
- **undated** — experiments past their end date with no decision recorded.
- **category** — Development.
- **tier** — `daily`.

---

## Revenue, finance & legal

The domain with the hardest dates and the highest cost of missing one.

### `invoices-and-bills`

- **pull** — `mcp__Intuit_QuickBooks__qbo_accounting_get_ar_aging_summary` and `..._ap_aging_summary`; `qbo_sales_get_invoices` for anything due in the window.
- **dated** — invoice due dates, bill due dates, estimate expiry dates, all inside the window.
- **undated** — anything already overdue, which is not a future commitment but is very much an open loop, listed with how far past due.
- **category** — Deadline.
- **tier** — `daily`.

### `payroll-and-tax`

- **pull** — `mcp__Intuit_QuickBooks__qbo_payroll_get_pay_schedules` and `..._get_company_payroll_readiness`.
- **dated** — pay dates in the window and the approval cutoff before each one, which is the date that actually binds. Filing deadlines if the config declares them.
- **undated** — a payroll run flagged not-ready.
- **category** — Deadline.
- **tier** — `daily`.

### `contracts`

- **pull** — `mcp__Docusign__getAllAgreements` and `mcp__Docusign__getEnvelopes`.
- **dated** — **renewal and expiration dates inside the window**, and any envelope with an expiry. A renewal date is the archetype of an obligation that exists nowhere on a calendar and costs real money to miss.
- **undated** — envelopes awaiting the owner's own signature, and envelopes sent to others still unsigned past the configured interval.
- **category** — Deadline for renewals, Client & Partner for envelopes.
- **tier** — `daily`.

### `pipeline-commitments`

- **pull** — `mcp__Clarify__get-calendar-events` and `mcp__Clarify__query-data` for deals with a close date in the window.
- **dated** — committed close dates, and any customer-facing milestone that was promised.
- **undated** — deals whose close date has already passed without a resolution.
- **category** — Client & Partner.
- **tier** — `daily`.

### `business-plan`

- **pull** — `mcp__LivePlan__get_milestones`.
- **dated** — plan milestones with a date in the window.
- **undated** — milestones already past their date and not marked done.
- **category** — Deadline.
- **tier** — `weekly`.

---

## Operations, knowledge & governance

### `scheduled-tasks` — what will fire on its own

- **pull** — `mcp__claude-code-remote__list_triggers`.
- **dated** — every enabled recurring task's firing times inside the window, rendered as a light background series rather than as commitment chips. It is context, not obligation: knowing the board deck generates itself on the first is why you do not block a morning for it.
- **undated** — a task that is disabled or suspended, or whose `last_fired_at` is far behind its cadence. A scheduled task that silently stopped firing is the automation equivalent of an orphaned run, and nothing else will tell you.
- **category** — Operations.
- **tier** — `always`. It is one call and it catches a failure mode that is otherwise invisible.

### `decisions` — sign-offs owed

- **pull** — the project's decision records at `surfaces.decisions.paths`, read for `status:` in frontmatter.
- **dated** — a decision with a stated decide-by date.
- **undated** — every record at `proposed` or `pending sign-off`, with its age and who owes the signature. This is one of the highest-value undated categories on the list: a decision record parked at *proposed* blocks work that nobody has connected back to it.
- **category** — Governance.
- **tier** — `daily`.

### `project-hygiene`

- **pull** — the project folders in `surfaces.projectHygiene.paths`, plus the session handoff.
- **dated** — anything in a backlog or sprint file carrying an explicit date.
- **undated** — a session handoff older than `surfaces.projectHygiene.staleHandoffDays`, default 14. A stale handoff means sessions have been running without recording state, and the next session will start from a wrong picture.
- **category** — Operations.
- **tier** — `daily`.

### `personal`

- **pull** — `mcp__Monarch__GetRecurring` if personal finance tracking is enabled.
- **dated** — recurring bills and subscription renewals in the window.
- **undated** — nothing.
- **category** — Personal & Health.
- **tier** — `off` by default. Personal finance is opt-in, and it stays that way — a shared-drive config should not quietly start rendering someone's bank into an HTML file that opens on their screen.

---

## What this does not do

It does not create, send, post, merge, pay, sign, or schedule anything on any of these surfaces. Every one of them is read. The briefing's job is to put the whole obligation set in one place where the pattern is visible, and then to get out of the way — the deciding stays with the person reading it.

It also does not re-derive what another skill already owns. Where a plugin in this fleet is the authority on a surface — the kanban sync for Jira conventions, the outreach tracker for engagement state, the CRM health check for pipeline state — read that authority's output rather than reimplementing its logic. Two implementations of the same rule drift, and the briefing is the one that will drift silently.
