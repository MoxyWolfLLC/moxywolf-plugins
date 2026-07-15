---
name: email-lifecycle
description: This skill should be used when the user invokes one of the /email-* lifecycle commands (/email-activation, /email-nurture, /email-convert, /email-retain, /email-lifecycle) or asks for the best practices, tooling, or a drafted sequence for a stage of the product email lifecycle (onboarding/activation, nurture, convert-to-paid, retain/expand, or the whole arc). For the stage in scope it returns: (1) best practices, (2) which installed skills to use + catalog adoption candidates, (3) a benchmark of the named product's current setup, (4) prioritized recommendations, and (5) an auto-drafted email sequence. It is the email-specific, stage-sharded sibling of marcom-audit.
---

# Email Lifecycle

The engine behind the `/email-*` commands. Each command runs this skill scoped to one lifecycle stage (or the whole arc), and for that scope produces five things: **best practices → tooling (have + adopt) → benchmark of our current setup → recommendations → an auto-drafted sequence.**

The stage is set by the invoking command; you only resolve the target and goal.

## Inputs

- **Stage** — set by the command (`activation` | `nurture` | `convert` | `retain` | `full`). Don't ask; the command carries it.
- **Target product** — which product's email lifecycle (STIGViewer, SAMS, OpenControls, RegGenome, …). Needed for the benchmark + draft. If not given in the invocation, ask once (`AskUserQuestion`). Product-agnostic best practices can still be produced without it — say so and skip the benchmark.
- **Goal / metric** — the number this stage moves (activation rate, free→paid conversion, NRR, dunning recovery). Default to the stage's canonical KPI (below) if unspecified.

## Stage matrix

Everything the pipeline needs, per stage. `/email-lifecycle` runs all four stages in order.

| Stage (`command`) | Enroll on (events) | Goal event · KPI | Authoring skills (installed) | Adoption-candidate regex (catalog) |
|---|---|---|---|---|
| **activation** (`/email-activation`) | `signup_created`; `email_verified=false`+delay; `first_value` absent (e.g. `first_stig_view`) | first value reached · activation rate | `growth-engineer-skills:onboarding-cro`, `:signup-flow-cro`, `:email-sequence` | `(onboarding|activation|welcome email|first-run|time-to-value|verify|getting started)` |
| **nurture** (`/email-nurture`) | activated-free idle; content/feature engagement; `dayN` cadence | engaged / retained free user · usage depth, return rate | `growth-engineer-skills:email-sequence`, `:copywriting`, `:marketing-psychology`, `moxywolf-skills:voice-injection` | `(nurtur|drip|newsletter|education|re-?engage|lifecycle email|content series)` |
| **convert** (`/email-convert`) | PQL signals: `feature_gate_hit`, `usage_limit_hit`, `viewed_pricing`, repeat high-value use | upgraded to paid · free→paid conversion | `growth-engineer-skills:paywall-upgrade-cro`, `:pricing-strategy`, `saas-pricing-engine:tier-builder` | `(upgrade|paywall|free.?to.?paid|trial conversion|pricing|offer|monetiz|upsell)` |
| **retain** (`/email-retain`) | `upgraded` (welcome-to-paid); `usage_milestone`; `renewal_upcoming`; `payment_failed` (dunning); `churn_risk` | retained / expanded · net revenue retention, dunning recovery | `growth-engineer-skills:churn-prevention`, `:revops` | `(retention|churn|dunning|failed payment|win.?back|expansion|renewal|upsell|save offer)` |

Shared authoring/voice for every stage: read `MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md` before drafting copy; `growth-engineer-skills:copywriting` + `moxywolf-skills:voice-injection` polish it.

## Reference runtime (what the recommendations target)

Recommendations and drafted triggers assume the MoxyWolf reference stack unless the product's setup dictates otherwise:

- **Orchestration + measurement:** PostHog (event-triggered Workflows), which the product already owns. Fallback engine: Loops / Customer.io.
- **Transport:** Resend (`@repo/mail`). Transactional in code (React Email + i18n, engineering-owned via spec/PR); lifecycle bodies in the orchestration engine, marketing-owned.
- **Events:** first-party — the app server captures events via the **PostHog Node SDK**; provider webhooks (Resend delivered/opened/clicked) land in a **first-party backend route**. **No n8n** — it is being retired (team decision; see project memory `project_no_n8n`). Re-home any existing n8n→CRM pipe as a direct server call or a PostHog→Clarify destination.
- **Measurement:** emit `email_sent` on every send + Resend webhooks → PostHog, joined on `message_id`; funnel per stage (sent→opened→clicked→goal), MRR attributed to the driving sequence.

