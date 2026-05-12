# Data Collection Guide

Step-by-step instructions for collecting monthly board deck data from each source.
All data goes into a single JSON file following the schema in `data-schema.md`.

## Source 1: LivePlan (Financials)

LivePlan provides cash position, burn rate, P&L, balance sheet, and revenue data.

### Steps

1. Open LivePlan dashboard at https://app.liveplan.com
2. Navigate to **Dashboard > Forecast vs Actual**
3. Collect the following for the current month and prior month:

| Field | Where to Find | JSON Path |
|-------|--------------|-----------|
| Cash Position | Dashboard > Cash balance | `financials.leftCards[0].value` |
| Monthly Burn | P&L > Total Expenses (prior month) | `financials.leftCards[1].value` |
| MTD Burn | P&L > Total Expenses (current month) | `financials.leftCards[2].value` |
| Revenue | P&L > Total Revenue | `financials.leftCards[3].value` |

4. Navigate to **Reports > Profit & Loss** for the prior full month:
   - Record: Revenue, Total Expenses, Expense breakdown (%), Net Profit
   - Note variance vs forecast (%)

5. Navigate to **Reports > Profit & Loss** for the current MTD:
   - Record: Revenue, Total Expenses, breakdown, Net Profit
   - Note pacing vs forecast

6. Navigate to **Reports > Balance Sheet**:
   - Record: Cash Balance, Accounts Receivable, Accounts Payable, Net Cash Flow
   - Note month-over-month change (%)

### Formatting Rules

- Negative values: wrap in parentheses, e.g. `($38,593)`
- Use `red` valueColor for negative cash or zero revenue
- Use `dark` valueColor for neutral values
- P&L sections use background colors: `redBg` for loss months, `yellowBg` for caution, `blueBg` for balance sheet

## Source 2: GA4 (Top-of-Funnel Analytics)

GA4 provides sessions, channel breakdown, engagement rates, and key events per product.

### Steps

1. Open Google Analytics at https://analytics.google.com
2. For each product with a GA4 property (currently STIGViewer and PRFAQ):

**STIGViewer GA4:**

3. Set date range to the reporting month
4. Navigate to **Reports > Acquisition > Traffic acquisition**
5. Collect:

| Metric | JSON Path |
|--------|-----------|
| Total sessions | `portfolio[0].tof` — format as `"75,799 (-9.59%)"` with MoM % |
| Organic Search sessions | `stigviewerOKRs.channels` and `kr1Marketing.items` |
| Direct sessions | `stigviewerOKRs.channels` |
| Referral sessions | `stigviewerOKRs.channels` |
| Engagement Rate | `stigviewerOKRs.kr1Marketing.items` — format as `"33.54% (+69.59%)"` |
| Key Events count | `stigviewerOKRs.kr1Marketing.items` |

6. Calculate MoM percentages by comparing to prior month's data.

**PRFAQ GA4:**

7. Switch to the PRFAQ property
8. Collect total sessions, engagement rate, engaged sessions, traffic sources
9. Map to `prfaqOKRs.kr1Marketing`

**SAMS & RegGenome:**

- If no GA4 property exists, set `tofMuted: true` and `tof: "No GA4 property"`

### Formatting Rules

- Always include MoM percentage change: `"75,799 (-9.59%)"`
- Highlight strong growth with `{ "highlight": true, "highlightColor": "green" }`
- Use `muted: true` for metrics that need input or are unavailable

## Source 3: Taskade (Sprint & Task Data)

Taskade provides sprint progress, story points, task status, and velocity.

### Steps

1. Open Taskade workspace
2. Navigate to the current sprint board
3. Collect task counts by status:

| Status | JSON Path |
|--------|-----------|
| Done tasks | `sprint.doneTasks` (array of task name strings) |
| In Progress tasks | `sprint.inProgress` (array with priority/points) |
| To Do tasks | `sprint.toDo` (array with priority/points) |
| Blocked tasks | Count for `sprint.kpis` |
| Bugs | Count + status for `sprint.kpis` |

4. Calculate velocity:
   - Sum story points of Done tasks
   - Divide by total sprint story points
   - Record as decimal: `sprint.velocityPct` (e.g., `0.528`)
   - Format label: `sprint.velocityLabel` (e.g., `"52.8%  (28/53 story points)"`)

5. Map sprint metadata:
   - `sprint.title`: Sprint name (e.g., "Sprint Command: STIGViewer Go-Live")
   - `sprint.dates`: Date range (e.g., "Feb 7 – Feb 16, 2026")

6. Map per-product OKR dev sections:
   - STIGViewer: `stigviewerOKRs.kr2Dev` and `kr3Ops`
   - SAMS: `samsOKRs.devItems` and `opsItems`
   - RegGenome: `reggenomeOKRs.devItems`
   - PRFAQ: `prfaqOKRs.kr2Dev`

### Formatting Rules

- In-progress tasks include priority and points: `"STIGViewer Final Branding Cleanup (Critical, 8 pts)"`
- Sprint KPI colors: `green` for good, `yellow` for caution, `gray` for neutral
- Use `highlight: true` for notable achievements

## Source 4: GitHub (All-Branch Commit Velocity)

