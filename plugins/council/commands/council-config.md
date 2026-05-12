---
description: View or modify Council plugin settings
allowed-tools: Read, Write, Edit
argument-hint: [show | set <key> <value> | rebuild-router]
---

Manage Council configuration. The config is stored at `${CLAUDE_PLUGIN_ROOT}/skills/deliberation-engine/references/model-configs.md`.

**If no arguments or `show`:**
Read the current model-configs.md and present a summary:
- Current model lineup (slot → model → provider)
- Default size (small/medium/large)
- Temperature and token limits
- Budget default
- Router mode and status

For router status, read `council-memory.json` from the workspace:
- If no memory file: "Router: learned mode (no data yet — all queries go to full deliberation)"
- If memory exists: "Router: {mode} mode | {N} deliberations logged | {M} routing rules | accuracy: {X}%"

**If `set <key> <value>`:**
Edit the relevant section of model-configs.md. Supported keys:
- `analyst`, `strategist`, `challenger`, `synthesist` → swap a model ID (any valid OpenRouter model)
- `temperature` → set default temperature (0.0-1.5)
- `budget` → set default per-deliberation budget in USD
- `chairman` → `highest_ranked` (default — peer review decides) or a specific model ID (always uses that model for synthesis)
- `router` → `learned` (default), `always_deliberate`, or `always_shortcut`

After any change, confirm what was updated and show the new value.

**Router mode details:**

| Mode | Behavior |
|------|----------|
| `learned` | Full routing logic: heuristic fallback when < 20 samples, learned rules when available. The default and recommended mode. |
| `always_deliberate` | Every query goes through the full Council pipeline regardless of type. Useful for building up pattern memory quickly, or when you want maximum answer quality and don't mind the cost. |
| `always_shortcut` | Every query goes to a single model. Useful when you're cost-conscious and want to use the Council's model selection intelligence without the multi-model overhead. |

**If `rebuild-router`:**

Manually trigger a routing model rebuild from the current pattern memory data. This runs pattern-memory Operation 5 (Rebuild Routing Model).

Steps:
1. Read `council-memory.json` from the workspace
2. If fewer than 20 deliberations: warn the user ("Need at least 20 deliberations to build meaningful routing rules. Currently at {N}. Keep deliberating!")
3. If 20+ deliberations: run the rebuild algorithm
4. Report the results:
   - Number of rules generated
   - Rules summary (category → action → confidence)
   - Routing accuracy on historical data
   - Any categories that need more data (between 0.4-0.6 value score)

```
Router rebuilt from {N} deliberations:

Rules:
  architecture_decision → deliberate (confidence: 0.91, value: 0.78, 8 samples)
  compliance_security   → deliberate (confidence: 0.85, value: 0.72, 6 samples)
  factual_lookup        → single_model → openai/gpt-4o (confidence: 0.87, value: 0.22, 5 samples)
  code_implementation   → single_model → openai/gpt-4o (confidence: 0.74, value: 0.31, 4 samples)

Undecided (need more data):
  strategy_business     → deliberating to learn (value: 0.52, 3 samples)
  creative_writing      → deliberating to learn (value: 0.48, 2 samples)

Historical routing accuracy: 82% (18/22 correct decisions)
```

**If `reset-router`:**

Clear all routing rules without deleting deliberation history. Useful if the router's decisions feel off and you want it to re-learn from scratch.

1. Read `council-memory.json`
2. Set `routing_model.rules` to `[]`, `routing_model.last_rebuilt` to `null`, `routing_model.sample_size` to `0`
3. Write the file
4. Confirm: "Router reset. All {N} deliberation records preserved. Router will default to full deliberation until rebuilt."

**If `estimate [flags]`:**

Show estimated cost for a deliberation with the given flags, without running it. Reads current model pricing from `references/model-configs.md` and computes:

```
/council-config estimate --size large --deep --thorough
```

Output:
```
Cost Estimate:
  Stage 1 Round 1 (6 models): ~$0.05-0.08
  Stage 1 Round 2 (--deep):   ~$0.05-0.08
  CI Round (--thorough):       ~$0.03-0.06
  Stage 2 Peer Review:        ~$0.05-0.06
  Stage 3 Synthesis:           ~$0.02-0.04
  ─────────────────────────────────────
  Estimated total:             ~$0.20-0.32

  Flags: --size large --deep --thorough
  Models: 6 (Analyst, Strategist, Challenger, Synthesist, Specialist, Verifier)
  API calls: 25 (6+6+6+6+1)
```

Estimation uses the per-model token pricing from model-configs.md with assumed token counts:
- Stage 1: ~1K input + ~2K output per model
- Deep Round 2: ~9K input (query + 4-6 Round 1 responses) + ~2K output per model
- CI Round: ~9K input + ~2K output per model
- Stage 2: ~8K input + ~500 output per model
- Stage 3: ~10K input + ~3K output

**If `templates`:**

List all available deliberation templates from `references/templates.md`:

```
Available Templates:
  code-review        — Code quality, security, and maintainability review
  architecture       — System design and technology choice evaluation (suggests --deep)
  writing-critique   — Writing quality and persuasion assessment
  research-synthesis — Multi-source research synthesis (suggests --large --deep --thorough)
  compliance-check   — Framework compliance gap analysis
  business-strategy  — Market, competitive, and execution evaluation (suggests --deep)

Usage: /deliberate --template code-review <your code or question>
```
