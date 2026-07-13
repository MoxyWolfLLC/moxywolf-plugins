# Agent Team Design Patterns

When a skill's work is too big or too varied for one agent, it gets decomposed across several. This reference is the design vocabulary for that decomposition: six named patterns, how to combine them, and how to pick the execution substrate.

Concept-ported from [revfactory/harness](https://github.com/revfactory/harness) (Apache-2.0) — the six-pattern taxonomy and the mode-selection discipline, re-specified for Cowork/Claude Code's actual primitives. No code vendored; the patterns are re-expressed here. harness targets Claude Code's *experimental* agent-teams feature (`TeamCreate`/`SendMessage`, behind `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`); this reference maps the same patterns onto the primitives that ship today.

## First decision: does this need more than one agent at all?

Most skills don't. A single agent following a good SKILL.md is the default. Reach for a multi-agent design only when one of these is true:

- The work splits into **genuinely parallel** independent pieces (wall-clock matters).
- It needs **independent perspectives** that shouldn't contaminate each other (a reviewer that didn't write the thing; three finders that are blind to each other).
- It's **larger than one context window** can hold (a migration across hundreds of files, an audit of a whole repo).

If none of these holds, write a single-agent skill. Multi-agent adds token cost, coordination overhead, and failure surface — earn it.

## Execution substrates in Cowork / Claude Code

Three ways to run more than one agent. Pick by how much coordination the pattern needs:

| Substrate | Primitive | What it gives you | Cost |
|---|---|---|---|
| **Sub-agents** | the `Agent` tool | Spawn N agents; each returns its result to the caller. No inter-agent comms. | Low, token-efficient |
| **Deterministic orchestration** | the `Workflow` tool | Scripted `pipeline()` / `parallel()` fan-out with control flow (loops, conditionals, budgets). Agents don't talk; the script coordinates. | Medium; best for fixed-shape fan-out |
| **Persistent spawned agents** | `Agent` + `SendMessage` | Continue a spawned agent with its context intact; pass messages between turns. Closest to true "teams." | Higher; use when agents must iterate together |

harness's "agent teams" (real inter-agent `SendMessage`, self-coordinating shared task list) map onto the third row where available, and onto the `Workflow` tool when the coordination can be scripted deterministically. When a pattern below says "needs live collaboration," that's the third row or a `Workflow`; when it says "just collect results," the first row (plain sub-agents) is enough and cheaper.

## The six patterns

### 1. Pipeline
Sequential stages; each agent's output is the next one's input.

```
[analyze] → [design] → [build] → [verify]
```

- **Use when:** each stage strongly depends on the prior stage's artifact.
- **Example:** writing a paper — outline → draft → edit → fact-check.
- **Caution:** a slow stage stalls the whole line. Keep stages as independent as you can, and parallelize *within* a stage where possible.
- **Substrate:** `Workflow`'s `pipeline()` is the natural fit — items flow stage to stage with no barrier. Plain sub-agents work if you drive the sequence yourself.

### 2. Fan-out / Fan-in
Split one input across parallel workers, then merge.

```
          ┌→ [expert A] ─┐
[split] → ├→ [expert B] ─┼→ [merge]
          └→ [expert C] ─┘
```

- **Use when:** the same input needs several independent angles or domains analyzed at once.
- **Example:** a comprehensive research sweep — official / media / community / academic sources probed in parallel, then synthesized.
- **Caution:** the merge step's quality caps the whole result. Invest in the synthesis prompt.
- **Substrate:** `Workflow`'s `parallel()` (barrier) or `pipeline()` with a merge stage. If the workers benefit from seeing each other's findings mid-flight, use persistent spawned agents instead — cross-pollination raises quality over blind parallel.

### 3. Expert Pool
A router picks the right specialist per input instead of running all of them.

```
[router] → { expert A | expert B | expert C }
```

- **Use when:** different input types need different handling and running every expert is wasteful.
- **Example:** code review that routes to the security, performance, or architecture specialist depending on the diff.
- **Caution:** the router's classification accuracy is the whole game. Make routing criteria explicit.
- **Substrate:** plain sub-agents — you only invoke the chosen expert, so no standing team is needed.

### 4. Producer–Reviewer
A generator and a checker work as a pair, looping until the output passes.

```
[produce] → [review] → (issues?) → [produce] again
```

