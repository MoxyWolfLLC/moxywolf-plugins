---
read_when: "synergy-discover loads this to call the right Apify actor with the right input. Both actors are no-cookie, pay-per-result, harvestapi."
status: canonical
---

# Apify actors for discovery

Both run via `mcp__Apify__call-actor` (or the dedicated tool). Pull results with `mcp__Apify__get-dataset-items`. They're pay-per-result (~$0.002/post), no LinkedIn cookies needed.

## Author center — `harvestapi/linkedin-profile-posts`

Actor id `A3cAPGpwBEG8RJwse`. Pulls recent posts for a list of profiles.

Input (key fields):

```json
{
  "targetUrls": ["https://www.linkedin.com/in/<slug>/", "..."],
  "maxPosts": 10,
  "postedLimit": "month",
  "includeReposts": true,
  "includeQuotePosts": true,
  "scrapeReactions": false,
  "scrapeComments": false
}
```

- `targetUrls` must be full `linkedin.com/in/<slug>/` (or `/company/<slug>`) URLs. Resolve names → profile URLs first (web search, allowed_domains linkedin.com).
- `postedLimit`: `any | 1h | 24h | week | month | 3months | 6months | year`.

## Content center — `harvestapi/linkedin-post-search`

Actor id `buIWk2uOUzTmcLsuB`. Searches recent posts by query.

Input (key fields):

```json
{
  "searchQueries": ["prove what your AI did", "AI governance audit trail", "..."],
  "maxPosts": 12,
  "postedLimit": "month",
  "sortBy": "relevance",
  "scrapeReactions": false,
  "scrapeComments": false,
  "profileScraperMode": "short"
}
```

- `searchQueries` are LinkedIn search-bar strings — use high-signal phrases and signature phrases from the fingerprint, not generic terms (generic governance terms return vendor/recruiter noise).
- `sortBy`: `relevance` (best fit) or `date` (freshest). Also supports `authorUrls`, `authorKeywords`, `authorsCompanies`, `mentioningMember/Company`, `contentType`.

## Reading results

`get-dataset-items` with a projected `fields=` list keeps the payload small. Useful fields: `author.name`, `author.publicIdentifier`, `author.info`, `content`, `repost.content`, `postedAt.postedAgoText`, `engagement.likes`, `engagement.comments`, `linkedinUrl`, `query.search`.

If the projected result still exceeds the context limit, the tool saves it to a file. Don't try to chunk it with line offsets — delegate scoring to a subagent: hand it the file path, the fingerprint themes, the exclude-list (publicIdentifiers already in the tracker), and the output contract (ranked synergy cards), and have it return only the cards.

## Dedupe + cost

Always pass the tracker's existing `publicIdentifier`s as an exclude-list to scoring so already-engaged authors don't resurface. Cap `maxPosts` and the query count to keep cost in cents; a content sweep of ~6 queries x 12 posts is ~$0.15.
