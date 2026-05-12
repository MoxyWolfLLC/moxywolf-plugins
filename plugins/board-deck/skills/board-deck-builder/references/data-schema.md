# Board Deck Data Schema

Complete JSON schema for the board deck data file. See `example-data.json` for a
working February 2026 example.

## Top-Level Structure

```json
{
  "meta": { ... },
  "executiveSummary": { ... },
  "portfolio": [ ... ],
  "northStar": { ... },
  "financials": { ... },
  "stigviewerOKRs": { ... },
  "prfaqOKRs": { ... },
  "samsOKRs": { ... },
  "reggenomeOKRs": { ... },
  "githubVelocity": { ... },
  "reggenomeActivity": { ... },
  "sprint": { ... },
  "risks": [ ... ],
  "decisions": [ ... ]
}
```

## Common Patterns

### Text Items

Many sections use arrays of "items" that can be either plain strings or objects
with styling flags:

```json
// Plain string
"Revenue: $0"

// Object with flags
{
  "text": "Organic Search: +58.39%",
  "highlight": true,
  "highlightColor": "green",
  "muted": false,
  "bold": false
}
```

| Flag | Type | Effect |
|------|------|--------|
| `text` | string | The display text (required for object form) |
| `highlight` | boolean | Adds colored background chip |
| `highlightColor` | string | Color key for highlight: `green`, `yellow`, `red`, `blue` |
| `muted` | boolean | Renders in gray italic |
| `bold` | boolean | Renders in bold |

### Color Keys

Use these keys anywhere a color is referenced. The build script resolves them
to hex values:

```
orange      → FF6B35     dark        → 1A1A2E
darkLight   → 2D2D44     white       → FFFFFF
offWhite    → F5F5F5     gray        → 6B7280
grayLight   → D1D5DB     grayMid     → 9CA3AF
green       → 10B981     greenBg     → ECFDF5
yellow      → F59E0B     yellowBg    → FFFBEB
red         → EF4444     redBg       → FEF2F2
blue        → 3B82F6     blueBg      → EFF6FF
```

---

## Section: `meta`

| Field | Type | Description |
|-------|------|-------------|
| `month` | string | Full month name, e.g. `"February"` |
| `year` | number | Four-digit year, e.g. `2026` |
| `tagline` | string | Board deck tagline |

## Section: `executiveSummary`

| Field | Type | Description |
|-------|------|-------------|
| `headline` | string | One-line performance summary |
| `learning` | string | Key insight or learning this month |
| `obstacle` | string | Primary blocker or challenge |
| `priority` | string | Top priority for next period |

## Section: `portfolio`

Array of 4 product objects (STIGViewer, PRFAQ, SAMS, RegGenome):

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Product name |
| `tof` | string | Top-of-funnel stat, e.g. `"75,799 (-9.59%)"` |
| `tofMuted` | boolean | (optional) Gray out TOF if no data |
| `devStatus` | string | Development status summary |
| `devStatusMuted` | boolean | (optional) Gray out dev status |
| `health` | string | `"On Track"`, `"At Risk"`, or `"Off Track"` |
| `healthColor` | string | Color key: `green`, `yellow`, or `red` |

## Section: `northStar`

Portfolio North Star metric displayed on the Portfolio Dashboard slide (Slide 3).
MoxyWolf's operational North Star is **Milestone Velocity x Revenue Quality**.

| Field | Type | Description |
|-------|------|-------------|
| `formula` | string | Display formula, e.g. `"Milestone Velocity x Revenue Quality"` |
| `currentScore` | string | Current composite score, e.g. `"0.589"` |
| `scoreColor` | string | Color key for score: `green` (good), `yellow` (caution), `red` (poor) |
| `target` | string | Target threshold, e.g. `"<0.75"` |
| `productsScoring` | string | Products below target, e.g. `"2/3 (67%)"` |
| `productsScoringColor` | string | Color key for products scoring indicator |
| `trend` | string | `"Up"`, `"Down"`, or `"Flat"` — drives arrow/diamond icon and color |

## Section: `financials`

| Field | Type | Description |
|-------|------|-------------|
| `leftCards` | array | Array of 4 card objects |
| `rightSections` | array | Array of P&L/balance sheet sections |

**leftCards item:**

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Card title |
| `value` | string | Display value, e.g. `"($38,593)"` |
| `valueColor` | string | Color key: `red`, `dark`, etc. |

**rightSections item:**

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Section heading |
| `bgColor` | string | Background color key: `redBg`, `yellowBg`, `blueBg` |
| `items` | array | Array of strings (line items) |

## Section: `stigviewerOKRs`

| Field | Type | Description |
|-------|------|-------------|
| `kr1Marketing.items` | array | Marketing KR items (text items) |
| `kr2Dev.label` | string | Dev KR label with status |
| `kr2Dev.labelColor` | string | Color key for status |
| `kr2Dev.items` | array | Dev KR items (text items) |
| `kr3Ops.label` | string | Ops KR label with status |
| `kr3Ops.labelColor` | string | Color key for status |
| `kr3Ops.items` | array | Ops KR items (text items) |
| `channels` | array | Channel breakdown (text items) |

## Section: `prfaqOKRs`

| Field | Type | Description |
|-------|------|-------------|
| `kr1Marketing.bigStat` | string | Big number display (e.g. `"41"`) |
| `kr1Marketing.bigStatSub` | string | Subtitle under big number (supports `\n`) |
| `kr1Marketing.items` | array | Marketing items (text items) |
| `kr2Dev.placeholder` | string | Placeholder text if no dev data |
| `productContext` | array | Context bullet points (text items) |
| `keyActions` | array | Array of action strings |