- **Use when:** output quality matters and there's an objective-ish bar to check against.
- **Example:** generate a component → adversarial review → regenerate the parts that failed. (This is the shape gstack-execution's ship + codex-review already use.)
- **Caution:** cap retries (2–3) to avoid an infinite produce/review loop.
- **Substrate:** persistent spawned agents when producer and reviewer should exchange live feedback; `Workflow` when the loop can be scripted with a fixed retry cap.

### 5. Supervisor
A central agent holds the work state and hands pieces out dynamically as workers free up.

```
          ┌→ [worker A]
[supervisor] ┼→ [worker B]   ← assigns from a live queue
          └→ [worker C]
```

- **Use when:** the workload is variable or only knowable at runtime.
- **Example:** a large code migration — the supervisor scans the file list and doles out batches.
- **Difference from fan-out:** fan-out fixes the split up front; the supervisor adjusts as it watches progress.
- **Caution:** the supervisor can become the bottleneck — hand out chunks large enough that coordination doesn't dominate.
- **Substrate:** `Workflow` with a work queue and a loop, or persistent spawned agents self-serving from a shared task list.

### 6. Hierarchical Delegation
A lead delegates to sub-leads who delegate to workers — recursive decomposition.

```
[lead] → [sub-lead A] → [worker A1]
                      → [worker A2]
       → [sub-lead B] → [worker B1]
```

- **Use when:** the problem decomposes naturally into a tree (e.g. full-stack build: lead → frontend lead (UI/logic/test) + backend lead (API/DB/test)).
- **Caution:** depth ≥ 3 loses context and adds latency. Stay within two levels; flatten if you can.
- **Substrate:** watch the substrate limits — sub-agents generally can't spawn their own sub-agents, so implement level 1 as the orchestrator and level 2 as its sub-agents, or flatten to a single fan-out. A `Workflow` can express the tree explicitly.

## Composite patterns

Real designs usually combine patterns:

| Composite | Shape | Example |
|---|---|---|
| **Fan-out + Producer–Reviewer** | parallel generate, then review each | translate to 4 languages in parallel → native reviewer per language |
| **Pipeline + Fan-out** | a sequential stage that parallelizes internally | analyze (seq) → implement (parallel) → integration test (seq) |
| **Supervisor + Expert Pool** | supervisor dynamically calls specialists | support triage — classify the ticket, assign the right expert |

## Run discipline: observability and failure propagation

Choosing a pattern is half the design; the other half is being able to tell, afterwards, what the team actually did and what it cost. These disciplines are concept-ported from ByteDance's [deer-flow](https://github.com/bytedance/deer-flow) (MIT) — a production agent harness that learned them at scale. No code copied; the ideas are re-expressed for Cowork's primitives.

- **Attribute cost to the dispatching stage, not the run.** When a skill fans out, record each sub-agent's token spend against the stage that dispatched it (the `Workflow` tool's `budget.spent()` gives the pool; the stage labels give the attribution). "The run cost 400k" teaches nothing; "the verify stage cost 3× the find stage" tells the next revision where to cut. Skills that spawn agents should say in their design which stages are expected to be expensive.
- **Define termination conditions when the sub-agent is spawned, not discovered later.** Every spawned agent gets, in its prompt: what done looks like, what to return, and when to stop trying. An agent without a termination condition ends when its context runs out, which is a budget decision made by accident.
- **A failed sub-agent must report failure, never a plausible result.** Model/provider errors, empty tool results, and blown assumptions surface to the orchestrator as *failed tasks* — the orchestrator retries, reroutes, or reports honestly. The failure mode to design against is a sub-agent degrading into confident emptiness that the merge stage then launders into the final answer. In `Workflow` scripts this is the `.filter(Boolean)` discipline plus checking counts: if 2 of 5 finders returned null, the synthesis must say so.
- **Long-running sub-agents that compact must re-anchor.** When an agent summarizes its own older context to keep going, the summary is injected as durable grounding it continues *from* — not silently dropped. If the substrate doesn't do this (plain sub-agents don't), prefer shorter-lived agents that return and are re-spawned with a digest, over one long agent quietly forgetting its first half.

## Agents vs skills (so the port lands in the right place)

| | Skill | Agent |
|---|---|---|
| Is | procedural knowledge + tool bundle | a persona + operating principles |
| Answers | "how is it done" | "who does it" |
| Lives | `skills/` | `agents/` (or a sub-agent type) |

A skill is the procedure an agent follows; an agent is the role that invokes skills. When skill-creator produces a skill whose work spans multiple roles, name the pattern from this file, then decide the substrate — and, per skill-creator's own discipline, only add the extra agents that earn their keep.

## How to use this in skill-creator

During **Capture Intent / Interview**, ask whether the skill's work is single-agent or needs decomposition. If decomposition is warranted (parallelism, independent perspectives, or scale beyond one context), pick a pattern above, record it in the skill's design, and choose the lightest substrate that supports it. Prefer plain sub-agents unless the pattern genuinely needs live collaboration or scripted control flow. Document the chosen pattern in the SKILL.md so future maintainers know why the skill is shaped the way it is.
