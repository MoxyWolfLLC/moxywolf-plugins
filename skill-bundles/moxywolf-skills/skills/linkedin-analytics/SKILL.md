---
name: linkedin-analytics
description: >
  Generate weekly LinkedIn performance analytics reports by scraping Content and Audience
  analytics pages. Extracts impressions, reach, engagement, follower growth, and demographic
  breakdowns, then compiles a structured markdown report with actionable recommendations.
  Use this skill whenever the user says "LinkedIn analytics", "LinkedIn report", "LinkedIn
  performance", "how is my LinkedIn doing", "weekly LinkedIn update", "LinkedIn numbers",
  "LinkedIn metrics", "run LinkedIn analytics", or "/linkedin-analytics". Also trigger when
  the user asks about their LinkedIn impressions, follower growth, audience demographics, or
  engagement rates in a reporting context. Read-only workflow that never modifies LinkedIn content.
---

# LinkedIn Analytics Report

Generate a comprehensive weekly LinkedIn analytics report by scraping two LinkedIn analytics
pages, extracting all visible metrics, and compiling a structured analysis with actionable
recommendations. The report is saved as a dated markdown file.

## Prerequisites

- Rube MCP tools must be available (for web scraping LinkedIn pages).
- The user must have an active LinkedIn session (logged in via their browser).
- If LinkedIn shows a login gate, CAPTCHA, or blocks access, stop and inform the user.

## Pages to Scrape

| Page | URL | What to Extract |
|------|-----|-----------------|
| Content Analytics | `https://www.linkedin.com/analytics/creator/content/` | Impressions, reach, engagement, top posts |
| Audience Analytics | `https://www.linkedin.com/analytics/creator/audience/` | Followers, growth, demographics |

## Workflow

### Step 1: Initialize Rube Tools

Use `RUBE_SEARCH_TOOLS` with use_case: "scrape or browse a LinkedIn webpage URL to read its content"

Verify the `composio_search` toolkit has an active connection. If not, initiate via `RUBE_MANAGE_CONNECTIONS`.

Store the `session_id` — reuse it for all subsequent tool calls.

### Step 2: Scrape Content Analytics

Fetch `https://www.linkedin.com/analytics/creator/content/` using:

```
RUBE_MULTI_EXECUTE_TOOL
  tool: COMPOSIO_SEARCH_FETCH_URL_CONTENT
  arguments: { "urls": ["https://www.linkedin.com/analytics/creator/content/"], "max_characters": 15000, "text": true }
```

**Fallback chain:**
1. Try `BROWSERLESS_UNBLOCK_PROTECTED_CONTENT` if initial fetch fails
2. If all fetches fail, note "Content analytics unavailable" and proceed to audience page

From the returned content, extract:

**Content Performance:**
- Total Impressions (number and % change vs. prior 7 days)
- Trend shape (flat, steady climb, spike)

**Discovery:**
- Impressions count and % change
- Members Reached count and % change

**Top Performing Posts:**
- Date range shown
- For each post:
  - Post topic (summarize in ~10 words — never reproduce full post text)
  - Whether it was an original post or repost
  - Impression count
  - Reaction count
  - Comment count
  - Repost count

If the raw text is hard to parse, use `invoke_llm` via the Rube workbench to extract structured data from the scraped content.

### Step 3: Scrape Audience Analytics

Fetch `https://www.linkedin.com/analytics/creator/audience/` using the same tool chain.

```
RUBE_MULTI_EXECUTE_TOOL
  tool: COMPOSIO_SEARCH_FETCH_URL_CONTENT
  arguments: { "urls": ["https://www.linkedin.com/analytics/creator/audience/"], "max_characters": 15000, "text": true }
```

From the returned content, extract:

**Follower Overview:**
- Total Followers (number and % change vs. prior 7 days)
- New Followers trend and approximate total gained

**Demographics (all available sections):**
- Job Titles (top 5 with percentages)
- Seniority levels (all shown with percentages)
- Industries (top 5 with percentages)
- Locations (top 5 metro areas with percentages)
- Company Size (all ranges with percentages)
- Companies (top 5 if available)

### Step 4: Compile the Report

Generate a markdown file named `linkedin-analytics-YYYY-MM-DD.md` using today's date.

Use this template structure:

