# Council — Multi-Model AI Deliberation

Four AI models debate so you get a better answer, the system gets smarter every time you use it, and now it remembers what it learned.

Council gives any Cowork user access to structured multi-model deliberation. Instead of relying on a single model's response, Council collects independent answers from multiple LLMs, has them peer-review each other anonymously, and synthesizes the best insights into one authoritative answer.

The smart router learns which questions actually benefit from full deliberation. The autoresearch loop systematically improves deliberation prompts from your actual usage data. And starting in v0.6.0, the Obsidian vault integration means Council reads organizational context before deliberating and writes decision records back to the vault afterward. Verification becomes institutional knowledge.

No backend required. Council dispatches directly to OpenRouter via its public API from within Cowork's bash sandbox.

## Setup

1. Install the plugin in Cowork.
2. Make sure the team-shared OpenRouter key file exists in the MoxyWolf Vault at
   `_Shared Knowledge/Agents and Plugins/openrouter.env` with a single line:
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
   Ask Dorian if the placeholder is still in the file. The vault must be mounted
   in your Cowork session. Council's `scripts/openrouter_key.py` auto-discovers
   the file in either the Cowork bash sandbox mount or a native macOS Google
   Drive mount — no shell-rc edits required.
3. Run `/deliberate` with any question.

**Lookup order** when the dispatch script resolves the key:

1. `OPENROUTER_API_KEY` env var, if you've exported it for the session.
2. File at `$OPENROUTER_KEY_FILE`, if set.
3. `$MOXYWOLF_VAULT/_Shared Knowledge/Agents and Plugins/openrouter.env`.
4. Cowork bash sandbox vault mount (`/sessions/*/mnt/MoxyWolf Vault/...`).
5. macOS Google Drive vault mount (`~/Library/CloudStorage/GoogleDrive-*/Shared drives/MoxyWolf Shared Files/MoxyWolf Vault/...`).

If none of those yield a key, Council halts with a message listing every path it
tried.

**Quick sanity check** from any bash call:

```bash
python3 "${COUNCIL_PLUGIN}/scripts/openrouter_key.py" --where
```

prints the source label and path the loader resolved.

## Commands

| Command | Description |
|---------|-------------|
| `/deliberate <question>` | Run a multi-model deliberation (always uses full council) |
| `/council-config` | View or modify model lineup, router mode, and settings |
| `/council-stats` | View performance metrics, routing accuracy, and deliberation history |
| `/council-optimize` | Disabled by DR-140 until the case store (CC-002) and a new optimizer exist |
| `/decide <question>` | Ask the decider council one typed question (predicate, `--choices`, or `--levels`) and see each voice, the majority and the ledger receipt |

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

### /council-optimize

Disabled by DR-140. Every run, with any flag, prints the reason and stops.

## Skills

| Skill | Phase | Description |
|-------|-------|-------------|
| deliberation-engine | 6 (Active) | Core 3-stage pipeline with vault context injection, smart-router gate, MoA deep mode, templates, autoresearch, and post-deliberation vault writes |
| pattern-memory | 6 (Active) | Persistent learning with vault sync — logs outcomes, tracks value-added, detects self-preference bias, stores optimization experiments, syncs to Obsidian vault every 5th deliberation |
| smart-router | 5 (Active) | Learned routing — heuristic fallback → data-driven rules after 20+ deliberations |

## The decider council (DC-001)

The deliberation council above puts language models in a room over an open question. The decider council is its sibling for typed questions: yes or no (`predicate`, answered as a probability), pick one (`choice`), or rate against ordered levels (`score`). Three decision models from three vendors answer, so no vendor grades its own work: `typesafe-ai/jev`, `perplexity/pplx-decider-v1.2` and `openai/gpt-6-luna-decisions`, the `DECIDERS` constant in `scripts/decider_council.py` (`GSTACK_DECIDERS` overrides it). One request body is serialized once and sent to each slug on the AI Gateway's OpenAI-compatible `POST /v1/decisions` with only the leading `model` member different, concurrently, each voice bounded by one `DECIDER_TIMEOUT_MS` (8000) deadline covering the connection and the body read. The live probe of 2026-10-18 (`docs/evidence/decision-quorum-probe-2026-10-18.md`) saw all three answer in the documented shape at about $0.00002, $0.000008 and $0.00009 per call.

