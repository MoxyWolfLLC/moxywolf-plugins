# gstack Execution Plugin

**Author:** MoxyWolf LLC
**Based on:** [gstack](https://github.com/garrytan/gstack) by Garry Tan (MIT License), with adversarial-review framing from OpenAI's [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (Apache-2.0)
**Version:** see `.claude-plugin/plugin.json` — deliberately not restated here, because a version in prose has nothing keeping it true. This README sat at 0.5.0 through sixteen minor releases.
**Requires:** Git. Optional but load-bearing: a reviewer CLI of a different model family than the builder (`codex`, `gemini`), Claude in Chrome for the browser commands, and Node with `ai@7.0.105+` plus an `AI_GATEWAY_API_KEY` for the packet coverage scorer.

## What this is

The factory floor. Product Orchestrator decides what to build; this plugin builds, reviews, and ships it — and, more than anything else it does, it refuses to let a change claim more than it has earned.

Adapted from Garry Tan's gstack. The adaptation that matters is not the command list: it is that every gate here reports what it examined, and a gate that examined nothing fails instead of passing.

## The rule the rest of it serves

> A check reports its coverage. A pass over zero input is a failure. Skipped is not passed.

Three of this plugin's own checks once shipped as false passes of exactly that kind — green lines over input they had never looked at. The whole verification discipline in `skills/gstack-execution/references/verification-checks.md` exists because of that, and it is injected at session start rather than left as documentation.

## The loop

`/gstack-design-doc` → `/gstack-build` → cross-tool peer review at a checkpoint → human merge.

An item is declared in `DESIGN.md` before it is built. Several items form one checkpoint, reviewed together. The review is dispatched, not blocked on. A non-pass outcome stops the loop; it never becomes a merge.

## Commands

| Command | Description | Tools Used |
|---------|-------------|-----------|
| `/gstack-design-doc` | Create or refresh `DESIGN.md` as an editable artifact; approval writes it to the repo and Taskade, commits, pushes, pulls back | Artifact + Git |
| `/gstack-build` | The coding loop: design doc gate → build one item → push + verify + pull back → cross-tool review until clean → human release handoff → record merge before done | Git + `codex`/`claude` CLI |
| `/gstack-review` | Structural code review with two-pass checklist | Git + Grep |
| `/gstack-plan-review` | Pre-code plan-hardening loop over PLAN.md (real Codex or fresh-context Claude critic) | Git + Grep + `codex` CLI (optional) |
| `/gstack-peer-review` | Bounded cross-tool review loop at an implementation checkpoint (Codex ↔ Claude Code), fixed contract, explicit outcomes | Git + the other tool's CLI (`codex` or `claude`) |
| `/gstack-codex-review` | Compatibility alias for `/gstack-peer-review --builder claude` | Same |
| `/gstack-verify` | Post-build check of the implementation against its plan/spec (claim table + drift report) | Git + Grep + Read |
| `/gstack-investigate` | Root cause debugging with hypothesis testing | Git + Grep + Read |
| `/gstack-cso` | Security audit: OWASP + STRIDE + supply chain + secrets | Grep + Bash |
| `/gstack-ship` | Test → review → PR pipeline, worktree-isolated with a safe-fix/escalate contract; the Ship Report carries required Verified / Unverified lines | Git + Bash |
| `/gstack-design` | Design system audit and component generation | Read + Write |
| `/gstack-qa` | Browser QA testing with bug fixing | Claude in Chrome |
| `/gstack-browse` | Quick page verification and health check | Claude in Chrome |

## Scripts

| Script | What it does |
|--------|--------------|
| `peer_review.py` | The review dispatcher: reviewer routing by model family, surface construction, content-bound findings, dispatch/collect, explicit outcomes |
| `packet_coverage.mjs` | Scores each acceptance criterion declared for an item against the review packet, so a packet narrower than the item it claims is caught before the review opens. Typed boolean scoring through TypeSafe AI's Jev on the Vercel AI Gateway |
| `agent_token.py` | Acts on GitHub as the `moxywolf-agent` app (GA-005): mints a one-hour token per command and passes it through the environment, never argv, output or a file. No fallback to a person's token |
| `review_host.sh` | Stands up a shell where a dispatched review survives between calls. Use it whenever a review has timed out once |
| `run_all_tests.py` | The repository's own gate. Discovers every `test_*.py` and `--selftest`, names what it examined, and **fails when it discovers none** |
| `tool_rung.py` | Answers "is there a connector for this service?" by looking. Connector → CLI → REST → browser |
| `task_graph.py` | Executable task graphs with frozen inputs, an undeclared-write sweep, and a read-side fake-edge report |
| `endform_workflow.py` | The E2E gate and its preflight: proves the gate *can* run before anything is pushed |
| `repo_gates.py` | Reads and configures branch protection; reports which checks actually gate a merge |
| `governance.py` | Capability grants that name what they permit rather than who may act |
| `measure.py` | Records what each gstack run cost (builder tokens from the session transcript, counted once per message; reviewer tokens as each CLI reports them) as an Obsidian note, and scores XE-012's predictions per vocabulary version. `release` calls it when `GSTACK_MEASURE_DIR` is set |
| `vocab_check.py` | Checks that DESIGN.md's item statuses and the contracts use the vocabulary in `references/vocabulary.json`, the one home for every outcome, status and round shape the dispatcher enforces |

## What a review is, and is not

Reviewer routing is a table of `{family, model, floor}`. **A reviewer sharing the builder's model family is refused before it runs** — a harness swap is not an independent mind, and a record that cannot tell the two apart is worth less than no record. A fallback to a second reviewer is permitted only across families, and is recorded *as* a fallback, because a fallback nobody recorded is a silent downgrade.

The reviewer receives the diff, the files it changes, and the code that references them — not the repository tree. Handing over the tree made reviews spend their budget reading the repository; bounding the surface took a review that had been timing out down to 67 seconds. The surface names the **callers the change did not touch**, because a change is not finished when the file it edits is consistent, but when the files depending on it still hold.

A round records which files the reviewer opened and how many it was offered. A review reporting no findings is two different events — it looked and found nothing, or it barely looked — and without the denominator they are indistinguishable. Where the filesystem cannot report reads, the round says so rather than claiming the reviewer examined nothing.

Peer-review records are written to a directory you name. There is no silent default: the old one wrote to a session-local home, so review IDs cited as evidence in this repository's own design document resolved to nothing.

## Two ways to buy a pass, and why neither is allowed

When a review will not fit the time available, the tempting fixes are to pick a faster model or to trim acceptance criteria until one completes. Both buy a pass rather than earning it, and the second is worse: criteria narrower than the declared item let a review approve something unfinished. That happened here — an item passed 13/13 with one of its criteria never built.

Move the shell instead. That is what `review_host.sh` is for.

The second one is now gated rather than trusted. Before a review opens, `packet_coverage.mjs` reads
the criteria the item declared in `DESIGN.md`, reads the packet the review would be handed, and scores
each criterion for whether the packet covers it. A criterion scoring below the floor blocks the open.
`--accept-narrow-packet` proceeds anyway and the record says so, because an override that reads like a
pass is the failure this gate exists to prevent.

Three properties of the gate matter more than the scorer behind it:

- **The score may raise a gate and never lower one.** A model that says "ship it" cannot open a door
  that was closed; it can only close one that was open. A scoring step wired the other way turns every
  miscalibration into a merge.
- **A scorer that did not run is recorded as not run.** No key, no Node, no network: the record reads
  `not_run` or `unavailable`, never `coverage verified`. This was wrong once — an unavailable scorer
  set `coverage_checked` to true — and the fix is the only reason the field means anything.
- **Scoring stays out of the dispatcher.** `coverage_verdict` reads a report and never produces one,
  so the gate can be audited, replayed and tested without a network call.

The scorer found two criteria that had been declared and never built, in items that had already passed
review. It also, once, reported zero problems over 16 of 19 criteria because a regex anchor borrowed
from Python silently dropped the last criterion of every item — which is check #1 of the verification
discipline applied to the gate itself: a pass over input it never read is a failure, whoever produced it.

## Licence and provenance

MIT, following gstack. Adversarial-review framing adapted from codex-plugin-cc (Apache-2.0). The verification discipline, the peer-review contract, the review surface and the gates are MoxyWolf's.
