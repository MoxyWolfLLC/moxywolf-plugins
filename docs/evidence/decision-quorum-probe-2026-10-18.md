# Decider council probe, 2026-10-18 (DC-001 criterion 8)

Sent from the Release Owner's Mac (macOS shell; the Cowork device VM's proxy refuses `ai-gateway.vercel.sh` with 403) with `urllib`, no SDK, key from the vault's `aigateway.env`. One body, `POST https://ai-gateway.vercel.sh/v1/decisions`, the `model` field changed per voice and nothing else. The five questions carry MR-002's five names with short one-sentence instructions written for the probe; they are not the production payload. `model_select.mjs` sends longer instructions with the yes/no criteria appended (`councilQuestions()`), and the first production request went out when the selector ran on this item's own packet (council ledger line `7f38d63e26ab`, 2026-10-18, all three voices `floor`). The `input` is a one-paragraph description of DC-001 itself. (Corrected after review 20261018-100213 F8; the first version of this file called the questions verbatim.)

## Result

All three voices answered HTTP 200 with the documented shape: five `predicate` answers in question order, each with `probability`, plus `usage` and `provider_metadata.gateway.cost`. No refusals. No voice is dropped from `DECIDERS`.

| Voice | HTTP | Latency | input_tokens | cost (USD) | trust_boundary | cross_file | docs_only | has_tests | risky |
|---|---|---|---|---|---|---|---|---|---|
| `typesafe-ai/jev` | 200 | 746 ms | 514 | 0.000021588 | 0.67 | 0.85 | 0.04 | 0.56 | 0.74 |
| `perplexity/pplx-decider-v1.2` | 200 | 519 ms | 382 | 0.00000764 | 0.46 | 0.93 | 0.01 | 1.00 | 0.75 |
| `openai/gpt-6-luna-decisions` | 200 | 520 ms | 939 | 0.0000939 | 0.92 | 1.00 | 0.00 | 0.88 | 0.04 |

Read against MR-002's rule table, per voice: Jev gives `floor` by `risky` (0.74 ≥ 0.70); Perplexity gives `floor` by `risky` (0.75); OpenAI gives `floor` by `trust_boundary` (0.92 ≥ 0.30). All three agree on the tier and disagree on why: OpenAI reads `risky` at 0.04 where the other two read it above 0.70, and the three read `trust_boundary` at 0.67, 0.46 and 0.92. That spread, on the very first call, is the reason the council records every voice and not only the majority.

`input_tokens` differs per voice for the same body (514, 382, 939) because each vendor tokenizes its own way; cost is billed on the vendor's count. Per call: about $0.00002 (Jev), $0.000008 (Perplexity Decider), $0.00009 (OpenAI).

## Request body

```json
{
 "input": "Item DC-001: a Python script decider_council.py in plugins/council/scripts that posts typed questions to three decision models on the AI Gateway /v1/decisions endpoint, records every answer on a shared JSONL ledger, computes a majority, and a /decide command. First caller is model_select.mjs. Credentials come from GSTACK_AIGATEWAY_ENV or AI_GATEWAY_API_KEY. Tests: test_decider_council.py against a localhost stub; test_model_select.py gains cases.",
 "questions": [
  {
   "type": "predicate",
   "name": "trust_boundary",
   "instructions": "Does the item change authentication, authorization, payment, credentials, the agent's token or app, a ruleset, a workflow, or anything that decides what an agent may do?"
  },
  {
   "type": "predicate",
   "name": "cross_file",
   "instructions": "Does building it need reasoning across more than one file at once?"
  },
  {
   "type": "predicate",
   "name": "docs_only",
   "instructions": "Is it documentation, configuration, a status line or a version move only?"
  },
  {
   "type": "predicate",
   "name": "has_tests",
   "instructions": "Do the criteria name executable tests?"
  },
  {
   "type": "predicate",
   "name": "risky",
   "instructions": "Does it touch production data, money, credentials or secrets, or an irreversible action such as a migration, a deletion, a send, a payment or a merge to a protected branch?"
  }
 ]
}
```

## Responses, verbatim

### `typesafe-ai/jev`

```json
{
 "answers": [
  {
   "type": "predicate",
   "name": "trust_boundary",
   "probability": 0.67
  },
  {
   "type": "predicate",
   "name": "cross_file",
   "probability": 0.85
  },
  {
   "type": "predicate",
   "name": "docs_only",
   "probability": 0.04
  },
  {
   "type": "predicate",
   "name": "has_tests",
   "probability": 0.56
  },
  {
   "type": "predicate",
   "name": "risky",
   "probability": 0.74
  }
 ],
 "model": "typesafe-ai/jev",
 "provider_metadata": {
  "typesafe": {
   "confidence": {}
  },
  "gateway": {
   "routing": {
    "originalModelId": "typesafe-ai/jev",
    "resolvedProvider": "typesafe-ai",
    "fallbacksAvailable": [
     "digitalocean"
    ],
    "planningReasoning": "System credentials planned for: typesafe-ai, digitalocean. Total execution order: typesafe-ai(system) \u2192 digitalocean(system)",
    "canonicalSlug": "typesafe-ai/jev",
    "finalProvider": "typesafe-ai",
    "modelAttemptCount": 1,
    "modelAttempts": [
     {
      "canonicalSlug": "typesafe-ai/jev",
      "success": true,
      "providerAttemptCount": 1,
      "providerAttempts": [
       {
        "provider": "typesafe-ai",
        "credentialType": "system",
        "success": true,
        "startTime": 1792340803957,
        "endTime": 1792340804081,
        "statusCode": 200
       }
      ]
     }
    ],
    "totalProviderAttemptCount": 1
   },
   "cost": "0.000021588",
   "marketCost": "0.000021588",
   "surchargeCost": "0",
   "gatewayCost": "0.000021588",
   "inferenceCost": "0.000021588",
   "inputInferenceCost": "0.000021588",
   "outputInferenceCost": "0",
   "generationId": "gen_01M57XCG02GFT1RG45N83A4M8B"
  }
 },
 "usage": {
  "input_tokens": 514,
  "output_tokens": 89,
  "total_tokens": 603
 }
}
```