**Majority wins** (Dorian, 2026-10-18). For a choice, the value more than half the available voices picked; for a predicate or a score, the median. No majority (a three-way split, or fewer than two voices) is returned as `tie`, never as a pick. Availability is a property of answers, not of HTTP: a voice that times out, errors, refuses, or answers out of shape (a malformed envelope included) is `unavailable` for that question and is not counted. `quorum` is `full` when every question has at least two available voices, `degraded` when every question has one, `unavailable` when any question has none. Appends and outcome writes share one file lock, so concurrent callers lose nothing.

**Code decides what an answer means.** The script returns probabilities and the majority and carries no bar, tier or policy. The caller's rule table turns answers into an action, and registers the function that scores an outcome in `OUTCOME_RULES` (today: `model_select`, gstack-execution's builder-tier selector, the first caller).

**Every call is on one ledger**, `$GSTACK_PEER_REVIEW_DIR/decisions/<YYYYMM>.jsonl` (else `~/.gstack/decisions/`): caller, ref, each voice's answer verbatim, the majority, cost, latency, and an `outcome` the caller fills later with `decider_council.py outcome --line <id> --result '<json>'`. `decider_council.py score [--caller <name>]` prints, per caller, calls, lines with an outcome, questions agreed and ties; per voice, calls, answers, unavailable answers, agreement with the majority (n of d), ties (n of answers), mean cost, median latency, and over lines with an outcome how often the voice was right by the caller's rule; and the majority's own right-of-scored. Zeros print as zeros. `decider_council.py gate --caller <name>` exits 0 only when the caller has 20 lines with outcomes in which every question had at least two available voices, and the majority, scored over something, is at least as right as Jev alone; until then callers act on Jev's answer, as they did before. A decider that has not been scored watches before it steers.

```bash
# from any plugin, by path
python3 plugins/council/scripts/decider_council.py ask --caller my_plugin --ref item-7 --input facts.txt \
  --questions '[{"type":"choice","name":"lane","instructions":"Which lane?","choices":[{"value":"closed"},{"value":"narrow"},{"value":"wide"}]}]'
```

The output is JSON: `id` and `ledger` (the receipt), `voices` (model, status, latency, cost, `unavailable`), `answers` (per question: `majority`, `agreed`, `tie`, `available`, `by_voice`), and `quorum` (`full`, `degraded`, `unavailable`). Tests: `scripts/test_decider_council.py`, against a stub `/v1/decisions` that answers per slug.

## How It Works

**Routing:** Before anything runs, the smart router evaluates your query. Simple factual questions go to a single model (~$0.01). Complex decisions, comparisons, and strategy questions go to the full council (~$0.08-0.12). The router starts conservative (deliberate on everything) and learns from outcomes.

**Stage 1 — Collect:** Four models answer your question independently, each with a different perspective (Analyst, Strategist, Challenger, Synthesist).

**Stage 2 — Peer Review:** Each model reviews the other three responses anonymously. The review protocol adapts by query type: voting for reasoning questions, consensus for knowledge questions.

**Stage 3 — Synthesize:** The highest-ranked model becomes chairman and synthesizes all insights into one unified answer, flagging where models agreed (high confidence) and disagreed (needs your judgment).

**Learning:** Every outcome is logged — model rankings, deliberation value-added, routing decisions, and your feedback. After 20+ deliberations, the router builds data-driven rules that get smarter over time.

**Templates:** Pre-built context wrappers for common scenarios — code review, architecture decisions, writing critique, research synthesis, compliance checks, and business strategy. Each template frames the question and suggests optimal flags.

**Self-Improvement:** disabled by DR-140. The legacy `/council-optimize` loop worked from rating fields alone, which aren't replayable cases. A new optimizer will use the CC-002 case store.

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
| Strategist | `anthropic/claude-sonnet-5` | Anthropic |
| Challenger | `google/gemini-2.5-flash` | Google |
| Synthesist | `x-ai/grok-4.3` | xAI |

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

## Replay cases (CC-002, DR-140)

A rated deliberation can be saved as a redacted replay case, only by opt-in, for a future optimizer to replay. `scripts/council_cases.py` (stdlib) does all of it:

