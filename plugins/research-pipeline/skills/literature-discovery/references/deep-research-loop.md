# Deep Research Loop

The recursive expansion mode behind `/discover-literature --deep`. Ordinary discovery is one flat round: fan out, merge, present. This is the bounded recursive version — each level's *learnings* generate the next level's queries, so the search follows what it found instead of what you guessed at the start.

Concept-ported from the deep-research mode in [gpt-researcher](https://github.com/assafelovic/gpt-researcher) (Assaf Elovic, Apache-2.0). The recursion shape, the breadth/depth/concurrency parameterization, and the propagate-learnings-upward discipline are theirs. The learnings-digest schema, the evidence-typed triage, the dry-level termination, and the declared-budget gate are ours. No code copied.

## Why recursion beats a bigger flat search

A flat search is only as good as the query you opened with. You ask about "STIG automation," you get the literature that uses those words. What you miss is everything the field calls something else — the SCAP tooling papers, the policy-as-code work, the configuration-drift literature — because you didn't know those names when you wrote the query.

Recursion fixes that by letting the corpus name its own adjacent territory. Level 1 finds the obvious sources; reading them tells you what the field actually argues about; those arguments become level 2's queries. The gain isn't more sources, it's *differently-named* sources.

## Parameters

| Parameter | Default | What it controls |
|---|---|---|
| `breadth` (B) | 4 | Sub-queries generated per node at each level |
| `depth` (D) | 2 | How many levels below the root |
| `concurrency` (C) | 4 | Sibling branches investigated at once |

Node count is bounded by `B^D` in the worst case (16 at the defaults). Real runs come in well under that because dry branches terminate early. Never run `D > 3` without an explicit ask — depth 4 at breadth 4 is 256 nodes and the marginal source stops being worth the spend around level 3.

## The loop

**Level 0 — root.** The user's topic. Run the ordinary Step 3 / Step 3b discovery against it (API engine plus multi-model swarm). This is the seed corpus.

**Distill a learnings digest.** Before generating any child queries, read what the level actually returned and write a digest with exactly three buckets:

- **Established** — what the sources agree on. This is what you no longer need to search for.
- **Contested** — where sources disagree, or where one source's premise contradicts another's finding. Every contested item is a candidate child query, because disagreement means there is literature on both sides you haven't read.
- **Unanswered** — questions the corpus raises and does not settle, plus named entities (standards, tools, authors, programs) that appear without explanation. Named-but-unexplained entities are the highest-yield child queries in practice; they are the field's vocabulary leaking through.

The digest is the only thing that crosses between levels. Do not pass raw source lists down — a child branch that inherits its parent's full result set re-finds the parent's sources and reports them as new.

**Generate child queries.** Take `B` items from the digest, weighted contested-first, then unanswered, then established-with-a-gap. Each becomes one child query. Write them as search queries, not as questions: `"policy-as-code" configuration drift compliance` beats `how does policy-as-code handle configuration drift?`.

**Descend.** Run the children concurrently, up to `C` at a time. Each child runs its own discovery round and produces its own digest. A child that returns zero sources surviving dedup is a **dry branch** — record it and do not descend further from it. Dry branches are information: they mark where the literature actually ends.

**Dedup at every level, against the whole library.** Not against the parent, not against siblings — against everything ingested so far plus everything staged this run. Reuse Step 4's dedup (DOI, URL, title similarity >90%). Without this the same foundational paper is "discovered" at every level and the source count inflates while the corpus doesn't.

**Propagate upward.** When a level's children are all resolved, merge their digests into the parent's before the parent concludes. A finding from one branch frequently resolves another branch's contested item — that cross-pollination is the whole point of running siblings against a shared digest rather than as independent searches. Note explicitly in the merged digest which contested items got resolved by a sibling and which are still open; the still-open ones are what the final gap analysis reports.

**Terminate** on any of: depth cap reached, every branch at the current level went dry, or the declared budget is exhausted. Say which one ended the run — "stopped at depth 2 as configured" and "stopped because every branch went dry at depth 1" mean very different things about the literature.

## Declared budget, before the run

State the shape and the estimated spend before spending anything, and get an explicit go:

```
Deep research: "[topic]"
  breadth 4 x depth 2 = up to 16 discovery rounds (usually 8-11 after dry branches)
  estimated: $0.30-0.60 in swarm calls, 4-8 minutes
  API calls are free; the cost is the OpenRouter swarm at ~$0.03-0.07 per round

Proceed? (or adjust breadth/depth)
```

Then record the actuals when it finishes — rounds run, dry branches, sources added, wall time, spend — and write them to the library's metadata so `/research-status` can show what the corpus cost to build. A research library whose build cost is unknown can't be rebuilt or budgeted for.

## Substrate

Sibling branches are independent work over a shared digest, which is Fan-out/Fan-in from `moxywolf-skills:skill-creator`'s `references/agent-team-patterns.md`. Two ways to run it:

- **Plain sub-agents (default).** Spawn one agent per child query with the digest in its prompt and a termination condition; collect the returned candidate lists. Cheap, and it gives each branch context isolation for free — a branch can't be biased by a sibling's raw results because it never sees them.
- **The `Workflow` tool** when the tree is large enough that per-stage cost attribution matters. Use `pipeline()` over the child queries, not `parallel()` — there is no barrier between "child 1 finished searching" and "child 1 can be digested," so a barrier just idles the fast branches.

Per that same reference's run discipline: give every spawned branch its termination condition when you spawn it, attribute spend to the level that dispatched it, and treat a branch that errored as *failed*, not as a dry branch. A dry branch means "no literature here." A failed branch means "we don't know." Reporting the second as the first is how a gap analysis ends up confidently wrong.