Don't re-propose n8n or a second body store. If the product's real setup differs, benchmark against it and note the delta.

## Pipeline (run for each stage in scope)

### 1. Best practices
State the stage's best practices, concretely and critically. Pull from the stage's installed authoring skills (read their `SKILL.md` or invoke read-only) and top them up with **live external research** (`perplexity_research`, `firecrawl_search`, `research-pipeline:discover-literature`) for current, sourced practice and target benchmarks. Prefer primary/recent sources; flag contested points. Cover: trigger logic, sequence shape (how many, cadence, exit-on-goal), copy/personalization, and the stage's KPI.

### 2. Tooling — have + adopt
List the installed skills to use (from the matrix) **and** query the Workforce Automation catalog for adoption candidates we don't have, using the stage regex:

```sql
with installed as (
  select lower(t.current_name) nm
  from public.tools t join public.sources s on s.id=t.source_id
  where s.name='installed'
)
select t.current_name, left(coalesce(t.current_description,''),150) descr, sr.name source, t.dup_count
from public.tools t join public.sources sr on sr.id=t.source_id
where t.status='active' and coalesce(t.is_canonical,true)=true and sr.name<>'installed'
  and (coalesce(t.current_name,'')||' '||coalesce(t.current_description,'')) ~* :STAGE_REGEX
  and lower(t.current_name) not in (select nm from installed)
order by (sr.name='coreyhaines31/marketingskills') desc, t.dup_count desc nulls last
limit 15;
```

Run it against Supabase project `lmhfgsaznbwnnfldpxgc` via the Supabase MCP `execute_sql`. If that project isn't reachable, note the degradation and fall back to the curated `coreyhaines31/marketingskills` items named in the matrix.

### 3. Benchmark (needs target product)
Read the product's current state for this stage — its email code (transactional templates, trigger hooks), its Taskade `12 – MARCOM` / `08 – Go-to-Market` artifacts, and live signal (PostHog, Clarify, Resend). Mark each best practice: doing it / partial / not doing it / doing the opposite. Grade honestly. If the product's repo/folder isn't mounted, say so and benchmark on whatever is available, flagging "instrument/connect to measure."

### 4. Recommendations
Prioritized, most-costly-gap first, aligned to the reference runtime. No wall-clock estimates — complexity/dependencies only. Name the owner where it's a code surface (transactional = engineering, spec/PR).

### 5. Auto-draft the sequence
Produce the actual sequence for the stage: for each message — trigger event + delay, exit condition, audience/branch, subject line, and a body outline (or full copy for the key messages), in MoxyWolf voice. Prefer to **invoke the stage's installed authoring skill** (`email-sequence`, `onboarding-cro`, `paywall-upgrade-cro`, `churn-prevention`) to generate it; if that skill isn't installed this session, draft directly from the best-practice spec. Mark each message transactional vs marketing (consent/unsubscribe applies to marketing only).

## Output

Write a stage brief to the target product's `12 – MARCOM/` (or `08 – Go-to-Market/`), named `email-<stage>-best-practices-<product>-YYYY-MM-DD.md`, with the five sections above and the drafted sequence appended. Deliver via `SendUserFile`. For `/email-lifecycle`, write one combined document with a section per stage plus an end-to-end trigger map. If the target folder isn't mounted, deliver via `SendUserFile` only and ask where to save it.

## Edge cases

- **No target product given.** Produce product-agnostic best practices + tooling + a template sequence; skip the benchmark; note it.
- **Supabase catalog unreachable.** Tier-2 degrades to the curated pack named in the matrix + external research; say so.
- **Authoring skill not installed.** Draft directly from the best-practice spec; list the skill as an adoption candidate.
- **Product's email lives in a repo/folder not mounted.** Benchmark on available artifacts; flag the unread surface rather than guessing.
- **Stage is `full`.** Run all four stages; dedupe shared recommendations (event spine, measurement) into a single cross-stage section so they aren't repeated four times.

## Notes

- Sibling of `marcom-audit`: `/marcom-best-practices` is the general cross-domain sweep; the `/email-*` commands are the deep, stage-sharded email path. Reuse marcom-audit's three-tier method (installed → catalog → external) here.
- Honor the no-n8n constraint and the single-body-store-per-class rule in every recommendation.
- Reference skills by `plugin:skill` invocation name. No wall-clock estimates; small team, never "solo founder"; never fabricate names or numbers.
