# SparkToro Integration

SparkToro provides audience intelligence (sites, podcasts, follows, talking points by audience segment) that isn't available through general web search or Apify actors. It requires a SparkToro account.

## Data to Request from User

Ask user to run these SparkToro searches and provide results:

### Search 1: Solution Category
**"My audience frequently talks about..."**
Input: Solution category from PR/FAQ
Example: "compliance automation" or "product validation tools"

### Search 2: Competitor Sites
**"My audience frequently visits..."**
Input: Competitor domains
Example: Known competitor websites

### Search 3: ICP Profiles
**"My audience uses these words in their profile..."**
Input: Buyer/User titles from PR/FAQ
Example: "compliance officer" or "product manager"

## Expected Input Format

```
SPARKTORO FINDINGS

Search: [what was searched]
Audience size: [number]

Top Social Accounts:
1. [account] - [followers] - [relevance]
2. [account] - [followers]
3. [account] - [followers]

Top Websites:
1. [domain] - [% of audience]
2. [domain] - [%]
3. [domain] - [%]

Top Podcasts:
1. [podcast] - [% of audience]
2. [podcast] - [%]

Top YouTube Channels:
1. [channel] - [% of audience]
2. [channel] - [%]

Top Subreddits:
1. [subreddit] - [% of audience]
2. [subreddit] - [%]

Keywords Searched:
1. [keyword]
2. [keyword]
3. [keyword]

Demographics:
- Job titles: [list]
- Skills: [list]
```

## Integration Points

### Content Placement Recommendations

Map SparkToro data to awareness stages:

| SparkToro Data | Use For |
|----------------|---------|
| Top Podcasts | Guest appearance priorities by stage |
| Top Websites | Guest post / PR targets |
| Top YouTube Channels | Collaboration opportunities |
| Top Subreddits | Community engagement priorities |
| Social Accounts | Influencer identification |

### Stage Assignment

Categorize each channel/publication by the stage it serves:

- **Stage 2 channels:** Educational, problem-focused content
- **Stage 3 channels:** Review sites, comparison content
- **Stage 4 channels:** Product-focused, decision content

### Keyword Expansion

Add SparkToro keywords to each stage's keyword list:
- Problem-language keywords → Stage 2
- Category/solution keywords → Stage 3
- Product-specific keywords → Stage 4

### ICP Validation

Cross-reference SparkToro demographics with PR/FAQ personas:
- Do job titles match buyer/user?
- Do skills align with expected sophistication?
- Does interest data validate positioning?

## Output Integration

Include SparkToro insights in final report:

```markdown
### Placement Opportunities (from SparkToro)

**Stage 2 Placements:**
- [Podcast 1] - [% of audience] - Educational focus
- [Publication 1] - [% of audience] - Industry coverage

**Stage 3 Placements:**
- [Podcast 2] - [% of audience] - Buyer-focused
- [Review site] - [% of audience] - Comparison content

**Stage 4 Placements:**
- [Subreddit] - [% of audience] - Product discussions
- [Channel] - [% of audience] - Reviews
```