GitHub provides per-branch commit activity, contributor data, and true development
velocity across ALL active branches. This is essential because SAMS (and other products
with GitHub repos) uses a main → develop → feature/* branching workflow where most
work happens on feature branches that aren't merged to main until go-live. Measuring
only the default branch drastically undercounts actual development velocity.

### Steps

1. Use Rube `GITHUB_LIST_BRANCHES` tool for each product repo with a GitHub presence:
   - **STIGViewer**: owner `MoxyWolfLLC`, repo `stigviewer`, per_page 100
   - **SAMS**: owner `MoxyWolfLLC`, repo `SAMS`, per_page 100

2. For EACH repo above, and for EACH branch returned, use `GITHUB_LIST_COMMITS` with:
   - owner: `MoxyWolfLLC`
   - repo: [repo name — `stigviewer` or `SAMS`]
   - sha: [branch name]
   - since: first day of reporting month (ISO 8601)
   - until: last day of reporting month (ISO 8601)
   - per_page: 100

3. Collect per branch:

| Metric | Description |
|--------|-------------|
| Branch name | The branch identifier |
| Category | `default`, `integration`, `feature`, `hotfix`, `release`, `other` |
| Commits (period) | Total commits on this branch during the reporting month |
| Last commit date | Most recent commit timestamp |
| Top contributor | Author with the most commits on this branch |
| Active contributors | All authors + commit counts |

4. **Deduplicate commits by SHA** across branches to compute true project-wide velocity.
   The same commit appears on multiple branches after merges — count each unique SHA
   only once for the aggregate total.

5. Map to JSON — the `githubVelocity` section is now **per-repo**, keyed by product name:

| Metric | JSON Path |
|--------|-----------|
| Per-repo velocity | `githubVelocity.repos[]` (one entry per repo) |
| Repo name | `githubVelocity.repos[].repoName` |
| Product name | `githubVelocity.repos[].product` |
| Total active branches | `githubVelocity.repos[].totalBranches` |
| Total unique commits | `githubVelocity.repos[].totalUniqueCommits` |
| Weekly breakdown | `githubVelocity.repos[].weeklyBreakdown[]` |
| Contributors | `githubVelocity.repos[].contributors[]` |
| Per-branch detail | `githubVelocity.repos[].branches[]` |
| Stale branches | `githubVelocity.repos[].staleBranches[]` |
| Velocity summary | `githubVelocity.repos[].velocitySummary` |
| Cross-repo aggregate | `githubVelocity.aggregateUniqueCommits` |
| Cross-repo contributors | `githubVelocity.aggregateContributors` |

6. **Enrich product OKR dev sections** with GitHub data:
   - **STIGViewer**: add commit velocity to `stigviewerOKRs.kr2Dev.items` (e.g., `"GitHub: 85 commits across 4 branches"`)
   - Update `portfolio[0].devStatus` (STIGViewer) to include commit count alongside Taskade tasks
   - **SAMS**: add commit velocity to `samsOKRs.devItems` (e.g., `"GitHub: 47 commits across 6 branches"`)
   - Update `portfolio[2].devStatus` (SAMS) to include commit count alongside Taskade tasks
   - For any product with a GitHub repo, the `devStatus` field should reflect both
     Taskade task progress AND GitHub commit velocity

### Formatting Rules

- Branch status: `"Active"` (commits in last 14 days), `"Stale"` (>14 days no activity)
- Contributor format: `"username (N commits)"`
- Weekly breakdown format: `"W10: 12 commits"`
- Highlight high-activity branches: `{ "highlight": true, "highlightColor": "green" }`
- Use `"muted": true` for stale branches
- Velocity summary: `"47 unique commits across 6 active branches (3 contributors)"`

## Source 5: Gmail (RegGenome Activity Intelligence)

RegGenome does not have a GitHub repo or GA4 property, so its development and
partnership activity is tracked through email. Use Rube `GMAIL_FETCH_EMAILS` to
search Dorian's inbox for RegGenome-related transcripts, meeting notes, and
correspondence from the reporting month.

### Steps

1. Use Rube `GMAIL_FETCH_EMAILS` with:
   - query: `reggenome after:YYYY/MM/01 before:YYYY/MM+1/01` (reporting month boundaries)
   - max_results: 50
   - include_payload: true

2. Also search for related terms that may appear without "reggenome" explicitly:
   - query: `(reggenome OR "regulatory genome" OR "reg genome") after:YYYY/MM/01 before:YYYY/MM+1/01`

3. For each matching email/thread, extract:
   - Subject line
   - Date
   - Participants (from/to)
   - Key action items or decisions mentioned
   - Meeting transcript summaries (if transcript attachments present)

4. Synthesize into RegGenome activity items:
   - Partnership outreach status (emails sent/received, responses)
   - Meeting outcomes and decisions
   - API integration discussions
   - Any commitments or deadlines mentioned

5. Map to JSON:

| Metric | JSON Path |
|--------|-----------|
| Email activity summary | `reggenomeActivity.emailSummary` |
| Key threads | `reggenomeActivity.threads[]` |
| Action items found | `reggenomeActivity.actionItems[]` |
| Partnership status | `reggenomeActivity.partnershipStatus` |

6. **Enrich RegGenome OKR dev sections** with email intelligence:
   - Update `reggenomeOKRs.devItems` with partnership/meeting activity
   - Update `portfolio[3].devStatus` (RegGenome) to reflect email-derived progress
   - Replace generic "Needs input" placeholders with actual data from emails

### Formatting Rules

- Thread format: `"[Date] Subject — key outcome"`
- Use `"highlight": true` for significant partnership responses or meeting outcomes
- Use `"muted": true` for outreach with no response yet

## Manual Inputs

Some fields require manual input each month:

| Field | JSON Path | Source |
|-------|-----------|--------|
| Executive Summary headline | `executiveSummary.headline` | Founder summary |
| Executive Summary learning | `executiveSummary.learning` | Founder reflection |
| Executive Summary obstacle | `executiveSummary.obstacle` | Current blockers |
| Executive Summary priority | `executiveSummary.priority` | Next month focus |
| KPIs (MRR, Customers, etc.) | `kpis.*` | Product metrics |
| Risks | `risks[]` | Risk assessment |
| Strategic Decisions | `decisions[]` | Board discussion items |
| Month/Year/Tagline | `meta.*` | Current period |
