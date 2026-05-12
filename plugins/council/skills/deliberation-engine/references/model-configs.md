# Model Configurations

Default model lineup and configuration for the Council deliberation pipeline.

---

## Default Lineup (Medium — 4 models)

| Slot | Model ID | Provider | Role | Why This Model |
|------|----------|----------|------|----------------|
| Analyst | `openai/gpt-4o` | OpenAI | Precise, structured | Strong at structured reasoning, code, and quantitative analysis |
| Strategist | `anthropic/claude-sonnet-4` | Anthropic | Nuanced, contextual | Excels at nuanced analysis, long-form reasoning, and considering context |
| Challenger | `google/gemini-2.0-flash` | Google | Fast, contrarian | Fast inference, good at lateral thinking, cost-effective |
| Synthesist | `x-ai/grok-3` | xAI | Cross-domain lateral | Strong general knowledge, unconventional perspectives |

## Small Lineup (2 models)

For quick deliberations or budget-conscious use. Uses only Analyst + Strategist, with Strategist as default chairman.

| Slot | Model ID |
|------|----------|
| Analyst | `openai/gpt-4o` |
| Strategist | `anthropic/claude-sonnet-4` |

## Large Lineup (6 models)

For high-stakes deliberations. Adds two more perspectives.

| Slot | Model ID | Provider | Role |
|------|----------|----------|------|
| Analyst | `openai/gpt-4o` | OpenAI | Precise, structured |
| Strategist | `anthropic/claude-sonnet-4` | Anthropic | Nuanced, contextual |
| Challenger | `google/gemini-2.0-flash` | Google | Fast, contrarian |
| Synthesist | `x-ai/grok-3` | xAI | Cross-domain lateral |
| Specialist | `meta-llama/llama-3.3-70b-instruct` | Meta | Open-source perspective |
| Verifier | `deepseek/deepseek-r1` | DeepSeek | Reasoning chain verification |

## Configuration Parameters

```json
{
  "temperature": 0.7,
  "max_tokens_collect": 2000,
  "max_tokens_review": 800,
  "max_tokens_synthesis": 3000,
  "timeout_per_call_ms": 30000,
  "chairman_selection": "highest_ranked",
  "anonymization": true
}
```

### Parameter Notes

- **temperature 0.7**: Balanced between creativity and consistency. Lower (0.3-0.5) for factual queries, higher (0.8-1.0) for creative tasks. The autoresearch loop (Phase 5) will optimize this per query type.
- **max_tokens_collect 2000**: Enough for a thorough response without bloat. The review prompt penalizes length-without-substance.
- **max_tokens_review 800**: Reviews should be concise — rankings/consensus + brief rationales.
- **max_tokens_synthesis 3000**: Chairman needs room to integrate 4 perspectives thoroughly.
- **timeout 30s**: If a model doesn't respond in 30 seconds, proceed without it.
- **chairman_selection**: `highest_ranked` (Stage 2 winner) or `fixed` (always use a specific model).
- **anonymization**: Always true for peer review. Stage 2 uses "Response A/B/C/D" labels.

## Cost Reference

Approximate cost per call at March 2026 OpenRouter pricing:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|----------------------|
| openai/gpt-4o | $2.50 | $10.00 |
| anthropic/claude-sonnet-4 | $3.00 | $15.00 |
| google/gemini-2.0-flash | $0.10 | $0.40 |
| x-ai/grok-3 | $3.00 | $15.00 |
| meta-llama/llama-3.3-70b-instruct | $0.40 | $0.40 |
| deepseek/deepseek-r1 | $0.55 | $2.19 |

**Budget guardrails:** Before executing Stage 1, estimate total cost based on query length × model count × 3 stages. If estimate exceeds `--budget` (default $0.15), warn the user before proceeding.