## Section: `samsOKRs`

| Field | Type | Description |
|-------|------|-------------|
| `devLabel` | string | Dev status label |
| `devLabelColor` | string | Color key |
| `devItems` | array | Array of dev task strings |
| `opsLabel` | string | Ops status label |
| `opsLabelColor` | string | Color key |
| `opsItems` | array | Array of ops task strings |
| `footer` | string | Footer text for TOF/metrics |

## Section: `reggenomeOKRs`

| Field | Type | Description |
|-------|------|-------------|
| `devItems` | array | Dev items (text items, can be string or object) |
| `footer` | string | Footer text for TOF/metrics |

## Section: `githubVelocity`

Multi-repo, all-branch commit velocity data from GitHub. Each product with a GitHub
repo gets its own entry in `repos[]`. Commits are deduplicated by SHA within each
repo so feature-branch work that hasn't reached main is still counted.

| Field | Type | Description |
|-------|------|-------------|
| `repos` | array | Per-repo velocity data (see below) |
| `aggregateUniqueCommits` | number | Total unique commits across all repos |
| `aggregateContributors` | number | Total unique contributors across all repos |

**repos item:**

| Field | Type | Description |
|-------|------|-------------|
| `product` | string | Product name: `"STIGViewer"`, `"SAMS"`, etc. |
| `repoName` | string | GitHub repo name, e.g. `"stigviewer"`, `"SAMS"` |
| `owner` | string | GitHub org, e.g. `"MoxyWolfLLC"` |
| `totalBranches` | number | Total branches in the repo |
| `activeBranches` | number | Branches with commits in last 14 days |
| `totalUniqueCommits` | number | Deduplicated commit count for the reporting month |
| `weeklyBreakdown` | array | Per-week commit counts (see below) |
| `contributors` | array | All active contributors across all branches (see below) |
| `branches` | array | Per-branch detail (see below) |
| `staleBranches` | array | Branches with no activity in 14+ days (see below) |
| `velocitySummary` | string | Human-readable summary, e.g. `"47 unique commits across 6 active branches"` |

**weeklyBreakdown item:**

| Field | Type | Description |
|-------|------|-------------|
| `week` | string | Week identifier, e.g. `"W10"` or `"2026-W10"` |
| `commits` | number | Unique commit count for that week |

**contributors item:**

| Field | Type | Description |
|-------|------|-------------|
| `login` | string | GitHub username |
| `commits` | number | Total unique commits by this contributor |
| `branches` | array | Branch names this contributor committed to |

**branches item:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Branch name |
| `category` | string | `"default"`, `"integration"`, `"feature"`, `"hotfix"`, `"release"`, `"other"` |
| `commits` | number | Commits on this branch during the reporting month |
| `lastCommitDate` | string | ISO 8601 timestamp of last commit |
| `topContributor` | string | Author with most commits on this branch |
| `status` | string | `"Active"` or `"Stale"` |

**staleBranches item:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Branch name |
| `lastCommitDate` | string | ISO 8601 timestamp of last commit |
| `daysSinceLastCommit` | number | Days since last activity |
| `author` | string | Last commit author |

## Section: `reggenomeActivity`

Email-derived activity intelligence for RegGenome, sourced from Gmail. Since
RegGenome has no GitHub repo or GA4 property, email is the primary signal for
partnership progress, meeting outcomes, and development activity.

| Field | Type | Description |
|-------|------|-------------|
| `emailSummary` | string | One-line summary, e.g. `"5 threads, 2 partnership responses, 1 meeting transcript"` |
| `threads` | array | Key email threads (see below) |
| `actionItems` | array | Action items extracted from emails (array of strings) |
| `partnershipStatus` | string | Overall partnership pipeline status |

**threads item:**

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | Date of most recent message, e.g. `"2026-02-15"` |
| `subject` | string | Email subject line |
| `participants` | array | Array of participant names/emails |
| `outcome` | string | Key outcome or decision from the thread |
| `highlight` | boolean | (optional) True if this is a significant development |

## Section: `sprint`

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Sprint name |
| `dates` | string | Sprint date range |
| `velocityPct` | number | Velocity as decimal (0.0 – 1.0) |
| `velocityLabel` | string | Formatted velocity display |
| `kpis` | array | Sprint KPI cards (see below) |
| `doneTasks` | array | Array of completed task name strings |
| `inProgress` | array | Array of in-progress task strings |
| `toDo` | array | Array of to-do task strings |

**Sprint KPI item:**

| Field | Type | Description |
|-------|------|-------------|
| `value` | string | The number |
| `label` | string | KPI name (Done, In Progress, etc.) |
| `color` | string | Color key |

## Section: `risks`

Array of risk objects:

| Field | Type | Description |
|-------|------|-------------|
| `priority` | string | `"P0"`, `"P1"`, `"P2"`, `"P3"` |
| `category` | string | `"Technical"`, `"Ops"`, `"Financial"`, etc. |
| `description` | string | Risk description |
| `mitigation` | string | Mitigation plan |
| `color` | string | Color key: `red` (P0), `yellow` (P1), `blue` (P2+) |

## Section: `decisions`

Array of decision objects:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Decision topic |
| `context` | string | Background context |
| `recommendation` | string | Recommended action |
| `color` | string | Color key: `orange`, `blue`, `green` |
