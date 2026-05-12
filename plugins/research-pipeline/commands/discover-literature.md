---
description: Search for sources on a topic using multi-model swarm + academic APIs
argument-hint: [library-name or topic]
---

Load the literature-discovery skill and run both discovery engines:
1. API Engine — OpenAlex, Semantic Scholar, arXiv, web search
2. Multi-Model Swarm — fan out to Perplexity, Gemini, GPT-4o, and DeepSeek
   via OpenRouter, then merge and deduplicate results

If "$ARGUMENTS" matches a library name, expand that library. If it looks like
a topic string, create a new library and run initial discovery.

For the swarm configuration, read `references/openrouter-swarm.md` in the
literature-discovery skill directory.

Steps:
1. Create library (if new topic) or assess existing library state
2. Run API searches across academic databases
3. Run multi-model swarm via OpenRouter (parallel calls to 3-4 models)
4. Merge and deduplicate: API results + swarm results + existing library
5. Score by cross-model agreement (high/medium/low confidence)
6. Validate low-confidence URLs
7. Present ranked candidates grouped by source type, flagging swarm-only finds
8. Ingest user-approved sources into Supabase
9. Run gap analysis and report remaining coverage holes
