# Tool Execution Guide

The market-awareness-analyzer uses a mix of built-in tools and Apify actors. There is no session-id concept — every call is independent.

## Execution Sequence

```
1. Web search batch (built-in WebSearch, called in parallel via multiple tool invocations):
   - WebSearch for each Stage 2 keyword (3-5 calls)
   - WebSearch for each Stage 3 keyword (3-5 calls)
   - WebSearch for each Stage 4 keyword (2-3 calls)

2. Google Trends (Apify actor):
   - mcp__Apify__call-actor with actorId "apify/google-trends-scraper"
   - One call comparing problem vs solution (TIMESERIES)
   - One call expanding the single dominant term (RELATED_QUERIES)

3. News (built-in WebSearch with site filter, OR Apify news actor):
   - WebSearch query: "[problem terms] news"
   - Filter results by date (last 30 days)
   - For deeper news scraping, use Apify actor "apify/google-news-scraper"

4. Reddit cross-subreddit search (Apify actor):
   - mcp__Apify__call-actor with actorId "trudax/reddit-scraper"
   - One call for problem terms
   - One call for solution terms

5. YouTube landscape (Apify actor, optional):
   - mcp__Apify__call-actor with actorId "apify/youtube-scraper"
   - One call for problem content
   - One call for solution content
```

Tip: Apify actor IDs sometimes change. Use `mcp__Apify__search-actors` with a keyword like "google trends" or "reddit search" to discover current alternatives if a hard-coded ID 404s.

## Tool Parameters

### Built-in `WebSearch`

```
WebSearch:
  query: "[keyword phrase]"
  allowed_domains: ["site1.com", "site2.com"]   # optional
  blocked_domains: ["spam-site.com"]            # optional
```

Analyze: Content types ranking, competitor presence, SERP intent match.

### Apify Google Trends (`apify/google-trends-scraper`)

```json
mcp__Apify__call-actor:
  actor: "apify/google-trends-scraper"
  input: {
    "searchTerms": ["problem term", "solution term"],
    "timeRange": "today 12-m",
    "geo": "US"
  }
```

For related-queries expansion, set `"includeRelatedQueries": true`.

### News via WebSearch

```
WebSearch:
  query: "[problem or industry terms] news 2026"
```

Then filter the result list for recency (most results include published dates). For higher fidelity, use the Apify news actor:

```json
mcp__Apify__call-actor:
  actor: "apify/google-news-scraper"
  input: {
    "queries": "[problem or industry terms]",
    "language": "EN",
    "maxItems": 50
  }
```

### Apify Reddit (`trudax/reddit-scraper`)

```json
mcp__Apify__call-actor:
  actor: "trudax/reddit-scraper"
  input: {
    "searches": ["problem terms", "solution terms"],
    "sort": "relevance",
    "maxItems": 50
  }
```

### Apify YouTube (`apify/youtube-scraper`)

```json
mcp__Apify__call-actor:
  actor: "apify/youtube-scraper"
  input: {
    "searchKeywords": "[how to + problem] OR [solution category]",
    "maxResults": 30
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
