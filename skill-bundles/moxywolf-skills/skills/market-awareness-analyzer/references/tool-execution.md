# Tool Execution Guide

## Session Setup

```
RUBE_SEARCH_TOOLS with session: {generate_id: true}
```

Pass returned session_id to ALL subsequent tool calls.

## Execution Sequence

```
1. RUBE_SEARCH_TOOLS → Get session_id, verify connections

2. RUBE_MULTI_EXECUTE_TOOL (Web Search Batch):
   - COMPOSIO_SEARCH_WEB for Stage 2 keywords (3-5)
   - COMPOSIO_SEARCH_WEB for Stage 3 keywords (3-5)
   - COMPOSIO_SEARCH_WEB for Stage 4 keywords (2-3)

3. RUBE_MULTI_EXECUTE_TOOL (Trends Batch):
   - COMPOSIO_SEARCH_TRENDS comparing problem vs solution
   - COMPOSIO_SEARCH_TRENDS with RELATED_QUERIES
   
4. RUBE_MULTI_EXECUTE_TOOL (News + Reddit):
   - COMPOSIO_SEARCH_NEWS for problem + industry
   - REDDIT_SEARCH_ACROSS_SUBREDDITS for problem terms
   - REDDIT_SEARCH_ACROSS_SUBREDDITS for solution terms

5. If SERPAPI connected:
   - SERPAPI_YOU_TUBE_SEARCH for problem content
   - SERPAPI_YOU_TUBE_SEARCH for solution content
```

## Tool Parameters

### COMPOSIO_SEARCH_WEB
```json
{
  "query": "[keyword]"
}
```
Analyze: Content types ranking, competitor presence, SERP intent match.

### COMPOSIO_SEARCH_TRENDS
```json
{
  "query": "problem term, solution term",
  "data_type": "TIMESERIES"
}
```
Or for expansion:
```json
{
  "query": "single term",
  "data_type": "RELATED_QUERIES"
}
```

### COMPOSIO_SEARCH_NEWS
```json
{
  "query": "[problem or industry terms]",
  "when": "m",
  "gl": "us"
}
```

### REDDIT_SEARCH_ACROSS_SUBREDDITS
```json
{
  "search_query": "[problem or solution terms]",
  "sort": "relevance",
  "limit": 50
}
```

### SERPAPI_YOU_TUBE_SEARCH
```json
{
  "query": "[how to + problem] or [solution category]"
}
```

## Interpretation Framework

### Web Search Results
| Result Type | Indicates |
|-------------|-----------|
| Forums/Q&A heavy | Stage 2 market |
| Product pages heavy | Stage 3-4 market |
| Educational blogs | Market being educated |
| Little content | Gap or no market |

### Trend Comparison
| Pattern | Indicates |
|---------|-----------|
| Problem >> Solution | Stage 2 dominant |
| Solution >> Problem | Stage 3-4 dominant |
| Both rising | Growing opportunity |
| Both declining | Saturated market |

### Reddit Sentiment
| Tone | Indicates |
|------|-----------|
| Frustrated, venting | Strong Stage 2 |
| Comparing options | Stage 3 |
| Reviewing products | Stage 4 |
| Resigned, normalized | Hard-to-reach market |

### YouTube Landscape
| Pattern | Indicates |
|---------|-----------|
| Few videos, high views | Content gap |
| Many videos, low views | Saturated |
| Vendor-heavy | Stage 3-4 |
| Educator-heavy | Stage 2 |
