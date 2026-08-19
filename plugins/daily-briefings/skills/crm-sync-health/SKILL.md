---
name: crm-sync-health
risk_tier: read-only
description: >
  Standalone read-only health check on a CRM sync pipeline in Supabase — stuck runs, budget-exceeded errors, and sources that have gone stale. Use when the user asks whether the CRM sync is healthy, whether a source is stuck or stale, what happened to the pipeline overnight, or invokes /crm-sync-health. Also the skill a scheduled daily run of that check invokes. Reports in one line when everything is at baseline, and leads with the source name and verbatim error detail when it is not. Never fixes anything.
---

# CRM sync health

A standalone check. It assumes no memory of prior runs, because a scheduled firing has none — everything needed to interpret the result is either in this file or in the config.

**Read-only, and that is the whole posture.** Do not fix anything. Do not re-run `sync-all`. Do not change secrets, data, schema, or config. Do not restart a source. If something is broken, say so precisely and stop — the value here is a trustworthy signal, and a checker that also repairs is a checker whose signal you can no longer read.

Read `${CLAUDE_PLUGIN_ROOT}/references/briefing-config.md` for the `crmHealth` block, and `${CLAUDE_PLUGIN_ROOT}/references/source-discipline.md` for the three-state rule, which applies here too: a database you could not reach is `unavailable`, and it must never be reported as a clean pipeline.

---

## Step 1 — Read the config

The `crmHealth` block in `briefings.config.json` carries the target and the baseline:

| Key | What it is |
|---|---|
| `crmHealth.projectId` | Supabase project id |
| `crmHealth.schema` | Schema holding `sync_log` |
| `crmHealth.pipelineSources` | The source names that belong to the ticking pipeline |
| `crmHealth.stuckMinutes` | How long a `running` row may sit before it counts as stuck |
| `crmHealth.staleHours` | How long without an `ok` before a source counts as stale |
| `crmHealth.knownIssues` | Named open issues, so they report as still-open rather than as news |
| `crmHealth.baseline` | The last verified result of the three checks, with its date |

If the block is absent, say so and stop. Do not guess a project id, and do not run this against a database the config does not name.

## Step 2 — Run the three checks

One query, via the Supabase MCP `execute_sql`. Substitute the config values for the schema, the source list, and the two thresholds.

```sql
select '1. stuck runs (>20 min)' as check, count(*)::text as result
from crm.sync_log where status='running' and finished_at is null and started_at < now() - interval '20 minutes'
union all
select '2. budget-exceeded (24h)', coalesce(string_agg(source||':'||n,', '),'none')
from (select source, count(*) n from crm.sync_log
      where status='error' and error_detail like '[elapsed %' and started_at > now()-interval '24 hours'
      group by source) b
union all
select '3. stale PIPELINE sources (no ok in 10h)', coalesce(string_agg(source||' ('||hrs||'h)',', '),'none')
from (select source, round(extract(epoch from (now()-max(finished_at) filter (where status='ok')))/3600,1) as hrs
      from crm.sync_log
      where source in ('sams','aiscrapesafe','stripe','clarify_pull','clarify_events_pull','clarify_mirror',
                       'stigviewer_partner_pull','sams_events_pull','posthog_events_pull','product_pql',
                       'customer_direct_advance','attio_pull','attio_users_mirror','attio_mirror')
      group by source
      having max(finished_at) filter (where status='ok') < now()-interval '10 hours') s;
```

## Step 3 — Read each line against the baseline

### Check 1 — stuck runs

Expected `0`.

A non-zero result means **the wall-clock budget guard did not fire**. Flag that distinctly, because it is a different failure from a source simply being slow: a slow source eventually logs `error`, while an orphan sits at `running` forever and is invisible to any health query that groups on `finished_at`.

The mechanism worth remembering: a serverless isolate killed by the platform runs no JavaScript, so a guard written in JavaScript cannot report its own death. A guard that never fires against a class of failure is not evidence that the class does not happen. Cross-check against check 3 — if the orphans are piling up while every source still has a recent `ok`, the pipeline is running fine and simply leaving corpses behind, which is a bookkeeping failure rather than an outage, and should be described that way.

When check 1 fires, break it down before reporting:

```sql
select source, count(*) n, min(started_at) oldest, max(started_at) newest
from crm.sync_log
where status='running' and finished_at is null and started_at < now() - interval '20 minutes'
group by source order by n desc;
```

Report the per-source counts and the date span. A span tells you whether this is one bad night or a slow accumulation, and those get different responses.

### Check 2 — budget-exceeded

The `[elapsed ` prefix is written only by the guard, so anything here is real rather than inferred.

When a source appears, pull the full row and **quote `error_detail` verbatim**, including the elapsed time and the stack:

```sql
select id, source, started_at, error_detail from crm.sync_log
where error_detail like '[elapsed %' order by started_at desc limit 5;
```

Do not paraphrase an error detail. The verbatim string is the evidence; a summary of it is an opinion.

### Check 3 — stale sources

The pipeline ticks roughly every four hours and GitHub Actions cron drifts by up to an hour and a half, so anything under `staleHours` is not interesting and is not reported.

A source listed in `crmHealth.knownIssues` reports as **still open**, not as news. Give its current number and move on.

**A known-stale source that has dropped back under the threshold has recovered on its own — say so clearly and plainly.** That is the good-news case and it is easy to lose in a report shaped around problems. Someone is waiting to hear it.

Any source here that is not a known issue is new, and leads the report.

## Step 4 — Report

**If checks 1 and 2 are clean and check 3 shows only known issues:** one line. `pipeline healthy, <issue> still stale at Nh.` Nothing more. The whole point of a daily check is that a healthy day costs one line to read.

**If anything else fires:** lead with the source name and the check number, quote `error_detail` verbatim where there is one, and state plainly whether it is a known issue or something new. Say which, in those words — an ambiguous report gets read as noise, and a check that gets read as noise stops getting read.

**If the database could not be reached:** say that, and say that the pipeline state is therefore unknown. Never report an unreachable database as a healthy one.

---

## Boundaries

- Read-only. No fix, no re-run, no restart, no write of any kind, no secret or config change. If the fix is obvious, name it and let a human make it.
- Never runs against a project the config does not name.
- Never paraphrases an `error_detail`.
- Never reports an unreachable source as a clean one.
- Ruled-out causes belong in the project's engineering notes, not in this file — this skill reports state, and it does not re-litigate a diagnosis. Point at the write-up rather than restating it.
