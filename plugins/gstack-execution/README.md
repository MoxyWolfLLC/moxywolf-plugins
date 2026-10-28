# gstack Execution Plugin

**Author:** MoxyWolf LLC
**Based on:** [gstack](https://github.com/garrytan/gstack) by Garry Tan (MIT License), with adversarial-review framing from OpenAI's [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (Apache-2.0)
**Version:** see `.claude-plugin/plugin.json` — deliberately not restated here, because a version in prose has nothing keeping it true. This README sat at 0.5.0 through sixteen minor releases.
**Requires:** Git. Optional but load-bearing: a reviewer CLI of a different model family than the builder (`codex`, `gemini`), Claude in Chrome for the browser commands, and Node with the scorer's dependency installed (`npm ci` in this directory) and a gateway key (see XE-014 below) for the packet coverage scorer.

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
| `/gstack-design-doc` | Create or refresh `DESIGN.md` as an editable artifact; approval writes it to the repo and the project workspace mirror, commits, pushes, pulls back | Artifact + Git |
| `/gstack-build` | The coding loop: design doc gate → build one item → push + verify + pull back → cross-tool review until clean → human release handoff → record merge before done | Git + `codex`/`claude` CLI |
| `/gstack-goal-new` | Draft a goal (GO-007): brief and plan by the agent, goal tests and holdout by the gpt family, the plain-English reading by the gemini family; opens the goal pull request for Dorian's approval | Git + `codex` CLI + OpenRouter |
| `/gstack-goal` | Run an approved goal (GO-003): each plan item through `/gstack-build` onto `goal/<id>`, then one goal pull request into `main` | Git + the other tool's CLI for the reviews |
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
| `check_ledger.py` | Runs a check with no shell and records its real exit code in a per-branch ledger under the review root (XE-034). A failure stays open until the same check, in the same directory with the same arguments, passes; `open-issues` lists what's open. The idea is from WXK-AI/jev-opus at `6b6b0f8` (MIT); no code copied |
| `unknowns.py` | Keeps a reviewer's open questions as revisioned ledger lines under the review root (EV-011): `record`, `update` (refused on a stale revision, nothing written), `close` (only by evidence that exists and carries enough authority: a round finding, a CI run at the head, a passed `check_ledger` run, or an observation a person entered on a release handoff), `list`; each write is one locked read-check-append. `peer_review.py round` writes one for each entry the reviewer declares in its `unknowns` list (falling back to `could not determine` / `could not verify` / `not verified` in unmet-row evidence only when it declared nothing), one line per question per review, closes a `repository` line when a later round meets its criterion, and `release` lists what's open; `close-all` closes a review's lines against one recorded observation, reachable as `peer_review.py unknowns close-all` too (EV-012); the observation may sit on any review of the same branch (EV-013). A question is never settled in the round that raised it. From morluto/rea at `7a6defa` (MIT); no code copied |
| `packet_coverage.mjs` | Scores each acceptance criterion declared for an item against the review packet, so a packet narrower than the item it claims is caught before the review opens. Typed boolean scoring through TypeSafe AI's Jev on the Vercel AI Gateway |
| `model_select.mjs` | Asks the decider council (`council/scripts/decider_council.py`: Jev, Perplexity Decider and OpenAI's decision model on the gateway's `/v1/decisions` wire, DC-001) five typed questions about an item and a rule table with asymmetric confidence bars maps the answers to a builder tier (`floor`, `standard`, `light`), written into the packet as `model_selection`; `record-release` appends the outcome beside it in a per-repository ledger, `score` prints agreement, and `route` mode is refused with `insufficient_history` until 20 scored lines at 0.90 (MR-001) |
| `release-lanes.json` (references) | The lane table GA-010 reads at `open`: `closed` paths and effects (migrations, payment, credentials, the agent's identity, workflows, deletions), `wide` ones (shared code, renames, many callers), everything else `contained`. A repository's `.gstack/release-lanes.json` replaces it whole. The closed lane never opens on its own |
| `agent_token.py` | Acts on GitHub as the `moxywolf-agent` app (GA-005): mints a one-hour token per command and passes it through the environment, never argv, output or a file. No fallback to a person's token. `permissions [--repo owner/name]` prints what that installation actually grants, which is the only thing that separates a permission the app never declared from one it declared and the installation has not accepted (GA-007) |
| `review_host.sh` | Stands up a shell where a dispatched review survives between calls. Use it whenever a review has timed out once |
| `ci_log_receipt.py` | Shortens a failed CI job's log to quotes a cheaper model picked, and keeps the receipt only if every quote is in the log byte for byte (XE-027). `peer_review.py ci-log` and the review surface use it. The idea comes from NVlabs/SoL-Pi's evidence-preserving reducer (MIT); no code is copied |
| `run_all_tests.py` | The repository's own gate. Discovers every `test_*.py` and `--selftest`, names what it examined, and **fails when it discovers none** |
| `tool_rung.py` | Answers "is there a connector for this service?" by looking. Connector → CLI → REST → browser |
| `task_graph.py` | Executable task graphs with frozen inputs, an undeclared-write sweep, a read-side fake-edge report, and a bounded in-run retry for one failed `worker` or `checker` node that opts in with `on_failure: "retry"` (XE-036): at most three dispatches per execution signature, the next attempt carries a correction packet, green siblings never move |
| `endform_workflow.py` | The E2E gate and its preflight: proves the gate *can* run before anything is pushed |
| `repo_gates.py` | Reads and configures branch protection; reports which checks actually gate a merge |
| `governance.py` | Capability grants that name what they permit rather than who may act |
| `measure.py` | Records what each gstack run cost (builder tokens from the session transcript, counted once per message; reviewer tokens as each CLI reports them) as an Obsidian note, and scores XE-012's predictions per vocabulary version. `release` calls it when `GSTACK_MEASURE_DIR` is set |
| `vocab_check.py` | Checks that DESIGN.md's item statuses and the contracts use the vocabulary in `references/vocabulary.json`, the one home for every outcome, status and round shape the dispatcher enforces |

## Agents

| Agent | Model | Tools | What it returns |
|---|---|---|---|
| `explore` | Haiku | Read, Glob, Grep | Where a symbol is defined, who calls it, which files an area touches: `path:line` and a verbatim quote, with a count of what it opened. No shell, no judgement |
| `docs` | Haiku | WebFetch, WebSearch, Read | The passage from a reference, changelog or spec, quoted, with its URL and version. No recommendation |

Reading is the cheap half of a build and the expensive half of a context window. Both agents run on Haiku with no shell because an agent that can loop on `grep \| head` burns tokens examining everything and reporting nothing. `/gstack-build` sends its mapping to them before it edits. The department agents in other plugins stay on the session's model: they produce judgements, which is the part that needs it.

## Which model builds an item (MR-001)

`model_select.mjs recommend <packet> DESIGN.md` asks the decider council (`plugins/council/scripts/decider_council.py`, DC-001) five typed questions about the item, verbatim as the script lists them. Three voices answer on one wire, `typesafe-ai/jev`, `perplexity/pplx-decider-v1.2` and `openai/gpt-6-luna-decisions`, and every voice's answers, the tier the table would give each, cost and latency are recorded in `model_selection.quorum`, with the council's ledger line id. The rule table reads Jev's answers in `shadow` and `route`, and the majority's in `quorum`:

| Question | True when |
|---|---|
| `trust_boundary` | the item changes code on a trust boundary: authentication, authorization, payment, credentials or secrets, the agent's GitHub token or app, a repository ruleset, a CI workflow, or anything that decides what an agent may do |
| `cross_file` | building it needs reasoning across more than one source file at once |
| `docs_only` | it is documentation, configuration, a status line or a version move only |
| `has_tests` | its criteria name executable tests the build must add or make pass |
| `risky` | it changes code that touches production data, money, credentials or secrets, or an irreversible action: a migration, a deletion of tracked files, a send, a payment, a merge to a protected branch (MR-002) |

A rule table in the script, not the model, maps the answers to a tier, first row that holds. Each answer is read against its own bar, and the bars are asymmetric (MR-002): spending more needs 0.30, spending less needs 0.60, because a wrong cheap pick costs a failed build and a wrong dear pick costs a few cents.

| Rule | Condition | Tier |
|---|---|---|
| `risky` | risky at or above 0.70 (`RISKY_BAR`) | `floor` (Opus 5 or higher) |
| `trust_boundary` | trust_boundary at or above 0.30 (`UPGRADE_BAR`) | `floor` |
| `cross_file` | cross_file at or above 0.30 (`UPGRADE_BAR`) | `floor` |
| `docs_only` | docs_only at or above 0.60 (`DOWNGRADE_BAR`) and has_tests below 0.50 | `light` (Sonnet) |
| `default` | anything else | `standard` (Sonnet with an Opus advisor) |

The bars are printed with the recommendation and recorded as `model_selection.thresholds`.

Three modes. `shadow`, the default: the build runs on the floor and the recommendation is only recorded; `open` refuses an item packet without a checked one. `route`, with `GSTACK_MODEL_ROUTING=route`: the tier is the one the build is told to run on, refused with `insufficient_history` until the ledger holds 20 scored shadow lines at agreement 0.90. `quorum`, with `GSTACK_MODEL_ROUTING=quorum` (DC-001.7): the table reads the majority of the three voices instead of Jev, refused with `insufficient_history` until `decider_council.py gate --caller model_select` passes (20 council lines with outcomes and at least two voices each, the majority at least as right as Jev alone); with one voice left the record is `rule: quorum_tie` and the tier is the dearest any voice gave, because a tie is not a decision. Jev unavailable is `unusable`, as before, with the other voices still on the record. `record-release` writes the release outcome onto the council line too, so `decider_council.py score --caller model_select` reads every voice against it. `record-release` appends each released item's outcome beside its recommendation in `$GSTACK_PEER_REVIEW_DIR/model-selection/<owner>-<repo>.jsonl`; `model_select.mjs score --repo <path>` prints per-tier counts, a per-rule row (how many items each rule fired for and how many cleared), overridden and routed lines apart, how many open or abandoned reviews it skipped, and `agreement` (the share of `standard` and `light` recommendations whose item cleared in at most two rounds with no blocking finding). A person's `model_selection.override: {tier, reason}` wins in both modes. Nothing here changes which model reviews.

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
- **An unchecked review doesn't release** (XE-014). The record has four states besides `checked`:
  `not_run` (no report), `unavailable` (no key on any path), `unusable` (a key that didn't work) and
  `broken` (the scorer couldn't start). `release` refuses all four unless the Release Owner's words go
  in `--coverage-exception`, and the handoff and `SURFACE.md` both lead with the status. The key is
  read from `AI_GATEWAY_API_KEY`, then the file `GSTACK_AIGATEWAY_ENV` names, then the vault's
  `aigateway.env` on a Mac. Install the scorer with `npm ci` in this directory.
- **Scoring stays out of the dispatcher.** `coverage_verdict` reads a report and never produces one,
  so the gate can be audited, replayed and tested without a network call.

The scorer found two criteria that had been declared and never built, in items that had already passed
review. It also, once, reported zero problems over 16 of 19 criteria because a regex anchor borrowed
from Python silently dropped the last criterion of every item — which is check #1 of the verification
discipline applied to the gate itself: a pass over input it never read is a failure, whoever produced it.

The open refuses one more shape of packet (XE-025). A criterion about a place the reviewer can't see, such as the Release Owner's Mac, the vault or a local run, has to name a repository file at the reviewed head that carries its evidence, usually `docs/evidence/<item>.md`. Otherwise the open fails as `unevidenced_off_repo_criterion`. `tests.results` doesn't count, because it's the builder's own account. `--accept-off-repo-criterion` proceeds anyway and the record says so.

And one more (XE-034). If a check run through `check_ledger.py` failed on the branch and the same check hasn't passed since, the open fails as `open_check_failure` and names each one. `--accept-open-failure "<reason>"` proceeds and records the reason word for word. `state.json` and the first line of `SURFACE.md` carry `ledger_status`: `clear`, `overridden`, or `none` for a branch that never used the ledger, which opens but shows it. The rule that only the same check can clear a failure comes from WXK-AI/jev-opus at `6b6b0f8` (MIT); no code was copied.

Two more things the surface carries (EV-010, EV-011). `PROVENANCE.json` names, for every file the reviewer is handed, where its bytes came from (`repository`, `ci_log`, `handler_output`, `fetched`, or `executor` for the dispatcher's own notes) and whether it is untrusted content; the builder writes it from each file's origin and the surface is `unusable` if any entry is missing. The reviewer reports a directive found inside untrusted content as a finding with `category: embedded_instruction` and does not follow it; the dispatcher refuses to let such a finding block. And the second line of `SURFACE.md` shows how many unknowns are open on the branch and how many embedded instructions the prior round reported; the open questions' own text is in `UNKNOWNS.md`, labelled untrusted, because a reviewer wrote it. Both ideas are from morluto/rea at `7a6defa` (MIT); no code was copied.

And one about what the reviewer is shown (XE-035). A file an acceptance criterion names by exact path always reaches the reviewer. On disk it sits outside the 25-file cap and takes no caller slot. An API reviewer, which is sent the surface as text under a 400,000-character cap, gets the diff, the changed files, the named files and then callers, in that order. If the cap would still drop a named file, changed files over 40,000 characters go as their hunks in `CHANGE.diff`, largest first, and the round record's `sent` list marks each one `as: diff_hunks`. If that isn't enough, or a named file can't be read, the review opens as `unusable`, names the file and takes no round. The round checks again against the reviewer that actually runs, so a fallback to an API reviewer is caught there. An API reviewer still isn't sent `dirs/`, `evidence/`, or the `dependencies/` files no criterion names.

## Licence and provenance

MIT, following gstack. Adversarial-review framing adapted from codex-plugin-cc (Apache-2.0). The verification discipline, the peer-review contract, the review surface and the gates are MoxyWolf's.

## Text the loop didn't write (TB-002)

Reviewer output, CI logs, pull request and issue bodies, fetched pages and retrieved memory go into
prompts inside one enclosure, defined once in
`skills/gstack-execution/references/untrusted-enclosure.md` and written by `scripts/enclosure.py`.
`test_untrusted_enclosure.py` fails if the rule gets a second home or an ingesting place stops
loading it.

**What it's worth:** it marks the boundary, it doesn't enforce it. The one number available, from the
external response's revised edition (2026-09-20), is executed adversarial actions falling from 60% to
30% on a synthetic benchmark whose traces and harness weren't published. That's a speed bump on
unverified evidence. TB-001 and TB-003 are the controls.

## Task context and artifact relationships

Optional versioned context now complements the existing executable workflows. Nodes select the artifacts they need, require accepted inputs, and refuse stale inputs or blocking questions before dispatch. Reports retain portable handoff digests and artifact relationships support transitive impact queries. An artifact that declares `attest` is checked against its source file at its revision before dispatch; one that does not remains a declaration. Unscoped nodes receive an empty-selection handoff, not `None`. See [Versioned decision context](skills/gstack-execution/references/task-graph-contract.md#versioned-decision-context) for the schema and `scripts/graph_context.py` commands. These records carry evidence, not approval authority; context changes conservatively invalidate packet-dependent work.

## Version history

- **0.96.0**: SM-010. `references/verification-checks.md` opens with the standing operating rule, verify before recommending commitment; the six checks follow under `## Checks`, unchanged. The verification-discipline hook injects the file verbatim, so the rule reaches every session it already reached.