```markdown
# LinkedIn Analytics Report
**Week of [date range from content page, or "ending YYYY-MM-DD" if range unavailable]**

---

## Content Performance

| Metric | This Week | vs. Prior 7 Days |
|---|---|---|
| Impressions | [number] | [+/- %] |
| Members Reached | [number] | [+/- %] |

[2-3 sentences describing the overall trend — what happened, why impressions moved]

### Top Performing Posts ([date range])

| # | Post Topic | Type | Impressions | Reactions | Comments | Reposts |
|---|---|---|---|---|---|---|
| 1 | [~10 word summary] | [Original/Repost] | [n] | [n] | [n] | [n] |

### What Worked

[Analysis of the top post — why it performed well, what hook/topic/format drove engagement]

### Engagement Rate

[Calculate: (reactions + comments + reposts) / impressions for the top post.
Compare to LinkedIn benchmark of ~1-2% average engagement rate.]

---

## Audience Insights

### Followers

| Metric | Value |
|---|---|
| Total Followers | [n] |
| Growth vs. Prior 7 Days | [+/- %] |

[1-2 sentences on follower growth trend]

### Demographics Breakdown

**Job Titles (Top 5)**

| Title | % of Followers |
|---|---|
| [title] | [%] |

**Seniority**

| Level | % |
|---|---|
| [level] | [%] |

[Note what % of audience is Senior/CXO/Director/Owner level combined]

**Industries (Top 5)**

| Industry | % |
|---|---|
| [industry] | [%] |

**Locations (Top 5)**

| Metro Area | % |
|---|---|
| [metro] | [%] |

**Company Size**

| Size | % |
|---|---|
| [range] | [%] |

[1-2 sentences interpreting the audience: who they are, whether they're decision-makers, what verticals dominate]

---

## Recommendations for This Week

1. **[Action based on top-performing content]**
   [Specific next step to capitalize on what worked]

2. **[Action based on engagement patterns]**
   [Content format, timing, or topic suggestion]

3. **[Action based on audience composition]**
   [How to tailor content to actual audience demographics]
```

### Step 5: Deliver

Save the report to `/mnt/user-data/outputs/linkedin-analytics-YYYY-MM-DD.md`.

Present a 3-4 sentence executive summary in the chat covering:
- Headline impressions number and trend direction
- Top post performance and engagement rate
- Follower growth
- One standout audience insight

Then share the file using `present_files`.

## Rules

- **Read-only**: This workflow only reads analytics pages. Never interact with any UI element that would post, delete, edit, follow, connect, or modify any LinkedIn content or settings.
- **Copyright**: Summarize post content in your own words (~10 words). Never reproduce full post text.
- **Missing data**: If a metric is not visible or the page layout has changed, note it as "Not available" in the report and continue with what is visible. A partial report is better than no report.
- **Errors**: If LinkedIn requires login, shows a CAPTCHA, or blocks access, stop immediately and inform the user. Do not retry aggressively.
- **Privacy**: Demographic data is aggregate (percentages), not individual. Treat it accordingly.
- **Calculations**: When computing engagement rates, show your formula so the user can verify.

## Handling Parse Difficulties

LinkedIn analytics pages can be complex. If the raw scraped text is hard to parse directly:

1. Use `RUBE_REMOTE_WORKBENCH` with `invoke_llm` to extract structured JSON from the raw page content
2. Define the exact fields you need in the LLM prompt
3. Parse the structured output to populate the report template

Example approach:
```python
raw_content = "..."  # from the fetch result
prompt = f"""Extract LinkedIn analytics from this page content as JSON:
{{
  "impressions": {{"count": number, "change_pct": string}},
  "members_reached": {{"count": number, "change_pct": string}},
  "posts": [
    {{"summary": "10-word topic summary", "type": "Original|Repost",
      "impressions": number, "reactions": number, "comments": number, "reposts": number}}
  ]
}}

Page content:
{raw_content[:8000]}"""

result, error = invoke_llm(prompt, reasoning_effort="medium")
```

## Alternate Execution Path: Claude in Chrome

If Claude in Chrome browser tools are available instead of Rube, the workflow adapts:

1. Use `tabs_context_mcp` with `createIfEmpty: true` to get a browser tab
2. Navigate to each analytics URL using `navigate`
3. Wait 3 seconds for page load, then use `read_page` or `get_page_text` to extract content
4. Use `computer` to scroll down and capture additional sections
5. Take screenshots at each major page for verification

The report compilation and delivery steps remain identical regardless of which scraping method is used.