### `perplexity/pplx-decider-v1.2`

```json
{
 "answers": [
  {
   "type": "predicate",
   "name": "trust_boundary",
   "probability": 0.46133006806765825
  },
  {
   "type": "predicate",
   "name": "cross_file",
   "probability": 0.9308282998501608
  },
  {
   "type": "predicate",
   "name": "docs_only",
   "probability": 0.009554578848981218
  },
  {
   "type": "predicate",
   "name": "has_tests",
   "probability": 0.9977457055106295
  },
  {
   "type": "predicate",
   "name": "risky",
   "probability": 0.7529112245560025
  }
 ],
 "model": "perplexity/pplx-decider-v1.2",
 "provider_metadata": {
  "typesafe": {
   "confidence": {}
  },
  "gateway": {
   "routing": {
    "originalModelId": "perplexity/pplx-decider-v1.2",
    "resolvedProvider": "perplexity",
    "fallbacksAvailable": [],
    "planningReasoning": "System credentials planned for: perplexity. Total execution order: perplexity(system)",
    "canonicalSlug": "perplexity/pplx-decider-v1.2",
    "finalProvider": "perplexity",
    "modelAttemptCount": 1,
    "modelAttempts": [
     {
      "canonicalSlug": "perplexity/pplx-decider-v1.2",
      "success": true,
      "providerAttemptCount": 1,
      "providerAttempts": [
       {
        "provider": "perplexity",
        "credentialType": "system",
        "success": true,
        "startTime": 1792340804363,
        "endTime": 1792340804606,
        "statusCode": 200
       }
      ]
     }
    ],
    "totalProviderAttemptCount": 1
   },
   "cost": "0.00000764",
   "marketCost": "0.00000764",
   "surchargeCost": "0",
   "gatewayCost": "0.00000764",
   "inferenceCost": "0.00000764",
   "inputInferenceCost": "0.00000764",
   "outputInferenceCost": "0",
   "generationId": "gen_01M57XCGQJZM1GDZN9FMBKBA90"
  }
 },
 "usage": {
  "input_tokens": 382,
  "output_tokens": 5,
  "total_tokens": 387
 }
}
```

### `openai/gpt-6-luna-decisions`

```json
{
 "answers": [
  {
   "type": "predicate",
   "name": "trust_boundary",
   "probability": 0.92
  },
  {
   "type": "predicate",
   "name": "cross_file",
   "probability": 1
  },
  {
   "type": "predicate",
   "name": "docs_only",
   "probability": 0
  },
  {
   "type": "predicate",
   "name": "has_tests",
   "probability": 0.88
  },
  {
   "type": "predicate",
   "name": "risky",
   "probability": 0.04
  }
 ],
 "model": "openai/gpt-6-luna-decisions",
 "provider_metadata": {
  "openai": {
   "usage": {
    "input_tokens": 939,
    "input_tokens_details": {
     "cached_tokens": 0,
     "cache_write_tokens": 0
    },
    "output_tokens": 0,
    "output_tokens_details": {
     "reasoning_tokens": 0
    },
    "total_tokens": 939
   },
   "confidence": {}
  },
  "gateway": {
   "routing": {
    "originalModelId": "openai/gpt-6-luna-decisions",
    "resolvedProvider": "openai",
    "fallbacksAvailable": [],
    "planningReasoning": "System credentials planned for: openai. Total execution order: openai(system)",
    "canonicalSlug": "openai/gpt-6-luna-decisions",
    "finalProvider": "openai",
    "modelAttemptCount": 1,
    "modelAttempts": [
     {
      "canonicalSlug": "openai/gpt-6-luna-decisions",
      "success": true,
      "providerAttemptCount": 1,
      "providerAttempts": [
       {
        "provider": "openai",
        "credentialType": "system",
        "success": true,
        "startTime": 1792340804873,
        "endTime": 1792340805060,
        "statusCode": 200
       }
      ]
     }
    ],
    "totalProviderAttemptCount": 1
   },
   "cost": "0.0000939",
   "marketCost": "0.0000939",
   "surchargeCost": "0",
   "gatewayCost": "0.0000939",
   "inferenceCost": "0.0000939",
   "inputInferenceCost": "0.0000939",
   "outputInferenceCost": "0",
   "generationId": "gen_01M57XCH70Y53WNEKRNGQGJ7HC"
  }
 },
 "usage": {
  "input_tokens": 939,
  "output_tokens": 0,
  "total_tokens": 939
 }
}
```
