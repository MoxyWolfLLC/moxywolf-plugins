# Pattern Memory JSON Schema

Full JSON Schema for validation of the council-memory.json file. Version 1.2 — includes optimization experiment tracking.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Council Pattern Memory",
  "type": "object",
  "required": ["version", "created", "deliberations", "routing_model", "model_performance", "optimization_log"],
  "properties": {
    "version": {
      "type": "string",
      "enum": ["1.0", "1.1", "1.2"]
    },
    "created": {
      "type": "string",
      "format": "date-time"
    },
    "last_updated": {
      "type": "string",
      "format": "date-time"
    },
    "deliberations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "timestamp", "query_hash", "query_summary", "query_features", "models_used", "rankings", "chairman", "confidence", "cost_usd"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^d_\\d{8}_\\d{3}$",
            "description": "Unique record ID: d_YYYYMMDD_NNN"
          },
          "timestamp": {
            "type": "string",
            "format": "date-time"
          },
          "query_hash": {
            "type": "string",
            "description": "SHA-256 first 8 chars of the query — for dedup, not content storage"
          },
          "query_summary": {
            "type": "string",
            "maxLength": 80,
            "description": "Human-readable summary of the query (no raw content)"
          },
          "query_features": {
            "type": "object",
            "required": ["length", "category", "protocol_used"],
            "properties": {
              "length": {
                "type": "integer",
                "description": "Character count of original query"
              },
              "category": {
                "type": "string",
                "enum": ["architecture_decision", "compliance_security", "code_implementation", "strategy_business", "creative_writing", "factual_lookup", "other"]
              },
              "keywords": {
                "type": "array",
                "items": { "type": "string" },
                "description": "Signal words found in the query"
              },
              "protocol_used": {
                "type": "string",
                "enum": ["voting", "consensus"]
              }
            }
          },
          "models_used": {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 2,
            "maxItems": 6
          },
          "rankings": {
            "type": "object",
            "additionalProperties": { "type": "integer" },
            "description": "Map of model ID → aggregated rank from peer review"
          },
          "chairman": {
            "type": "string",
            "description": "Model ID selected as chairman for synthesis"
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score derived from ranking spread"
          },
          "consensus_level": {
            "type": "string",
            "enum": ["strong", "moderate", "weak", "split"],
            "description": "How much the models agreed: strong (<0.5 std_dev), moderate (0.5-1.0), weak (1.0-1.5), split (>1.5)"
          },
          "cost_usd": {
            "type": "number",
            "description": "Total cost of this deliberation in USD"
          },
          "latency_ms": {
            "type": "integer",
            "description": "Total wall-clock time in milliseconds"
          },
          "self_preference": {
            "type": "object",
            "additionalProperties": { "type": "boolean" },
            "description": "Map of model ID → true for models that ranked their own response >=2 positions higher than consensus. Only models with detected bias are included. Empty object {} if no bias detected."
          },
          "deliberation_value_added": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 1,
            "description": "How much value the full council added over the best individual model response. 0.0 = no value, 1.0 = maximum value. null for single-model shortcut routes (no comparison possible). Primary signal for routing model training."
          },
          "routing_decision": {
            "type": "string",
            "enum": ["deliberate", "single_model"],
            "description": "What the smart-router decided for this query"
          },
          "routing_source": {
            "type": "string",
            "enum": ["heuristic_no_memory", "heuristic_learning", "learned", "explicit_command", "always_deliberate", "always_shortcut"],
            "description": "How the routing decision was made"
          },
          "routing_confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "The router's confidence in its decision"
          },
          "user_rating": {
            "type": ["string", "null"],
            "enum": ["positive", "negative", "neutral", null],
            "description": "User feedback on the deliberation quality"
          },
          "outcome": {
            "type": "string",
            "enum": ["accepted", "rejected", "partial", "unknown"],
            "description": "Whether the user accepted the deliberation result"
          }
        }
      }
    },
    "routing_model": {
      "type": "object",
      "required": ["sample_size", "rules"],
      "properties": {
        "last_rebuilt": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "When the routing rules were last regenerated from data"
        },
        "sample_size": {
          "type": "integer",
          "description": "Number of deliberations used to build current rules"
        },
        "routing_accuracy": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Percentage of past routing decisions that aligned with actual deliberation value outcomes"
        },
        "rules": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["condition", "action", "confidence"],
            "properties": {
              "condition": {
                "type": "string",
                "description": "Rule condition as a simple expression, e.g. \"category == 'architecture_decision'\""
              },
              "action": {
                "type": "string",
                "enum": ["deliberate", "single_model"]
              },
              "preferred_model": {
                "type": "string",
                "description": "For single_model rules: which model to route to"
              },
              "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
              },
              "sample_count": {
                "type": "integer",
                "description": "Number of deliberations that informed this rule"
              },
              "value_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Deliberation value score for this category (>0.6 = deliberate, <0.4 = single)"
              }
            }
          }
        }
      }
    },
    "model_performance": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "deliberations_participated": {
            "type": "integer",
            "description": "Total deliberations this model has been part of"
          },
          "avg_rank": {
            "type": "number",
            "description": "Running average rank across all deliberations"
          },
          "chairman_selections": {
            "type": "integer",
            "description": "How many times this model was selected as chairman"
          },
          "win_rate": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "chairman_selections / deliberations_participated"
          },
          "self_preference_count": {
            "type": "integer",
            "description": "Number of times self-preference bias was detected for this model"
          },
          "self_preference_rate": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "self_preference_count / deliberations_participated — flag if > 0.15"
          },
          "category_ranks": {
            "type": "object",
            "additionalProperties": { "type": "number" },
            "description": "Map of category → average rank in that category"
          },
          "best_categories": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Categories where avg_rank <= 1.5"
          },
          "worst_categories": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Categories where avg_rank >= 3.5"
          }
        }
      }
    },
    "optimization_log": {
      "type": "array",
      "description": "Records from autoresearch optimization runs. Each entry is one experiment.",
      "items": {
        "type": "object",
        "required": ["experiment_id", "timestamp", "variable_modified", "modification_type", "description", "baseline_pass_rate", "modified_pass_rate", "decision", "cost_usd", "benchmark_count"],
        "properties": {
          "experiment_id": {
            "type": "string",
            "pattern": "^opt_\\d{8}_\\d{3}$",
            "description": "Unique experiment ID: opt_YYYYMMDD_NNN"
          },
          "timestamp": {
            "type": "string",
            "format": "date-time"
          },
          "run_id": {
            "type": "string",
            "description": "Groups experiments from the same optimization run. Format: run_YYYYMMDD_HHmmss"
          },
          "variable_modified": {
            "type": "string",
            "description": "Which prompt variable was changed, e.g. 'synthesis_voting_chairman', 'analyst_role'"
          },
          "modification_type": {
            "type": "string",
            "enum": ["sharpen", "constrain", "expand_scope", "restructure", "remove"],
            "description": "The strategy used for this modification"
          },
          "description": {
            "type": "string",
            "description": "Human-readable description of what was changed"
          },
          "baseline_pass_rate": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "modified_pass_rate": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "criteria_delta": {
            "type": "object",
            "properties": {
              "C1_synthesis_superiority": { "type": "number" },
              "C2_peer_review_accuracy": { "type": "number" },
              "C3_multi_model_breadth": { "type": "number" },
              "C4_confidence_calibration": { "type": "number" },
              "C5_budget_compliance": { "type": "number" }
            },
            "description": "Change in pass rate per criterion (positive = improved)"
          },
          "decision": {
            "type": "string",
            "enum": ["keep", "revert", "skip"],
            "description": "Whether the modification was kept, reverted, or skipped"
          },
          "cost_usd": {
            "type": "number",
            "description": "Cost of running this experiment"
          },
          "benchmark_count": {
            "type": "integer",
            "description": "Number of benchmark queries used"
          },
          "benchmark_ids": {
            "type": "array",
            "items": { "type": "string" },
            "description": "IDs of the deliberation records used as benchmarks"
          }
        }
      }
    }
  }
}
```

## Schema Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-28 | Initial schema — Phase 2 release. Added `self_preference` to deliberation records, `self_preference_count` and `self_preference_rate` to model_performance, `value_score` to routing rules, `category_ranks` to model_performance. |
| 1.1 | 2026-03-28 | Phase 3 update. Added `deliberation_value_added`, `routing_decision`, `routing_source`, `routing_confidence` to deliberation records. Added `routing_accuracy` to routing_model. These fields enable the smart-router's learned routing and routing accuracy tracking. |
| 1.2 | 2026-03-28 | Phase 5 update. Added `optimization_log` array for autoresearch experiment tracking. Each experiment records variable modified, modification type, pass rates, criteria deltas, and decision. |