- **Publish gate.** `stage` redacts (secrets via `session_record.py`'s patterns, emails, phone and account numbers, listed names) into owner-only staging. `scan` runs gitleaks on `case.md`. `confirm` is run by the person who staged the case, on that device, with the store's audience word for word, the `12m-rule` retention and their own words. `publish` checks all of that, scans the final manifest a second time, writes an `add` request, and then copies the case into `council-cases/<project>/<case-id>/`. A missing gitleaks binary refuses; it never passes.
- **Audience.** Until `init --audience … --approved-by … --words …` records Dorian's approval, no save question is asked and `publish` refuses with `audience not approved`. OpenControls projects (cki, living-lexicon, mwe-ner and any project whose `project-surfaces.json` names OpenControls) are excluded. Access is shared-drive membership; organizers can open even a limited-access folder.
- **One writer.** Drive has no atomic append, so only the device named in `store.json` runs `apply`. It applies inbox requests in order, and writes the ledger and index to temp files renamed into place. Every other device only drops requests.
- **Retention.** Proposal cases expire 12 months after publication. Held-out cases have no date until retired, then 12 months. `exclude` takes effect for readers as soon as it's requested. People delete folders; `delete-record` and `cleared` record each remaining copy. The store never deletes.
- **Readers** go through `lookup <case-id>`, which overlays pending excludes on the index. `init` needs a readable projects root, so every OpenControls project is found, and `--backup` names each backup that must be `cleared` after a deletion. `apply` holds a lock on the writer device.
- **verify** detects accidental and incomplete changes (hashes, the ledger chain, the writer id, Drive conflict copies). It is not tamper evidence.
- **Readiness.** `status --project <slug>` exits 0 at 15 eligible proposal and 5 eligible held-out cases, else 3. The thresholds are an operational starting point.

The store is found on the workspace or Google Drive mount, or given with `--store`. There is no Drive API writer.

## Version History

- **0.15.0**: DC-003. `decider_council.py ask --budget <file> --run <id>` checks a run's budget before each call and spends only through a dedicated, capped AI Gateway key bound to the run; `budget init|show|recover` manage the file. Bounded, not guaranteed: Vercel's budget is a soft cap. Tests: `scripts/test_dc003_*.py`.

- **0.14.0**: CC-002. Opt-in, redacted Council replay cases in the vault by project: `council_cases.py` with the publish gate, approved audience, single writer, retention, `verify` and readiness `status`. `/deliberate` asks for a rating and then, only when allowed, whether to save a case. `/council-stats cases` reports readiness. Test: `scripts/test_council_cases.py`.

- **0.13.1**: CC-001. `/council-optimize` is disabled by DR-140: it stops before any step with every flag, including `--dry-run`, and prints why. `/council-stats optimization` shows `optimizer: disabled (DR-140)`. The legacy loop's references carry a disabled line. It stays off until the case store (CC-002) and a new optimizer item exist.

- **0.13.0**: ME-004. `openrouter_dispatch.py` sends top-level `cache_control` on `anthropic/` jobs (a job's `"cache": false` opts out) and records `cache: {read, write}` from OpenRouter's `usage.prompt_tokens_details` in each result and in `_summary.json`, `null` with a reason when the fields are absent, plus `cache.requested`, so a job that never asked for caching is reported as caching not requested and not as a miss. Kept to measure whether caching pays on one-shot council calls; whether to turn it off is Dorian's call. Test: `scripts/test_openrouter_dispatch.py`.

## License

MIT — MoxyWolf LLC

The Jev router's choice margin and the calibration figures it cites come from [wuyoscar/jev-skill](https://github.com/wuyoscar/jev-skill) (MIT). The idea and the measurement are credited here; no code was copied.

The router's check that a Jev answer is well formed (an offered label, probabilities in [0, 1] that sum to 1) comes from [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) (MIT), re-expressed; no code was copied. The prompt optimizer keeps full experiment traces and reads them before proposing a change, following Meta-Harness (Lee, Nair, Zhang, Lee, Khattab and Finn, [arXiv 2603.28052](https://arxiv.org/abs/2603.28052), 2026, CC BY 4.0). The idea is re-expressed from the paper; no code was copied.

## Composio fallback

For apps with no native MCP connector, this plugin can reach them through Composio's Tool Router when the Composio connector is installed. See the `composio` plugin.
