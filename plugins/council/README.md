# Council — Multi-Model AI Deliberation

Four AI models debate so you get a better answer, the system gets smarter every time you use it, and now it remembers what it learned.

Council gives any Cowork user access to structured multi-model deliberation. Instead of relying on a single model's response, Council collects independent answers from multiple LLMs, has them peer-review each other anonymously, and synthesizes the best insights into one authoritative answer.

The smart router learns which questions actually benefit from full deliberation. The autoresearch loop systematically improves deliberation prompts from your actual usage data. And starting in v0.6.0, the Obsidian vault integration means Council reads organizational context before deliberating and writes decision records back to the vault afterward. Verification becomes institutional knowledge.

No backend required. Runs entirely inside Cowork using Rube's OpenRouter connection.

## Setup

1. Install the plugin in Cowork
2. Ensure you have an active [Rube](https://rube.sh) connection with OpenRouter enabled
3. Run `/deliberate` with any question

On first use, if your OpenRouter connection isn't active, the plugin will provide an authentication link.

## Commands

| Command | Description |
|---------|-------------|
| `/deliberate <question>` | Run a multi-model deliberation (always uses full council) |
| `/council-config` | View or modify model lineup, router mode, and settings |
| `/council-stats` | View performance metrics, routing accuracy, and deliberation history |
| `/council-optimize` | Run the autoresearch loop to self-improve deliberation prompts |

### /deliberate Options

```
/deliberate What's the best approach to implementing RBAC for multi-tenant SaaS?

/deliberate --size small Should I use Postgres or DynamoDB for this use case?

/deliberate --fast --budget 0.05 Explain the difference between OAuth and OIDC

/deliberate --thorough Compare microservices vs monolith for an early-stage startup
```

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--size` | small, medium, large | medium | 2, 4, or 6 models |
| `--fast` | flag | off | Skip peer review (collect + synthesize only) |
| `--deep` | flag | off | MoA two-round collection — models see all Round 1 responses before re-answering |
| `--thorough` | flag | off | Add Collective Improvement round |
| `--template` | name | none | Use a pre-built template (code-review, architecture, writing-critique, research-synthesis, compliance-check, business-strategy) |
| `--models` | comma-separated IDs | from config | Override model selection |
| `--budget` | dollar amount | 0.15 | Max cost for this deliberation |

### /council-config Options

```
/council-config show                              # View current settings
/council-config set analyst meta-llama/llama-3.3-70b-instruct  # Swap a model
/council-config set router always_deliberate      # Change router mode
/council-config rebuild-router                    # Manually rebuild routing rules
/council-config reset-router                      # Clear routing rules (keep history)
/council-config estimate --size large --deep      # Estimate cost for a deliberation
/council-config templates                         # List available deliberation templates
```

### /council-optimize Options

```
/council-optimize                                 # Run with defaults ($2.00 budget)
/council-optimize --budget 5.00                   # Larger optimization budget
/council-optimize --dry-run                       # Preview plan without running
/council-optimize --variable analyst_role          # Target a specific prompt variable
```

## Skills

| Skill | Phase | Description |
|-------|-------|-------------|
| deliberation-engine | 6 (Active) | Core 3-stage pipeline with vault context injection, smart-router gate, MoA deep mode, templates, autoresearch, and post-deliberation vault writes |
| pattern-memory | 6 (Active) | Persistent learning with vault sync — logs outcomes, tracks value-added, detects self-preference bias, stores optimization experiments, syncs to Obsidian vault every 5th deliberation |
| smart-router | 5 (Active) | Learned routing — heuristic fallback → data-driven rules after 20+ deliberations |

## How It Works

**Routing:** Before anything runs, the smart router evaluates your query. Simple factual questions go to a single model (~$0.01). Complex decisions, comparisons, and strategy questions go to the full council (~$0.08-0.12). The router starts conservative (deliberate on everything) and learns from outcomes.

**Stage 1 — Collect:** Four models answer your question independently, each with a different perspective (Analyst, Strategist, Challenger, Synthesist).

**Stage 2 — Peer Review:** Each model reviews the other three responses anonymously. The review protocol adapts by query type: voting for reasoning questions, consensus for knowledge questions.

**Stage 3 — Synthesize:** The highest-ranked model becomes chairman and synthesizes all insights into one unified answer, flagging where models agreed (high confidence) and disagreed (needs your judgment).

**Learning:** Every outcome is logged — model rankings, deliberation value-added, routing decisions, and your feedback. After 20+ deliberations, the router builds data-driven rules that get smarter over time.

**Templates:** Pre-built context wrappers for common scenarios — code review, architecture decisions, writing critique, research synthesis, compliance checks, and business strategy. Each template frames the question and suggests optimal flags.

**Self-Improvement:** After 3+ rated deliberations, `/council-optimize` runs an autoresearch loop that systematically tests prompt modifications against your real usage data and keeps only changes that improve deliberation quality.

## Cost

- **Full deliberation (medium, 4 models):** ~$0.08-0.12
- **Full deliberation (fast mode):** ~$0.05
- **Full deliberation (deep mode):** ~$0.14-0.20
- **Full deliberation (thorough mode):** ~$0.12-0.16
- **Full deliberation (deep + thorough):** ~$0.20-0.32
- **Single-model shortcut:** ~$0.005-0.02
- **Optimization experiment:** ~$0.08-0.12 per benchmark query

The router automatically reduces cost by routing simple queries to single models once it has enough data to make confident decisions. Use `/council-config estimate` to preview cost for any flag combination.

## Default Model Lineup

| Slot | Model ID | Provider |
|------|----------|----------|
| Analyst | `openai/gpt-4o` | OpenAI |
| Strategist | `anthropic/claude-sonnet-4` | Anthropic |
| Challenger | `google/gemini-2.0-flash` | Google |
| Synthesist | `x-ai/grok-3` | xAI |

Customize via `/council-config set analyst meta-llama/llama-3.3-70b-instruct` or any OpenRouter model ID. The router also learns which models perform best for different query categories and adjusts recommendations automatically.

## Router Modes

| Mode | Set via | Behavior |
|------|---------|----------|
| `learned` (default) | `/council-config set router learned` | Smart routing: heuristics → learned rules |
| `always_deliberate` | `/council-config set router always_deliberate` | Every query gets full council |
| `always_shortcut` | `/council-config set router always_shortcut` | Every query goes to single best model |

## Roadmap

- **Phase 1** ✅: Core deliberation pipeline with 3 commands
- **Phase 2** ✅: Persistent pattern memory — outcomes logged, model performance tracked, self-preference bias detected
- **Phase 3** ✅: Smart routing — learns when deliberation helps vs. single model suffices, dynamic model selection, routing accuracy tracking
- **Phase 4** ✅: Marketplace polish — templates, `--deep` MoA layering, cost estimator
- **Phase 5** ✅: Autoresearch — plugin's own prompts self-improve from usage data via `/council-optimize`
- **Phase 6** ✅ (current): Vault integration — reads organizational context before deliberation, writes decision records to Obsidian vault, syncs model performance and routing intelligence to vault for cross-session learning

## License

MIT — MoxyWolf LLC
