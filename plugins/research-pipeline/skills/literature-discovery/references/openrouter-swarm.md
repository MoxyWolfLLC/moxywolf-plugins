# OpenRouter Multi-Model Swarm Configuration

## API Basics

```
Endpoint: https://openrouter.ai/api/v1/chat/completions
Auth: Bearer token (OPENROUTER_API_KEY)
Required headers:
  - HTTP-Referer: https://moxywolf.com
  - X-Title: MoxyWolf Research Pipeline
```

## Model Roster

### Tier 1: Always Use

| Model | ID | Why | Cost (input/output per M tokens) |
|-------|-----|-----|------|
| Perplexity Sonar Pro | `perplexity/sonar-pro` | Live web search, returns cited URLs. Best ROI — most real sources per dollar. Irreplaceable. | $3/$15 |

### Tier 2: Pair with Perplexity

| Model | ID | Why | Cost |
|-------|-----|-----|------|
| Google Gemini 2.5 Flash | `google/gemini-2.5-flash-preview-05-20` | Fast, strong on government/standards docs. Use Flash not Pro — Pro burns tokens on reasoning before output. | $0.15/$0.60 |
| Anthropic Claude Sonnet | `anthropic/claude-sonnet-4` | Deep reasoning, honest about uncertainty, strong cross-domain connections. Good complement to Perplexity. | $3/$15 |
| DeepSeek Chat | `deepseek/deepseek-chat` | Cheap, fast, good at academic literature. Use Chat not R1 — R1's reasoning causes Rube timeout. | $0.14/$0.28 |

### Models to Avoid

| Model | ID | Why |
|-------|-----|-----|
| OpenAI GPT-4o | `openai/gpt-4o` | **Fabricates URLs.** Every URL it returned in testing was `example.com`. Cannot be trusted for source discovery. |
| DeepSeek R1 | `deepseek/deepseek-r1` | Reasoning phase exceeds Rube MCP 60-second timeout. Use `deepseek-chat` instead. |
| Google Gemini 2.5 Pro | `google/gemini-2.5-pro-preview-05-06` | Spends most of its 3000-token budget on internal reasoning, hits max_tokens before generating output. Use Flash. |

### Tier 3: Specialist (Use for Specific Needs)

| Model | ID | Why | Cost |
|-------|-----|-----|------|
| Meta Llama 4 Scout | `meta-llama/llama-4-scout` | 10M context. Use for processing very large documents or comparing multiple standards simultaneously. | $0.15/$0.40 |

## Prompt Variants

### Standard Discovery Prompt

For initial topic-first discovery. Optimized for breadth.

```json
{
  "model": "{model_id}",
  "messages": [
    {
      "role": "user",
      "content": "You are a research discovery agent. Find ALL significant sources — academic papers, government publications, industry whitepapers, blog posts, conference talks, and standards documents — on this topic:\n\nTOPIC: {topic}\nCONTEXT: {description}\n\nFor each source provide:\n1. Title (exact)\n2. Authors\n3. Year\n4. Type: academic | government | industry | blog | standard | book\n5. URL or DOI (real only, never fabricate)\n6. 2-3 sentence description\n7. Why it's relevant\n\nFind at least 15 sources. Prioritize: seminal works, recent publications (last 3 years), government standards (NIST, DISA, DoD), practitioner perspectives, and contrarian viewpoints.\n\nFormat as JSON array: [{\"title\": \"...\", \"authors\": \"...\", \"year\": 2024, \"type\": \"academic\", \"url\": \"...\", \"doi\": \"...\", \"description\": \"...\", \"relevance\": \"...\"}]"
    }
  ],
  "temperature": 0.3,
  "max_tokens": 4000
}
```

### Gap-Filling Prompt

For targeted expansion when specific gaps are identified.

```json
{
  "model": "{model_id}",
  "messages": [
    {
      "role": "system",
      "content": "You are a research gap analyst. The user has an existing research library and needs sources covering specific missing areas."
    },
    {
      "role": "user",
      "content": "RESEARCH TOPIC: {topic}\n\nEXISTING COVERAGE (themes already well-covered):\n{list_of_covered_themes}\n\nIDENTIFIED GAPS:\n{list_of_gaps}\n\nFind 5-10 sources specifically addressing each gap. Focus on the gaps, not the already-covered themes.\n\nFormat as JSON array with an additional field: \"fills_gap\": \"name of gap this addresses\""
    }
  ],
  "temperature": 0.3,
  "max_tokens": 4000
}
```

### Deep-Dive Prompt

For finding everything on a narrow sub-topic.

```json
{
  "model": "{model_id}",
  "messages": [
    {
      "role": "user",
      "content": "Find every significant source you can on this SPECIFIC sub-topic:\n\nSUB-TOPIC: {narrow_topic}\nBROADER CONTEXT: {library_topic}\n\nI need exhaustive coverage — even obscure sources, conference presentations, working papers, and draft standards. Include sources from outside the US if relevant.\n\nFormat as JSON array."
    }
  ],
  "temperature": 0.4,
  "max_tokens": 6000
}
```

## Merge Algorithm

### Step 1: Normalize

For each source from each model:
- Lowercase and strip punctuation from title
- Extract DOI if embedded in URL (e.g., `doi.org/10.1234/...` → `10.1234/...`)
- Normalize author names to `Surname, Initial.` format
- Parse year as integer

### Step 2: Match

Two sources are considered the same if:
- DOI match (exact, case-insensitive) — highest confidence
- URL match (exact after stripping protocol and trailing slash)
- Title similarity > 85% (Levenshtein ratio on normalized titles)
  AND year matches (±1 year tolerance)

### Step 3: Merge Metadata

When merging duplicates:
- Prefer DOI from any source that has one
- Prefer URL from Perplexity (most likely to be current/valid)
- Prefer abstract/description from the longest version
- Combine `discovered_by` arrays
- Keep the most specific `type` classification

### Step 4: Confidence Score

```
sources_found_by = count of unique models that found this source

confidence:
  3+ models → "high" (almost certainly real)
  2 models  → "medium" (likely real, worth including)
  1 model   → "low" (validate URL before including)
```

### Step 5: Validate Low-Confidence

For sources found by only 1 model:
- If it has a DOI → validate via CrossRef API
- If it has a URL → HEAD request to check for 404
- If neither validates → mark as "unverified" but still present to user
  with a warning flag

## Rate Limits and Parallelism

OpenRouter handles rate limiting per-model. Send requests in pairs via
`RUBE_MULTI_EXECUTE_TOOL`:

```
┌─ POST /chat/completions (perplexity/sonar-pro)
└─ POST /chat/completions (google/gemini-2.5-flash-preview-05-20)
```

Two models in parallel completes within the 60-second Rube timeout.
Three models risks timeout — run the third separately if needed.

If a model fails or times out, proceed without it.
Log the failure but don't block the pipeline.

## Example Cost Breakdown

Actual costs from live testing (March 2026, 2 models):

| Model | Input Cost | Output Cost | Total |
|-------|-----------|-------------|-------|
| Perplexity Sonar Pro | $0.0004 | $0.024 | $0.024 |
| Gemini 2.5 Flash | $0.0003 | $0.007 | $0.007 |
| **Total** | | | **$0.031** |

About 3 cents per discovery run. For weekly scheduled runs across 3 libraries,
that's ~$0.36/month.
