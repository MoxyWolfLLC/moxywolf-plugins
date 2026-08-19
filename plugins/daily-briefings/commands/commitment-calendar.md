---
description: "Build the rolling N-day commitment calendar as a self-contained HTML file — calendar, inbox, and every configured work surface, with clash and unprepped-deadline flags. Usage: /commitment-calendar [days] [--full]"
argument-hint: "[days] [--full]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "SendUserFile", "WebFetch", "mcp__Google_Calendar__list_calendars", "mcp__Google_Calendar__list_events", "mcp__Gmail__search_threads", "mcp__Gmail__get_thread", "mcp__Atlassian_Rovo__searchJiraIssuesUsingJql", "mcp__Atlassian_Rovo__getAccessibleAtlassianResources", "mcp__Github__list_pull_requests", "mcp__Github__list_issues", "mcp__Github__list_releases", "mcp__Vercel__list_deployments", "mcp__Vercel__get_domain_order", "mcp__Supabase__get_advisors", "mcp__Postiz__postsListTool", "mcp__remote-devices__publora__list_posts", "mcp__Apollo_io__apollo_tasks_search", "mcp__Clarify__get-campaigns", "mcp__Clarify__get-calendar-events", "mcp__Clarify__query-data", "mcp__Ahrefs__rank-tracker-overview", "mcp__Ahrefs__site-audit-issues", "mcp__Ahrefs__brand-radar-mentions-overview", "mcp__PostHog__exec", "mcp__Intuit_QuickBooks__qbo_accounting_get_ar_aging_summary", "mcp__Intuit_QuickBooks__qbo_accounting_get_ap_aging_summary", "mcp__Intuit_QuickBooks__qbo_sales_get_invoices", "mcp__Intuit_QuickBooks__qbo_payroll_get_pay_schedules", "mcp__Intuit_QuickBooks__qbo_payroll_get_company_payroll_readiness", "mcp__Docusign__getAllAgreements", "mcp__Docusign__getEnvelopes", "mcp__LivePlan__get_milestones", "mcp__Monarch__GetRecurring", "mcp__claude-code-remote__list_triggers", "mcp__remote-devices__get_device_info", "mcp__remote-devices__device_request_folder_access", "mcp__remote-devices__device_commit_files", "mcp__remote-devices__Control_Chrome__open_url", "mcp__remote-devices__Control_your_Mac__osascript"]
---

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/commitment-calendar/SKILL.md` and follow it end to end. The surface sweep in Step 3b is defined in `${CLAUDE_PLUGIN_ROOT}/references/work-surfaces.md`.

Arguments:

- a number is the window length in days, overriding `window.days` for this run only. It does not change the config.
- `--full` runs every surface regardless of tier, including the `weekly` ones. Use it when the question is "what am I forgetting" rather than "what is today."

Without `--full`, an ad-hoc run does the `always` surfaces and skips the `daily` ones; a scheduled run does both. Either way, every skipped surface is named in the footer with its reason — a skip is never silent.

Not every connector in the tool list will be available in every session, and that is expected. An unavailable surface is recorded as `unavailable` and named in the footer. It is never rendered as an empty result, and it is never a reason to abandon the run.

If this is a scheduled or otherwise unattended run, do not ask clarifying questions — resolve from the config and put anything unresolved in the footer caveats.
