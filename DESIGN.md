# Design: gstack Governed Execution

## Goal

Make gstack’s execution graph conform to Governed Autonomy: enforce authority and evidence completeness before introducing parallel execution. Every consequential action must be traceable to its governing policy, supporting evidence, and accountable human.

## Constraints and settled decisions

- Preserve cross-tool review, pinned commits, bounded review rounds, and recursion refusal.
- Keep low-risk, authorized work autonomous. Human approval belongs at consequential boundaries.
- Successful machine review does not grant release authority.
- Classify individual actions within commands; assess the effects of pushes and merges, including deployment triggers.
- Start with static workflows. No autonomous topology expansion.
- Keep `/gstack-verify` advisory; incomplete verification must remain visible.
- Reuse existing governance and audit machinery where it meets the requirements.
- A nonce establishes freshness and linkage, not proof of substantive review.
- Limit the GA items to gstack and the shared declarations necessary to govern it.
- Other plugins in this repository carry their own objective sections and items.
- This repository has no Vercel project, no package.json and no Playwright suite, so the Endform E2E gate does not apply to it.
- The agent's GitHub identity is the `moxywolf-agent` GitHub App (App ID 5007349), created by Dorian on 2026-09-20 and made installable on any account the same day. Its key and `github-app.env` live in the vault's `_Shared Knowledge/Agents and Plugins`. No machine user. It has one installation per account, resolved per repository at mint time rather than pinned in configuration (GA-006); as of 2026-09-20, MoxyWolfLLC, OpenControls-AI and GRCSchema.
- `main` carries a ruleset that restricts updates, requires a pull request and blocks force pushes, with two bypasses: Repository admin, and the `moxywolf-agent` app for pull requests only, so the app can merge a pull request and can't push to `main` (2026-09-20). Loosening it further is an amendment to this document.
- The agent merges when Dorian tells it to, and only then. It merges as `moxywolf-agent[bot]`, through the pull request, and the merge is recorded as agent-executed on his instruction, never as a human release (Dorian, 2026-09-20).

## Items and acceptance criteria

### GA-001 — Reconcile authority and enforce evidence completeness

**Status:** review. Implementation prepared; independent review and human merge pending.

1. Build, ship, peer-review, and governance documentation express one consistent release policy. Routine branch work remains authorized; consequential release requires recorded human authorization.
2. Review success requires coverage of every expected acceptance criterion. Missing, duplicate, unknown, malformed, or unmet criteria cannot produce a passing outcome.
3. Fix verification accounts for every previous blocker. Omission cannot silently resolve a finding; deferral requires the applicable authorization.
4. Evidence and release authorization identify the exact reviewed revision and action. Changed code invalidates an earlier release authorization.
5. Tests demonstrate that unauthorized release is refused through the execution entry point, rather than only through a helper.
6. Applicable command tiers and the named Release Owner are recorded. The agent cannot manufacture the human’s approval.

### GA-002 — Declare and execute static topology

**Status:** review; implemented on the GA-001 feature branch foundation; human merge pending.

1. Introduce machine-readable workflows for CSO and verify first.
2. The executor consumes the declarations; they are not parallel documentation.
3. Each node declares dependencies, inputs, outputs, permitted effects, and failure behavior.
4. Cycles, missing dependencies, conflicting writers, and missing required results prevent successful completion.
5. Persist node attempts and evidence references. Resume preserves valid work and invalidates descendants when their inputs change.

### GA-003 — Optimize independent branches

**Status:** review; depends on GA-002; human merge pending.

1. CSO prepares scope and architecture before parallel audit branches; independent verification precedes one owned report.
2. Verify freezes claims and code before parallel checks; convergence verifies coverage and detects extra implementation.
3. Multi-repository reviews split only where acceptance criteria are independent; coupled changes retain integration review.
4. Enforce a concurrency cap. Shared-state proof commands remain serialized unless isolated.
5. Demonstrate overlapping execution without lost findings, conflicting writes, or false success after a worker fails.

### GA-004 — Complete governance records and data boundaries

**Status:** review; builds on GA-001 and GA-002; human merge pending.

1. Record approvals, stops, overrides, edits, and execution outcomes with owner, action, revision, and evidence references.
2. Reuse the shared gate-log where possible; report machine-review outcomes separately from human oversight.
3. Enforce declared data-use permissions before external reviewer dispatch and release checks before output leaves its permitted scope.
4. Report oversight timing and override rates as investigation signals, never automatic judgments.
5. Prevent resumed runs from replaying consequential actions already completed.

### GA-005 — The agent acts as itself, and its merges say so

**Status:** review. Merged as `ce7a5e6` (PR #27) on 2026-09-20, executed by `moxywolf-agent[bot]` on Dorian's instruction recorded on the pull request. **Merged without peer review at that head**: Gemini was over its daily quota and the OpenAI account had no credit, and Dorian chose not to wait. `record-release` requires a passing review, so it has recorded no release for this item and none was faked. Criteria 1 to 7, 10 and 11 are met, criterion 7 checked live (the bot's merge refused with 405 before the bypass, its direct write to `main` refused with 409 after). Criterion 8 waits on Dorian's answers per merge, and criterion 9 on the OpenControls-AI decision and the PAT leaving every connected folder. The item stays `review`, not `done`, until the file is gone, per its own criterion 9.

**Links introduced:** the commit-to-actor link. A commit, pull request or merge names a GitHub login, and every reader, `record-release` included, assumes that login is the one who acted. Today the agent acts under Dorian's login, so the link resolves and names the wrong actor. The token-to-installation link: a token is minted from the app key for one command and lasts an hour, and nothing assumes it outlives that. The merge-to-instruction link: an agent merge names the instruction it acted on, and a reader assumes that instruction covered this pull request. The backfill-to-confirmation link: each past merge this item marks as agent-executed names its evidence and Dorian's answer, and nothing is marked from a commit subject alone.

The gap was found and written down on 2026-09-12: the AP merges were executed by Claude with the vault PAT at Dorian's instruction, and `record-release` can't tell that from a human merge, because the PAT carries the owner's identity. It happened again on 2026-09-19 with PRs #23 and #24. The memory graph drawn that day marks it as node 14. The defect was never that the agent merged. Dorian told it to, and that's his call. The defect is that the record says a human released it. With the agent on its own login, an agent merge is visible as one, and a merge nobody asked for is visible too.

The GitHub half was done by hand on 2026-09-20 and checked through the API. A ruleset on `main` restricts updates, requires a pull request and blocks force pushes, with Repository admin as the only bypass. The `moxywolf-agent` GitHub App exists, installed on this repo only, with Contents write, Pull requests write and Metadata read. As the bot, the test opened PR #26, and GitHub refused its merge (405, "Cannot update this protected ref") and refused a direct write to `main` (409, "Changes must be made through a pull request"). `main` stayed at `c20699a`. The PR was closed and its branch deleted. That test proved the bot is locked out. Dorian then decided the agent merges when he says so, so the ruleset gets the app as a pull-request-only bypass (criterion 7).

1. `scripts/agent_token.py exec -- <command>` mints an installation token from `github-app.env` and the key file it names, both read from the vault's `_Shared Knowledge/Agents and Plugins`, and runs the command with the token supplied through `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n` or an environment variable. The token never appears in argv, stdout, stderr or a file. Test: a fixture key and a stubbed token endpoint; the command's argv, the script's output and the temp directory are searched for the token and it's found in none of them.
2. Minting runs where GitHub's `/app` endpoints answer. The cloud proxy refuses them (403, checked 2026-09-20), and the device shell reaches them, so pushes and pull requests run from the device shell. When minting fails, the script exits non-zero and names the endpoint and the status. It never falls back to another credential, and a test asserts no code path in `gstack-execution` reads `github-pat.env`.
3. Commits pushed and pull requests opened by the loop name `moxywolf-agent[bot]`. Check: the first pull request the loop opens after this merges shows `user.login` = `moxywolf-agent[bot]` through the API.
4. Every instruction that tells the agent to push or open pull requests with the vault PAT says the app instead. Repo homes: `gstack-execution/commands/gstack-build.md`, `commands/gstack-design-doc.md`, `GOVERNANCE.md` (the credential table), `scripts/docs.md`, `scripts/repo_gates.py`, `scripts/review_host.sh`, `README.md`, `project-init/skills/session-start/SKILL.md` and `project-init/skills/session-end/SKILL.md`. Changelogs are exempt because they record what was, and a test fixture that names the file is not an instruction. A test greps those files for push instructions naming the PAT and reports how many files it examined; zero examined is a failure, per EV-001. Vault and Taskade homes are changed by hand and the grep output goes in the review packet: `DR-011-github-pat-vault-file.md`, the team-shared INDEX commit rule, and this project's `cowork-project-instructions.md`.
5. `record-release` tells the two kinds of merge apart. A merge by the named human is `human_merge_recorded`, as now. A merge by `moxywolf-agent[bot]` with an instruction recorded on the pull request (criterion 6) is `agent_merge_on_instruction`, and the record carries the instruction's text, its time and the comment URL. A bot merge with no recorded instruction is refused as `release_blocked` and named as an unrequested agent merge. `agent_merge_on_instruction` is a new vocabulary term, so the vocabulary goes to 1.1.0, which is an XE-012 break point. Tests cover all three. It reads the merge record with the app token over REST when `gh` is absent, since the device shell has no `gh` (checked 2026-09-20).
6. Before it merges, the agent posts Dorian's instruction on the pull request as a comment: his words verbatim, the time, and the pull requests the agent read it as covering. An instruction like "merge whatever else we have" is listed back as the specific pull requests before any merge. Then it merges through the pull request as the bot and runs `record-release`. `gstack-build.md` and the `gstack-execution` skill say so in one place each.
7. Dorian adds the `moxywolf-agent` app to the `main` ruleset's bypass list with mode **For pull requests only**. Check: a throwaway pull request merges as `moxywolf-agent[bot]`, a direct write to `main` by the bot is still refused (409), and the pull request and branch are removed afterwards.
8. Merges to `main` that the agent executed are listed in this item with merge commit, evidence and Dorian's answer. The draft list comes from merge subjects: #6, #7, #8, #11, #12, #22, #23 and #24 carry hand-written subjects ("Merge PR #N:" or "Merge pull request #N:" with no "from"), and #4, #5 and #9 carry GitHub's button format. A subject is a hint, not proof. Each row is `agent`, `human` or `unknown` as Dorian answers it, and `unknown` stays unknown. No release record or merge commit is rewritten.
9. The PAT leaves the agent's reach: Dorian moves `github-pat.env` out of every connected folder. It also pushes to OpenControls-AI repos today, and the app is installed on MoxyWolfLLC only. So before it moves, Dorian decides the OpenControls-AI path: switch the app to installable on any account and install it there, or create a second app. Until the file is gone, this item's status is `review`, not `done`, and says why. Check: the vault folder listing shows no `github-pat.env`.
10. After merge, the memory graph's node 14 is marked closed with the date and this item's merge commit, and the swimlane's merge step shows two paths: Dorian merges, or the agent merges as the bot on his recorded instruction.
11. `gstack-execution` and `project-init` each get a minor version bump with a changelog line.

### GA-007 — The credential can say what it actually grants

**Status:** done. Merged to `main` in `3c79c86` (PR #39, head `571574b`) on 22 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, with its version in `2014ab5` (PR #40), without cross-tool review at that head. Reviewed retroactively on 25 September at exactly that head: review `20260925-084234-571574b-9yqea0s4` (codex/gpt-6-astra, `no_blocking_findings`, 5/5), CI run 35690572187 read by the dispatcher. No release record exists: `record-release` refuses a merge that predates its review, and Dorian ruled the item done with this note.

**Links introduced:** none. It reads the access-token response the app already receives and prints a field `mint()` was discarding.

The failure it closes, measured on 2026-09-21. `workflows` was added to the app's declared permissions and a push touching `.github/workflows` was still refused, with a message byte-identical to the one returned before the permission existed:

> refusing to allow a GitHub App to create or update workflow `.github/workflows/unit-checks.yml` without `workflows` permission

Changing a GitHub App's permissions raises a REQUEST. Until each installation accepts it, that installation's tokens carry the old set. Nothing in the refusal distinguishes "not declared" from "declared, not yet accepted", and the loop has no way to tell which state it is in, so it either waits on a change already made or re-makes a change already accepted. The answer was on the wire the whole time: every `access_tokens` response carries the granted permissions, and `mint()` threw them away. Finding it cost 25 minutes and required importing the module and calling `request()` by hand.

1. `agent_token.py permissions [--repo owner/name]` prints the permissions the resolved installation actually grants, and its `repository_selection`. Repository resolution is GA-006's, unchanged.
2. It reports the installation id it read, and whether that id came from `--repo` or from `github-app.env`, because GA-006 made those two different answers and a reader comparing output across repositories needs to know which one they are looking at.
3. The subcommand is reachable. `--selftest` asserts the usage text offers it and the function exists, because a subcommand nobody can dispatch to is the same defect as a gate nobody runs.
4. Step 4 of the build loop names the permission case alongside the installation case it already covers, and names this command as what tells the two states apart.
5. Evidence: the command run against two installations of the same app in the same minute, one that has accepted a permission request and one that has not, showing the difference the refusal message hides.

### GA-006 — A token is minted for the installation that owns the repository

**Status:** done. Merged to `main` in `27fd672` (PR #31, head `29dff5c`) on 21 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded as `agent_merge_on_instruction`. Review `20260921-142113-29dff5c-xs3jf4jy` (gemini/gemini-3.1-pro-preview, `no_blocking_findings`, 9/9 acceptance), with the `tests` workflow green on the same head.

**Release handoff prepared, release record blocked by where the review ran.** Unlike CI-001, this item has its handoff: `release.json`, `awaiting_human_release`, prepared at 2026-09-21T21:22:56Z, links 3 of 3 re-resolved, which predates the merge. `record-release` still could not run, for a different reason. The reviewer needs more wall time than the device shell allows, so the review ran in the session's cloud container and the record's `repos[].path` is that container's checkout. `record-release` requires `--repo` to resolve to exactly that path, and the only host where it does is the one where `api.github.com` answers 403 through the agent proxy. The device has the credential and the API; the cloud has the record. No record was fabricated.

The fix is not a contract change. A review whose slow step runs elsewhere should still be opened with the packet pointing at the host that holds the credential, so the record and the release land together. That is a change to how the loop is driven, not to what it requires.

**Links introduced:** the repository-to-installation link. Until now a token's scope came from a constant in a file, and every caller assumed that constant covered the repository in front of it. After this the scope is derived from the repository at mint time, so the token names where it came from, and a repository the app cannot reach becomes a named refusal rather than a 404 the caller has to interpret.

GA-005 criterion 1 mints from the single installation id in `github-app.env`, and the app-identity constraint named it. That held while the app was installed on one account. It stopped holding on 2026-09-20, when GA-005 criterion 9 asked Dorian to choose the OpenControls-AI path and he chose it, making the app public and installing it on OpenControls-AI. A token minted from the MoxyWolfLLC installation answers 404 for `OpenControls-AI/cki`, which is the same answer GitHub gives for a repository that does not exist. The credential's reach therefore fails in the shape hardest to read, and it cost most of a session to that reading before the cause was found.

1. **The installation is resolved from the repository.** With a repository in hand the script asks `GET /repos/{owner}/{repo}/installation` with the app JWT and mints against the id that comes back. The id in `github-app.env` is a fallback used only when no repository can be determined, and it is never preferred over a resolved one.
2. **The repository is found where the caller already says it.** `--repo owner/name` when given; otherwise the `{owner}/{repo}` in an `api` path that begins `repos/`; otherwise `origin`'s URL in the working directory for `exec`. When none of the three answers, the script says which it tried before falling back.
3. **A wrong-installation failure never reads as a missing repository.** When a resolve fails, the script says the app is not installed on that owner, names the owner and the accounts it is installed on, and exits non-zero. It does not retry with the fallback id, because that token produces the same 404 and a second identical failure reads as a flaky network.
4. **One lookup per invocation, and nothing cached.** The resolve costs one request against the JWT the script already mints. Nothing writes the mapping to disk, because an installation can be removed between runs and a cached id would fail as a 404 long after the cause.
5. **The constraint stops naming one installation.** This document's app-identity constraint names the app and its key, not a single installation id, and says the installation is resolved per repository.
6. **Evidence.** `scripts/test_agent_token.py`: a stubbed `/repos/{owner}/{repo}/installation` returns an id different from the env's and the mint is asserted to use the resolved one; a resolve that 404s produces the not-installed message naming the owner and does not fall back; the `api` path parser and the `origin` URL parser each cover ssh and https remotes; no path writes an id to disk. The suite reports how many checks it examined and fails when it examines none, per EV-001. `scripts/run_all_tests.py` runs it.

## Second objective: academic-pipeline integrity

Goal: the pipeline must not encode a fact it cannot know. Names, filenames, and required sections come from run data or from the user, never from a template constant, and a mechanical gate reports what was checked before anything is presented as finished.

### AP-001 — Derive deliverable names and attribution from run data

**Status:** done. Review 20260911-163931-423bd0a-bo_glftu, fixes_verified; merged as 6603aae.

1. Stage 7 writes its deliverable to a name derived from the Stage 1 target slug. The orchestrator's artifact table and Stage 8's input reference that same name.
2. Stage 1's diagram deliverable is derived from the target slug likewise.
3. No skill contains a person's name as a worked example. The author block is populated from the vault voice profile or by asking. Inventing a name is forbidden in text.
4. Tests: grepping the plugin tree for the literal strings `complete_document.md`, `mermaid_diagram.md`, and the fabricated surname each return zero hits.

### AP-002 — Every declared requirement has a producer

**Status:** done. Review 20260911-165938-d11564a-g289mqlt, fixes_verified; merged as 856f5c6.

1. End-matter sections declared in Stage 4 appear in Stage 5's `structure_plan` whenever the venue requires them.
2. Stage 6 writes those sections as ordinary sections.
3. Stage 6 carries an explicit rule to number Vancouver citations by first appearance while drafting, rather than leaving order to a later repair.
4. Tests: a fixture run produces every section named in the formatting requirements' `section_order`.

### AP-003 — Mechanical release gate before completion

**Status:** done. Review 20260911-165938-d11564a-g289mqlt, fixes_verified; merged as 856f5c6.

1. The orchestrator runs a gate before presenting deliverables: zero em dashes, zero forbidden phrases, renumber `--check` exit 0, every `section_order` entry present, and no two references sharing a normalized DOI or URL.
2. Stage 7 dedupes on normalized DOI/URL, not only on BibTeX key, and warns when two keys resolve to one work.
3. The gate names each check and its result. A failing gate blocks the completion report rather than being narrated around it.
4. Tests: the gate run against a fixture carrying a planted em dash, a duplicate URL, and a missing section fails on exactly those three.

## Third objective: evidence integrity

Goal: a report is treated as evidence only when the links between it and the work it
describes still hold. Completeness checks items; nothing checked links. Every defect in
this objective is a link that still resolved after the thing at its other end had
changed, which produces a complete report, no error, and a person about to sign it.

Derived from "When Structure Pays" (Cougias, 2026), which reports three such defects in
this repository's own executor plus three false passes in its own completeness gate.

### EV-001 — No check reports a pass over input it did not examine

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** none; this item removes a false one (a verdict that implied
coverage it never had).

1. Every check returns what it examined and in what unit, and a PASS with zero coverage
   becomes a FAIL naming the shortfall. The rule is applied where results are assembled,
   so no later check can opt out of it by forgetting to.
2. A check that does not apply returns SKIP, is printed as SKIP, and is counted in the
   summary line. It is never folded into a green line.
3. Each check carries a seeded defect it must catch, because a repair verified only
   against the case that was reported reproduces the defect it is repairing.
4. Tests: a paper with no reference list fails `duplicate_sources` for examining nothing;
   an empty forbidden-phrase list and an empty `section_order` fail rather than report a
   clean paper; a non-Vancouver paper skips rather than passes citation order.

### EV-002 — Findings bind to content, and every link re-resolves on demand

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner, on the evidence as it stood and without a fresh review of the final head. Reviewed as `20260912-122421-80159e3-_lrr97ak` (codex/gpt-6-astra, `rounds_exhausted`): six blockers raised, five verified fixed by the reviewer. F2 was raised three times, as a missing round record, then a record carrying only an outcome, then fields checked for presence but not shape; repairing the third surfaced a fourth instance, two later sweeps re-reading the rounds without the shape check. The third repair and the one-walk change that followed it carry regression tests and no reviewer sign-off, because the round limit was reached first. **The record that review ID names no longer exists.** See EV-009: it was written to a session-local home and destroyed with the session, so what follows from it in this document is reconstruction from the pull request and the commit messages, not a record a reader can pull on.

**Links introduced:** a per-finding subject (blob id plus a span hash at the reviewed
head) retained in `round-N.json`; the `verify` report's re-resolution of that subject at
the repository's current head.

1. The dispatcher, not the reviewer, binds each finding to the content at the reviewed
   head when the round is recorded.
2. `verify` re-resolves the packet's commits, every finding subject, every disposition,
   and every recorded observation, and names each link it examined.
3. Drift expected from a repair is not reported as staleness; drift under any other
   disposition is.
4. A missing entry and a link that resolved to the wrong thing do not share an outcome
   name, and a record that cannot be re-resolved is a third answer.
5. `release` refuses on `stale_link` and `incomplete_record`.
6. Tests: content changing under an undisposed finding is stale; the same change under a
   `fixed` finding is not; a hand-edited span is detected; a snapshot-prefixed path and a
   repo-relative path bind to one subject.

### EV-003 — The undeclared-write sweep, in the direction nobody had

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** the declaration-to-behaviour link for every handler, checked at
runtime rather than against other declarations.

1. `run --audit-writes` hashes the run root before each node and after its handler
   returns, before declared outputs are written, and fails a node that wrote a path no
   declaration mentions.
2. The sweep forces serial execution, because attributing a write while several nodes are
   writing would be a declaration that can be false.
3. The exclusion of executor-owned files has one home.
4. Reads are not instrumented; a declared dependency that nothing reads is still
   undetected and is stated as a limit rather than implied to be covered.
5. Tests: a handler writing an undeclared path fails by name; a clean graph passes; audit
   mode does not overlap nodes.

### EV-004 — The approver's reconstruction gets a field

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** each observation's claim-to-command-to-output link, re-runnable by
`verify`.

1. `release` records, per repository, that the release head is the reviewed head, with
   the command and a digest of its output, plus any observation the approver adds.
2. The record states plainly that it captures what was run, not that a person read it.
3. `verify` re-runs recorded observations and reports one that no longer holds.
4. Tests: the automatic observation is recorded and re-verified; a stale digest is caught.

### EV-005 — Each item declares the links it introduces

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** none.

1. The design-doc template carries a `Links this item introduces` column and says to
   derive it from the change rather than copy another item's.
2. `/gstack-build` treats an item that introduces state with no declared links as not yet
   covered, and amends the doc before any code.
3. The review packet carries that row, and the reviewer rules on each link in both
   directions.

### EV-009 — A review record outlives the session that produced it

**Status:** done. Merged as `7b72605` (PR #10) on 2026-09-17 by the Release Owner. Review ID not carried here; see the pull request.

**Links introduced:** the review ID to its record on disk, which is the link this item
exists because it was already broken.

Found on 14 September 2026 by going to pull review `20260912-122421-80159e3-_lrr97ak`,
cited as the evidence for EV-002 one day after merge. `REVIEW_DIR` defaulted to
`$HOME/.gstack/peer-review`. In a sandboxed session `$HOME` is per-session and outside
every connected folder, so every record written there was destroyed when the session
ended. The identifier went on reading like evidence in this document, which is the same
failure the EV items were built to catch, in the governance record of the fix for it.

1. `GSTACK_PEER_REVIEW_DIR` is required and has no default. A review that cannot name a
   durable root does not open, and the error says what to set and why.
2. No code path falls back to the home directory, and a test asserts that against the
   source rather than against one call, because the defect was a default rather than a
   call site.
3. The command, the contract and `docs.md` all state the requirement, so the three places
   a reader could learn the old default agree with the code.
4. Tests: `review_root` exits naming the variable when it is unset; a declared directory
   is used as given; the source contains no home-directory fallback.

**Open:** graph-driven reviews already land in the run directory because `task_graph.py`
sets the variable. Direct invocations were the unprotected path, and nothing here recovers
the records already lost.

### EV-006 — Instrument reads

**Status:** building. Merged in part; criterion 1 is still open. Criterion 2 is met: a declared dependency the consumer's result gives no sign of using is reported as a candidate fake edge, surfaced in the report node. Criterion 1 is NOT met and is not claimed. Dependencies reach a command handler inlined in input.json and a model handler inlined in its prompt, so there is no per-dependency read to observe without changing the payload contract every existing handler depends on. What is measured is whether the handler's result references the dependency, which is a proxy: unreferenced is not proof of unused, so it is reported and never fatal. Upgrade path, mechanism verified 2026-09-17: per-dependency files make reads observable through atime, given the aging described in EV-008. Merged as `8bd7fae` (PR #18) on 2026-09-17.

**Links introduced:** the read side of every handler's declaration.

1. A node's declared inputs are compared against what its handler actually read.
2. A declared dependency that nothing reads is reported, completing the fake-edge test in
   both directions.

### EV-007 — Reference identity and archive at citation time

**Status:** done. Criterion 1 is met for identifiers whose canonical form is mechanical — arXiv, DOI and PubMed ids resolve to one work identity regardless of URL form, case or resolver, and the check reports which rule produced each identity. Linking a preprint to the DOI it later received needs a registry lookup, is not attempted, and the two remain separate works. Criterion 2 is met: cited URLs are archived at citation time to the Wayback Machine AND stored as a local copy beside the bibliography (Dorian, 2026-09-17, chose both), with the SHA-256 of the archived snapshot. The hash covers the SNAPSHOT, not the live page: hashing live HTML detects ad and timestamp rotation rather than drift, so this proves "this is the page I cited", not "the page has not changed". Persistently resolvable identifiers are skipped and recorded as skipped. An unreachable archive never blocks a citation; it is recorded with its reason, and the gate reports coverage from the record without touching the network. Criterion 3 is met: cited commits, test files and review identifiers resolve in the named repository, and a paper with no repository available returns SKIP rather than PASS. Merged as `8bd7fae` (PR #18) on 2026-09-17; criterion 2 archiving as `4c6e11a` (PR #19).

**Links introduced:** the reference-to-work link (identifier to canonical work) and the
citation-to-snapshot link.

1. References resolve to a canonical work identity before comparison, so one study cited
   as a preprint and as its announcement is detected as one work rather than two strings.
2. Every cited URL is archived at citation time and the reference stores the snapshot and
   its hash.
3. Every commit, test name and review identifier a manuscript cites resolves in the named
   repository at the cited commit.

### EV-008 — Record what a review examined, not only what it found

**Status:** building. Merged in part; criterion 1 (commands run) and criterion 3 are still open. Criteria 1 and 2 are met for file reads: the round records which surface files the reviewer opened, how many were offered, and whether it looked beyond the diff. Commands the reviewer ran are NOT recorded — the CLIs differ in what they report and some report nothing — so criterion 1's second half is unmet and unclaimed. Criterion 3 is not built; routing ad-hoc consultations through a recording address is a separate change to how tools are invoked, not to the review record. Merged as `8bd7fae` (PR #18) on 2026-09-17.

**Links introduced:** the review-to-search-space link.

1. A round records the paths the reviewer opened and the commands it ran.
2. A round that examined nothing outside the diff is visible as such.
3. Ad-hoc consultations with other tools are conducted through an address that leaves a
   record, so the denominator of a search stops being unknown.

## Fourth objective: execution economy

Opened 2026-09-17 after an audit of a three-day Codex session that built the OpenControls support platform. That session spent 2,319 tool calls to produce 54 file changes, 1,039 of them browser calls where an API existed, and was interrupted 43 times by approvals that re-derived authority the human had already granted. The implementation stayed small, so the restraint layer did its job. The cost was in the loop around the change, which no item in this design governs.

The premise: **a loop that cannot prove its own preconditions pays for them at the slowest point, and an approval that must be re-derived is not a decision, it is an interruption.** Completeness is a property of the change. Economy is a property of the path taken to make it, and that path is not in the diff.

Each item's `**Status:**` below is the only record of what is built. This preamble deliberately restates none of it: the previous version carried a count that contradicted the statuses beneath it within a day, because a fact with two homes drifts on the first merge that touches one.

### XE-001 — The gate proves it can run before anything is pushed

**Status:** done. Review 20260917-193232-339fea5-afng5hkw (gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance); merged as f1a1034.

**Links introduced:** none. The preflight report is derived from the working tree at call time and is not stored.

1. `endform_workflow.py preflight --repo <path>` answers, locally and without network, whether the E2E gate can run in this repository, and names every condition it examined.
2. It fails when the Playwright project root and the workflow's run directory differ, which is the defect that cost two push/CI/fix cycles in the audited session.
3. It fails when a `tsconfig` the test project extends resolves outside that project root, which is the defect that cost a third.
4. It reports every `secrets.*` name the workflow references, so a missing CI secret is discovered before the push rather than by a red check.
5. Per EV-001, a condition that could not be examined reports `SKIP` and is distinct from `PASS`, and a run that examined nothing exits non-zero rather than reporting success.
6. `/gstack-build` runs it once per repository before the first item and refuses to treat a red E2E gate as a code defect until it is green.

### XE-002 — An approval binds to a scope, and re-resolves

**Status:** done. Review 20260917-193232-339fea5-afng5hkw (gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance); merged as f1a1034.

**Links introduced:** a capability grant ledger. Each grant links a human decision to an action class and a resource pattern, and every subsequent action re-resolves against it.

1. An approval writes a structured grant, not a sentence. The grant carries the action class, a resource pattern, a scope of one-shot, session or project, and the granting human.
2. The checker matches a pending action against the ledger by pattern. It never re-reads the prose of a prior approval to decide whether that prose covers a new action.
3. A grant that does not match prompts once and writes a new grant. The prompt names the class and pattern being granted, so the human decides policy rather than re-deciding the same act.
4. Action classes that stay one-shot by construction: production data writes, sending mail to a real recipient, and merge.
5. This inherits EV-002's mechanism. Findings bind to content and re-resolve; grants bind to a scope and re-resolve. Neither re-reads prose to decide whether a link still holds.
6. **The ledger is not a security control.** It is written by the process it governs, exactly as `GOVERNANCE.md` already says of the review state files, so an agent that can write a grant can write its own. What the ledger buys is the human's attention, not containment. The containment is `ONE_SHOT_ONLY`, a set of classes no grant satisfies in advance at any scope, and protected-branch enforcement outside this process. An item that moves a class out of `ONE_SHOT_ONLY` is amending that boundary and needs the amendment, not a code change.
7. The ledger widens what a packet's `data_use` policy covers. It never removes a refusal: the owner, classification and repository/history checks are unchanged, and an action with no matching grant is still denied rather than resolved by re-reading a prior approval.

### XE-003 — The cheapest surface that answers the question

**Status:** done. Built and reviewed (20260917-204651-c8e63f7-humw079_, gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance). PR #14, merged as `d26c18a` on 2026-09-17.

**Links introduced:** none.

1. The tool order is connector, then CLI, then REST, then browser. A browser call is the last rung, not the first.
2. A session that uses a browser where a connector for that service is configured says so, and says which rung it took.
3. Where a browser is genuinely required, the page is read as structure rather than as pixels, and a query-focused read is preferred over a full snapshot on any page large enough for the difference to matter.

### XE-004 — A checkpoint is a batch, not an item

**Status:** done. Built and reviewed (20260917-204651-c8e63f7-humw079_, gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance). PR #14, merged as `d26c18a` on 2026-09-17.

**Links introduced:** none.

1. Cross-tool review runs at a checkpoint covering several items, not once per item.
2. A review is dispatched and collected. The dispatching session does not block on it and does not narrate its progress while it runs.
3. The audited session produced 51 messages whose entire content was that a review had not yet returned. That is the behavior this item removes.

### XE-005 — A reviewer is independent by what differs, not by its name

**Status:** done. Review 20260917-193232-339fea5-afng5hkw (gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance); merged as f1a1034. Criterion 6 (per-entry output headroom) was NOT in that merge's acceptance criteria and so was not reviewed; it is built in the XE-003/XE-004 checkpoint.

Criterion 4 carried a defect from that merge until 2026-09-21: `round` resolved the reviewer and wrote it to the round record but never back to `state.json`, and `status` reads `state.json`. A review run on gemini because codex was absent therefore reported `reviewer: codex, reviewer_is_fallback: false`, which is precisely the unrecorded fallback the criterion forbids. Found while confirming which tool had reviewed RR-001. Fixed on `build/RR-001-retrieval-review`; the intended reviewer is retained as `reviewer_intended` rather than overwritten.

**Links introduced:** none. The reviewer table is static configuration in the dispatcher, not stored state.

The dispatcher hardcodes two tools and derives the reviewer as "the other one". That encodes independence as a name rather than as a property, and two things already break it. Cursor can run Claude models, so a Claude builder reviewed by Cursor could share the builder's model family while satisfying every current check. And when the only named reviewer is unreachable, as happened on 2026-09-17 when Codex was first absent and then refused by its API for billing, the loop has nowhere to fall back to and the checkpoint lands unreviewed.

1. Reviewer routing is a table of `{tool, model_family, floor, invocation}` rather than a two-key map of builder to other tool. Adding a reviewer is a table entry, not a change to the dispatch path.
2. A reviewer whose `model_family` matches the builder's is refused before it runs, under an outcome distinct from `review_unavailable`, because a harness swap is not an independent mind and a record that cannot tell the two apart is worth less than no record.
3. The review record names the reviewer's tool **and** its model family, so a later reader can see what independence was actually obtained rather than inferring it from a tool name.
4. Fallback to a second reviewer is permitted only among entries whose family differs from the builder's, and the record says which reviewer ran and that it was a fallback. A fallback that is not recorded as one is a silent downgrade.
5. A reviewer response cut off at its output limit reports `output_truncated`, distinct from `malformed_output`. The two have different causes and different fixes, and collapsing them makes a headroom problem look like a broken reviewer. Gemini truncated a long structured response twice in this team's only run of it, during the 2026-09-15 Council deliberation, and the reviewer contract demands a longer and stricter structure than that deliberation did.
6. Each table entry carries its own output headroom, set against the reviewer contract's full response rather than a provider default. Precedent: the Council Sonnet-5 slot was configured at 3000 tokens and needed 12000, and under-provisioned it returned empty content while the dispatcher still reported success.

### XE-006 — The repo runs its own checks, or it has no gate

**Status:** done. Merged as `0abc472` (PR #16) on 2026-09-17. Review ID not carried here; see the pull request.

**Links introduced:** none.

This repository ships the verification discipline and does not apply it to itself. It carries eight
test files and four `--selftest` entry points, and no `.github/workflows` directory at all. Every
"suites green" reported during the XE objective was a human running commands in a sandbox and
reporting the result. Nothing ran at the boundary, so nothing stopped a broken dispatcher from
merging except attention.

The E2E gate is correctly scoped to Vercel-deployed repositories, and this is not one: there is no
`package.json`, no `vercel.json`, and no page to drive. Adding Playwright here would manufacture a
green check over nothing, which EV-001 already forbids. The error was not the missing browser suite.
It was reading "the web gate does not apply" as "no gate applies."

1. Every pull request and every push to `main` runs the repository's own checks in CI, and the
   merge is gated on them.
2. The runner reports what it examined — how many suites it discovered and ran, by name — rather
   than reporting only a verdict.
3. A run that discovers zero suites fails. A gate that finds nothing and exits green is the exact
   false pass this objective exists to remove, and it is how a gate silently dies when files move.
4. The check the loop requires is the one matching the repository kind. A repository with no web
   deployment is not exempt from having a gate; it is exempt from having *that* gate.

### XE-007 — The reviewer gets the change and its callers, not the tree

**Status:** done. Merged as `0abc472` (PR #16) on 2026-09-17. Review ID not carried here; see the pull request.

**Links introduced:** none. The surface is derived per round from the pinned commits; it stores nothing.

Every review in the 2026-09-17 session ran close to its time limit, and three did not finish at all.
The cause was measured, not guessed: the reviewer is handed a detached worktree of the whole
repository — 776 files, 31 MB — to answer a question about a 4-file, 172-line diff, and spends its
budget reading the repository. The same prompt and model against the change and the files it touches
returned a valid review in 81 seconds. This is XE-003's principle applied to the review loop itself.

The naive fix is wrong. Handing over only the changed files removes the reviewer's ability to see
that a change breaks an untouched caller, which is where the substantive blockers come from.

1. The reviewer receives the diff, the files it changes, and the files that reference those files —
   not the repository tree.
2. The surface is bounded, and when the bound excludes candidate files the excluded set is reported
   rather than silently dropped.
3. The surface states its own limits to the reviewer, and a reviewer that needs a file the surface
   does not carry reports that as a finding rather than guessing.
4. The round record names how many files the review could see and how many were withheld, so a later
   reader can tell a narrow review from a thorough one.

### XE-008 — A fact with two homes drifts; a format with one producer cannot

**Status:** done. Merged as `dbbe5dd` (PR #17) on 2026-09-17. Review ID not carried here; see the pull request.

**Links introduced:** none.

On 2026-09-17 the same defect shipped three times in one session: a design-doc preamble contradicting
the item statuses beneath it, a surface path format updated in its writer and not its parser, and a
function deleted after grepping the tests and not the callers. Checks caught all three. Reading
caught none — and verification check 5, "before changing a rule, find its second home", was already
written in four files and injected into every turn of that session. Restating it a fifth time is the
intervention that had already failed, which is the same shape as XE-003.

The three cases do not share one fix, and pretending they do is how a single mechanism gets credit
for coverage it does not have.

1. Where a fact can have one home, it has one. Prose does not restate a status that a structured
   field already carries.
2. Where a format crosses a boundary, one function emits it and the same function's output is what
   the parser accepts, so the two cannot drift. A test asserts the round trip rather than restating
   the spelling, because a spelling copied into a test is another home.
3. Where neither applies — a function's callers cannot be structurally prevented — the dispatcher
   computes which files reference the change and were not themselves touched, names them to the
   reviewer, and says what to do with them. The builder asserting "I checked the callers" is worth
   what the prose rule was worth.
4. This is a report routed to the reviewer, not a gate. Referencing a changed file is not an error,
   and a check that cannot fail must not be dressed as one.

### XE-009 — A review that cannot finish is not a review

**Status:** done. Merged as `2733a56` (PR #20) on 2026-09-17. Review ID not carried here; see the pull request.

**Links introduced:** none.

XE-004 split review into dispatch and collect so the loop would stop blocking. It could not actually
be used: Cowork's `device_bash` caps each call and gives it a PID namespace torn down on return, so
a dispatched review is reaped before it writes anything. Three reviews died that way on 2026-09-17,
and one change reached its pull request unreviewed as a result. The vault records the same class of
failure on 2026-06-13, where a reasoning model tripped a 45-second sandbox cap.

The wrong fix is available and tempting: pick a faster model, or trim acceptance criteria until a
review fits the clock. Both buy a pass rather than earning one, and the second is the XE-005.6
error — criteria narrower than the item, so the review passes something unfinished.

1. A review host is stood up by one idempotent script: reviewer CLI, checkout, and the environment
   a review needs.
2. Credentials are read from files, never passed as arguments, so they do not appear in `ps` or
   shell history.
3. The script fails loudly and specifically when it cannot do its job, rather than leaving a
   half-prepared host that fails later at the review.
4. The build loop names when to reach for a host, and names the two wrong fixes so they are not
   discovered independently by the next session.

### XE-010 — A packet narrower than the item it claims is not a review

**Status:** done. Merged as `1cff7f5` (PR #22) on 2026-09-18. Review ID not carried here; see the pull request.

**Links introduced:** the packet-to-declared-item link. A packet names the items it claims; the
coverage report binds each declared criterion to a score against that packet.

On 2026-09-17 a review returned `no_blocking_findings` at 13/13 on a packet whose acceptance
criteria were narrower than the items it claimed. XE-005 criterion 6 was never in the packet, so the
review could not have examined it, and it merged unbuilt. Scoring that day's packets against their
declared items afterwards found four of the same shape — XE-001 #6, XE-002 #3, EV-008 #1 and #3 —
two of which nobody had noticed. A review is only ever as wide as the criteria it is handed, and
nothing checked that width.

1. A packet names the declared items it claims, explicitly. It is not inferred from the packet's
   prose: packets are reused and their outcome text goes stale, which mis-mapped two reviews the
   first time this was measured.
2. Each declared criterion of each claimed item is scored against the packet's acceptance criteria,
   and a criterion no acceptance criterion tests refuses to open the review.
3. The gate is monotonic. It can refuse to open a review and can never approve one, because a score
   that removes a gate fails open exactly where being wrong matters most.
4. Opening anyway requires an explicit flag, and the review state records that it was overridden
   rather than covered.
5. A scorer that did not run is recorded as not run, never as covered. Not running it authorises
   nothing, so it must not block every review on a paid third-party service; it must also never let
   a later reader believe coverage was checked when it was not.
6. The extractor's own coverage is checked by a second independent count, and a partial extraction
   refuses to score rather than passing over what it did not read.

### XE-011 — One vocabulary for what the loop's agents hand each other

**Status:** review. Merged as `c20699a` (PR #24) on 2026-09-20 with SM-002 as one checkpoint. Criteria 1 to 5 are built: `vocabulary.json` 1.0.0 with 48 concepts, the dispatcher loading its outcome set from it, `vocab_check.py`, and version stamping on packets and round records. Criteria 6 to 8 are superseded by XE-012, which measures forward because this item's baseline was lost when it merged before any measurement ran. The review state of that merge is not recorded in this document and was not established when this status was written.

**Links introduced:** the term-to-definition link. A packet, round record or design status names a term by its id, and a reader assumes the definition that id carries today. The vocabulary is versioned, and a record cites the version it was written against, so a changed definition is visible in the record rather than silently read into it.

Agents in this loop spend tokens working out what the words in their own contracts mean, and spend more when two of them work it out differently. Three cases, all from this repository and this project:

- F2 on PR #9 was raised three times over one question, what a complete review round is: first a missing round, then a round carrying only an outcome, then fields checked for presence but not shape. The contract defined the round in prose, and the builder and the reviewer each read the prose.
- This file's own item statuses. The template allows five values: `planned`, `building`, `review`, `done`, `dropped`. On 2026-09-19 the `**Status:**` lines used ten spellings, including `built`, `built, partially` and `declared, building in this change`, none of which is in the set, and XE-003 read `done` and `human merge pending` in one line. Five items said `declared, building in this change` after they had merged.
- The MOXY board query used `project-moxywolf-plugins` while the board labels with `moxywolf-plugins`. The query returned zero rows, and zero rows read as an empty backlog rather than a wrong query. Corrected 2026-09-17.

The claim this item tests is that meaning defined once, with a stable id, is cheaper than meaning re-derived on every task. It's a claim, not a result. The cost of building and maintaining the vocabulary is real, so the item is judged on cost per correct answer across repeated tasks, maintenance included, and the decision rule is fixed before the measurement runs.

Scope is gstack-execution's own contracts. `project-init`, `team-kanban` and the other plugins adopt it only in a later item, and only if this one pays.

1. One file, `plugins/gstack-execution/skills/gstack-execution/references/vocabulary.json`, defines every term the peer-review contract, the packet, the round record and the design-doc template name as a controlled value, and nothing else. Seed set: review round, finding, blocking finding, every round and review outcome the dispatcher emits, sign-off, Release Owner, packet, acceptance criterion, item status. Each entry carries an id, a one-line definition, and where the term has a machine shape, the shape itself (the enum, or the JSON Schema fragment the validator uses). The file carries a version. Terms use SKOS labels (`prefLabel`, `definition`, `inScheme`) so the file reads as a standard concept scheme and not a format this repo invented.
2. The shapes in the vocabulary are the ones the code enforces. The dispatcher's outcome set and the round-record schema are loaded from `vocabulary.json`, not restated as literals in `peer_review.py` or its siblings. A test asserts that every outcome string the scripts can emit is a vocabulary id, and fails on a literal outside it. This is XE-008 criterion 2 applied to meaning: one producer, and the reader accepts what that producer emits.
3. `vocab_check.py` (or a `--selftest` case on an existing script) reports, for the design doc and each contract file: files examined, term uses found, uses that resolve, and uses that don't. It fails on an item status outside the vocabulary. It fails on a contract that restates a definition the vocabulary holds, detected as the definition text appearing outside `vocabulary.json`. It fails when it examined zero files or zero term uses, per EV-001.
4. Every `**Status:**` line in `DESIGN.md` uses a vocabulary status id, followed by free prose. `vocab_check.py` passes on the doc as committed.
5. A round record and a packet name the vocabulary version they were written against. `peer_review.py verify` reports a record whose version differs from the current vocabulary as `vocabulary_drift`. That's a report and not a failure, since an older record isn't wrong for being older, but a reader has to be able to see it.
6. Superseded by XE-012 on 2026-09-19. The baseline this criterion required was lost when this item merged before any measurement ran, so a before-and-after on one fixed task set is no longer possible. Measurement runs from here on under XE-012, and each vocabulary version is a break point.
7. Superseded by XE-012 on 2026-09-19. The decision rule survives there as prediction P1 and its refutation condition.
8. Superseded by XE-012 on 2026-09-19. What the measurement cannot see is XE-012 criterion 9.

### XE-012 — Every gstack run records what it cost, against predictions stated before the data

**Status:** review. Merged as `56dca19` (PR #25) on 2026-09-20, executed by `moxywolf-agent[bot]` on Dorian's instruction recorded on the pull request. **Merged without peer review at that head**: the last review, `20260919-214027-cbdc848-bwwwt75e`, ended `review_unavailable` after its round-1 findings were fixed, and Dorian chose not to wait. `record-release` has recorded no release for it, for the same reason as GA-005. Criteria 1 to 5 and 7 to 9 are built. Criterion 6 is built as `measure.py report` and **the weekly scheduled task is not registered**, so the first report was run by hand on 2026-09-20. Criterion 10 is added by the 2026-09-20 amendment and is not built. Two defects found after merge are open: the report prints `reviewer tokens 0 (reported rounds only)` for a run whose total is null, and a `thin-review rate 0%` over a null field, both of which this file's own rule forbids (EV-001, and `measure.py`'s docstring).

**Links introduced:** the run-to-transcript link: a run record's token counts come from a session transcript over a stated time window, and transcripts are ephemeral, so the record carries the counts, the window and the transcript's path at capture, and never assumes the path resolves later. The run-to-review link: the record names its review ID. The run-to-vocabulary link: the record names the vocabulary version it ran under, which is what makes a version change a break point.

XE-011 claims that meaning defined once is cheaper than meaning re-derived on every task. Nothing measures it. Its baseline was lost when it merged before any measurement ran, and Dorian decided on 2026-09-19 to measure from here on and treat each vocabulary version as a break point.

One measured session sets the scale. The session of 2026-09-19 that built SM-002 and XE-011 had, by 04:16 UTC on 20 September, run 190 assistant turns and 201 tool calls, written 146,655 output tokens and 1.46 million tokens to cache, and read 83.3 million tokens from cache, so cache reads were 98.1% of its tokens. The first count of the same session read 363 turns and 157 million cache-read tokens. It was wrong: the transcript logs one assistant message as several entries that repeat the same usage, and counting entries instead of message IDs nearly doubled it. That is this item's first finding, reached before any of it was built. Almost all of the cost is the agent re-reading its own context on every turn. So the lever is turns times context size, and the saving a shared vocabulary could buy is fewer turns spent rediscovering meaning and state, not shorter messages. The predictions below are written to that.

1. At `release`, and on demand, one record per gstack run is written: items, repo, reviewed head, review ID, vocabulary version, builder and reviewer model IDs, rounds used, outcome, files the reviewer examined against files offered, and whether it looked past the diff.
2. The builder's cost for the run is taken from the session transcript over an explicit window, from the run's first commit to `release`: input, output, cache-write and cache-read tokens, assistant turns and tool calls. The record states the window and the transcript path. If the transcript cannot be read, the token fields are `null` with the reason, never zero, per EV-001.
3. Each review round records the reviewer's own token usage as its CLI reports it. A CLI that reports none is recorded as `not_reported`, never as zero. The coverage scorer's input tokens, already recorded, are carried into the run record.
4. The record is an Obsidian note at `MoxyWolf Vault/Projects/Moxywolf Plugins/11-Knowledge/measurements/gstack-runs/<date>-<review-id>.md`, every number a frontmatter property, and a `.base` file in that folder lists runs and totals them by vocabulary version. The vault is the one home for these numbers; the repository keeps only the review records they point to.
5. A `correct` property is `pending` when written and only the named human sets it to `true` or `false`. Nothing else writes it, per the team's HITL rule. Cost per correct run counts only runs marked `true`, and pending runs are reported as pending.
6. A weekly scheduled report reads the notes and writes, per vocabulary version: runs, runs marked correct, builder and reviewer tokens per correct run, cache-read share, rounds per review, repeat findings, and the thin-review rate. It scores each prediction as supported, refuted, or insufficient data, and a version with fewer than 10 correct runs is insufficient data for any prediction. The report goes in the same folder with the date in its name.
7. Every record carries the model IDs, and any comparison across vocabulary versions that also crosses a model change says so in the report.
8. The predictions below were written on 2026-09-19, before any run was recorded, and commit the refutation condition with them. Changing a prediction after data exists is an amendment that keeps the original text beside the new one.
9. What the measurement cannot see is stated in every report: commands the reviewer ran and ad-hoc consultations (EV-008 criteria 1 and 3), per-dependency reads (EV-006 criterion 1), human time, and the measurement's own cost, which is counted and reported rather than hidden inside the totals.
10. Each run note records the packet's size in tokens and the context size at the run's first and last measured turn. A study of 2,451 coding agents reports the active context holding between 7,949 and 8,452 tokens while windows ranged from 38,886 to 644,962, so if that pattern holds here, packet width is a lever that can be measured rather than assumed. Recorded only: no prediction is attached to it until there is data.

**Predictions, stated 2026-09-19 before any data.**

- **P1. The vocabulary pays for itself.** Across the first two vocabulary versions with at least 10 correct runs each, builder tokens per correct run fall from the earlier version to the later one, net of tokens spent in commits that change `vocabulary.json`. Refuted if they do not fall. If refuted, XE-011's original rule applies: the vocabulary is frozen at its seed terms and no other plugin adopts it.
- **P2. Re-reading is the cost.** Cache reads are at least 90% of builder tokens in at least 9 of every 10 runs. Refuted if fewer. If it holds, work that shortens context or cuts turns is where savings are, and message compression is not.
- **P3. Defined terms stop being argued.** A repeat finding is a blocking finding raised again in a later round of the same review about the same criterion. Repeat findings about a term the vocabulary defines occur in at most 1 review in 10. Refuted if more.
- **P4. Thin reviews miss more.** A thin review opened nothing beyond the diff. Among runs that pass review and later have a defect traced to them, thin reviews are over-represented relative to their share of all passing runs. Refuted if they are not. This is first testable once at least 5 post-release defects are traced.

### XE-013 — A reviewer is reached over a transport, and its identity stays the model's

**Status:** done. Merged to `main` in `e28909b` (PR #38, head `008099a`) on 22 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction. Review `20260922-105812-008099a-vs3gs2t4` (openrouter-gemini/google/gemini-3.1-pro-preview, `no_blocking_findings`, 20/20 acceptance across XE-013 and CI-002, run as a recorded fallback with no cross-family corroboration).

**No release record.** `peer_review.py release` was never run for that review, and its packet names the cloud container's checkout, so `record-release` cannot resolve it from the device. None was fabricated; see `Taskade/Team Plugins/00 – Project Hub/note-2026-09-22-pr38-no-release-record.md`.

**Links introduced:** the round record gains a transport name and a provider model id. The model id resolves at the provider, not in this repository, so a model the provider retires leaves a record naming something that no longer resolves. The record keeps the model family alongside it, which does not go stale, and a reader checking what independence was obtained reads that rather than the id.

XE-005 made independence a property rather than a name and built the table for it. The dispatch path did not follow: `run_reviewer` is still an if/elif chain, one branch per CLI, each doing `shutil.which` then `subprocess.run`. So "adding a reviewer is a table entry, not a change to the dispatch path" is true of the table and false of the code, and three consequences are already live. A missing binary reports `review_unavailable`, which is why every review on 21 September ran Gemini as a recorded fallback with no cross-family corroboration. All three entries carry `max_output_flag: None`, so the per-entry headroom criterion 6 requires is declared and never enforced, and the code says so in its own comment. And usage is scraped per CLI, a regex on Codex's "tokens used" line and a dig into Gemini's `stats.models`.

OpenRouter is a transport, not a reviewer. Adding it as a single entry named for itself would re-encode at larger scale the error XE-005 removed, because one name would span every model family at once.

1. Entries separate **transport**, how the reviewer is invoked, from **identity**, its `model` and `model_family`. A reviewer sharing an existing transport is a table entry with no new dispatch branch.
2. An `openrouter` transport is added with one entry per model family it serves. A single entry named for the transport is refused at the table rather than at run time: the transport spans every family, and a record naming it as the reviewer says nothing about independence.
3. The transport applies `max_output` on the request, and the round records the headroom as enforced rather than declared. This is the first entry for which XE-005 criterion 6 is true.
4. Token usage arrives in the provider's single shape and the round records that source, per XE-012 criterion 3. The per-CLI parsers stay for the CLIs and gain no new cases.
5. An API reviewer has no filesystem, so the review surface XE-007 builds is sent as content. Which parts of it are sent is declared in the entry and recorded in the round.
6. EV-008 is restated for a reviewer that cannot open files. `examined_beyond_the_diff` measures what a reviewer chose to read, and a reviewer that reads only what it was handed has made no choice. The record carries what was **sent**, under a separate field name that cannot be read as the CLI measurement, and the CLI measurement is left untouched. A constant reported as a choice is the false signal EV-001 forbids.
7. Preference order still prefers a reviewer that opens its own surface, because that measurement is worth keeping where it exists. OpenRouter enters as a fallback: it runs when no independent CLI is installed, and the record says it was a fallback, per XE-005 criterion 4.
8. The credential is read from `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/openrouter.env` (variable `OPENROUTER_API_KEY`, DR-010), never from an argument or the repository. A missing credential reports `review_unavailable` naming the file it looked for.
9. Model floors apply per entry as they do now. An entry below its floor is refused before it runs.
10. Tests: a same-family entry refused before dispatch; headroom applied and recorded as enforced; a truncated response reporting `output_truncated` distinct from `malformed_output`; a missing credential reporting `review_unavailable` with the path; the fallback path recording `reviewer_is_fallback: true` and the family that ran; and one live round against a real OpenRouter model, recorded.

### XE-014 — A scorer that cannot start is a gate that is not there

**Status:** planned.

**Links introduced:** none. The coverage record gains a `credential_source` field naming where the key resolved from, which is a label for a later reader rather than a link that has to re-resolve.

XE-010 shipped on 2026-09-18 and has gated nothing since. Two defects are stacked, and the second one hides behind the first.

`packet_coverage.mjs` imports `ai`, and no `package.json` exists anywhere in this repository. The script exits 1 at `ERR_MODULE_NOT_FOUND` before `main()` runs, so it writes no `coverage` key at all. `tests.yml` is `setup-python` only, with no `setup-node`, no install step and no invocation of the scorer, so CI has never run it either. `test_packet_coverage.py` exercises `coverage_verdict` alone, over hand-built dicts. The suite is green over a producer that has never executed once. That is XE-010 criterion 6 one level up: that criterion made the extractor prove its own coverage, and nothing made the scorer prove it can run.

Behind it, the credential is unreachable by a second route. Measured on the Release Owner's Mac on 2026-09-22: `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/aigateway.env` holds a working 60-character `vck_` key that returns HTTP 200 from `typesafe-ai/jev` through the gateway in 135ms and separates a covered criterion at 0.90 from an absurd one at 0.05. Nothing exports it. Not `.zshrc`, not `.zprofile`, not `.profile`, and a fresh login shell has `AI_GATEWAY_API_KEY`, `GSTACK_OPENROUTER_ENV` and `GSTACK_AGENT_APP_ENV` all unset. DR-010 decided this class on 2026-05-18 and chose the vault file with a resolution chain. XE-013.8 narrowed it for this plugin to one home named by an environment variable. Neither reached this script, which consults the bare variable and nothing else.

What is not wrong, and was claimed as wrong in this item's first draft: there is no silent false pass. `coverage_verdict` returns `not_run` for an absent report and the review state records `coverage_checked: false`, which is XE-010 criterion 5 working exactly as written. The gate is absent and the record says so. What failed is that nothing surfaces the saying, so four days and three merges passed with an honest record nobody read.

1. The scorer's dependency is declared where a reader and an installer can both find it. A `package.json` names `ai` at the floor the README already states, with a lockfile. An import that resolves on one machine and nowhere else is not a dependency, it is a local accident.
2. Something installs it before the scorer runs, and the workflow that runs this repository's checks either is that something or explicitly is not. A gate whose producer no runner installs is a gate that exists only in review.
3. The credential is resolved from a file, as `peer_review.py` and `agent_token.py` do, and is placed into `process.env.AI_GATEWAY_API_KEY` rather than passed as an argument, because the AI SDK reads the variable itself and the script's `key` is only a guard. `GSTACK_AIGATEWAY_ENV` names the file. A set `AI_GATEWAY_API_KEY` still wins, so this is additive, per DR-010's own precedent.
4. When neither is set, the native macOS Google Drive vault path DR-010 specifies is tried. gstack runs from a Mac shell, and a convention satisfied only by an export nobody has made is the state this item exists to leave behind.
5. Four outcomes, distinguishable in the packet, where today there are two the script can reach and one it cannot. `checked` carries the scores. `unavailable` means no credential is configured on any path, stays non-blocking and exits 0, preserving XE-010 criterion 5 exactly. `unusable` means a credential is configured and does not work. `broken` means the scorer could not start at all, which is the state every run has been in and the one no status existed for.
6. A `coverage_checked: false` state is surfaced where the Release Owner decides, not only recorded in the state file. The record was correct for four days across three merges and nobody read it, which is the failure this item is actually repairing.
7. Every non-`checked` record names what was consulted: the variables read and the paths tried, in order, the way `openrouter_key()`'s refusal names its file.
8. The reader handles a final line with no terminating newline. `aigateway.env` has none, so `wc -l` reports 0 and a POSIX `while IFS= read -r` loop reads zero lines from a 79-byte file that plainly contains the key. A loader that mistakes that file for an empty one reproduces this defect under a new name.
9. The tree is clean when this lands, per DR-102. `aigateway.env` gets its trailing newline, and the item ships with one real `checked` coverage record produced against an actual packet and this DESIGN.md, so the fix arrives with evidence rather than with a claim that it would work.
10. Tests: at least one test EXECUTES `packet_coverage.mjs` as a subprocess rather than testing `coverage_verdict` alone, because a suite green over a producer that has never run is the defect and not the coverage of it; a missing `ai` package records `broken` and exits non-zero; no credential on any path records `unavailable` and exits 0, which is criterion 5 as a test; a `GSTACK_AIGATEWAY_ENV` naming a nonexistent path records `unusable`; a file setting no key records `unusable`; a file whose only line lacks a trailing newline yields the key, against a fixture byte-identical to the real one; a set `AI_GATEWAY_API_KEY` beats a file setting a different value; and every non-`checked` record is asserted to name at least one consulted path.

### XE-015 — A reviewer told it has no shell opens nothing, and still answers in schema

**Status:** done. Merged to `main` in `ee9800e` (PR #42, head `5cd483f`) on 22 September 2026 by `moxywolf-agent[bot]`, without cross-tool review at that head. Reviewed retroactively on 25 September at exactly that head: review `20260925-084236-5cd483f-frmnwj29` (codex/gpt-6-astra, `no_blocking_findings`, 6/6), CI run 35796467639 read by the dispatcher. No release record exists: `record-release` refuses a merge that predates its review, and Dorian ruled the item done with this note.

**Links introduced:** none. The round record's `examined` block already carries `read_tracking`, `examined_count` and `offered_count`; this item reads them instead of adding a field.

`review_prompt()` tells every reviewer "No commands can be run here. Every reviewer runs in its tool's read-only mode, which withholds shell execution." For the Claude transport that is true enough, because it is handed Read, Grep and Glob as tools. For the Codex transport it is false, and the falsehood is load-bearing: `codex exec --sandbox read-only` withholds writes, not shell, and the shell is the only way `codex exec` opens a file. Measured on the Release Owner's Mac on 2026-09-22 at codex-cli 0.154.0, with exactly the flags `run_reviewer` passes plus `--output-schema` and `--output-last-message`, codex ran `/bin/zsh -lc 'cat probe.txt'` and returned the file's contents. Told by the prompt that it could not, it did not try.

The consequence is recorded in review `20260922-152749-f66c764-h4odx948` against `MoxyWolfLLC/crm`: `examined_count` 0 of `offered_count` 11, every acceptance criterion `met: false`, and evidence on each reading "could not be read with the available tools". That round was refused, but only because its verdict happened to disagree with its finding severities. A reviewer that had answered `no_blocking_findings` with an empty findings array would have been recorded as a clean cross-tool review having opened nothing, and the loop would have handed it to a Release Owner as verified. That is EV-001 inside the reviewer path. `examined_nothing` already exists in the vocabulary under `verify_outcome` and is already applied to the verifier; nothing applied it to the reviewer.

After the prompt was corrected on the Release Owner's machine, the same packet at the same head produced `examined_count` 8 of 11, three caller files read beyond the diff, and one real `follow_up` finding the builder had missed: a user-facing notice still describing the ordering the change had just replaced.

1. The paragraph says that read-only withholds writes rather than reading; that a reviewer may open the files in the surface and, where its tool provides a shell, may run read-only commands such as `cat`, `grep`, `ls` and `find` against the surface directory; that for some reviewers the shell is the only way to open a file, so read-only mode is not a reason to conclude it cannot read; and that writing, deploying, and running the project's build or tests remain forbidden. The existing sentences about `tests.commands` being a record rather than an instruction, and about `separate` for a judgement that needs execution, are kept.
2. A round whose `examined` block reports `read_tracking` `available`, `offered_count` greater than 0 and `examined_count` 0 raises `examined_nothing` before `validate()` runs, so the outcome names what went wrong rather than depending on the verdict and the severities disagreeing. The raw reviewer output is recorded on the round before the refusal, so the record shows what was said as well as that nothing was read.
3. The refusal does not fire where reading cannot be measured. The `api` transports already record `read_tracking: not_applicable` and are untouched. The selftest's fake reviewer is exempt on its own ground, stated in the record: atime has one-second resolution and a selftest round completes in milliseconds, so an empty examined list there means not measurable rather than not examined, which is the distinction `examined_report` already draws for a noatime mount. The existing selftest assertions keep their outcomes.
4. A test executes the guard rather than only asserting over hand-built dicts. `test_examined_guard.py` drives a real `cmd_round` whose reviewer returns a verdict that validates cleanly, and asserts the outcome is `examined_nothing`, that the error names the count, and that the raw reviewer output is still recorded. It reaches that path by replacing `run_reviewer` rather than by using the `_SELFTEST` fake hook, because that hook is exempt under criterion 3 and exempting the thing under test is how a guard passes without guarding. The predicate is also tested in isolation across the measured, unmeasurable, no-filesystem and nothing-offered shapes. A test that checked only the condition would repeat XE-014 criterion 10's defect at a smaller scale.
5. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.31.0, per CI-002.
6. `peer_review.py --selftest` passes, and `scripts/run_all_tests.py` reports the suites it examined by name with a nonzero count.

### XE-016 — Counting what a review cost never costs the review

**Status:** done. Merged to `main` in `ecd461f` (PR #47, head `4ebde4e`) on 23 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260923-093946-4ebde4e-x_j2eigq` (codex/gpt-6-astra, `no_blocking_findings`, 5/5 acceptance, 32 of 34 surface files examined), with the `tests` workflow green on the same head.

**Links introduced:** none. The round record's `reviewer_usage` field already exists (XE-012); this item changes how it is parsed, not what it holds.

Round 2 of DS-001's review (`20260923-090656-95ef88a-xatof78b`) crashed after codex had finished and been paid for. `reviewer_usage()` looks for codex's `tokens used` line with `tokens used\W*([\d,]+)`, and `[\d,]+` accepts a string of commas alone. Codex printed something that matched that way, `int(",")` raised `ValueError`, and the exception escaped `run_reviewer` before the verdict was parsed or saved. The review state stayed at one round used, so nothing was corrupted, but the round was lost. Usage is bookkeeping. A defect in bookkeeping must not be able to throw away the thing it was counting.

1. The codex pattern requires a digit before any comma: `tokens used\W*(\d[\d,]*)`. A match with no digits is no match.
2. `run_reviewer` treats any exception from `reviewer_usage()` as `"not_reported"`, the value XE-012 already defines for usage a CLI did not report, and the round continues to parse and save its verdict.
3. Tests: `reviewer_usage("codex", "", "tokens used: ,")` returns `"not_reported"`; the existing `tokens used\n1,234` case still returns 1234; and a round driven through `cmd_round` with a reviewer whose usage parse raises still records its verdict with `reviewer_usage` set to `"not_reported"`.
4. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.32.0, and the top-level marketplace version moves, per CI-002.
5. `peer_review.py --selftest` passes, and `scripts/run_all_tests.py` reports what it examined with a nonzero count.

### XE-017 — A finding about a file the reviewer was never shown is not checked, and says so

**Status:** done. Merged to `main` in `f82f4e2` (PR #49, head `67db337`) on 23 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Reviews: `20260923-100054-6f9e6f9-vxfm8nrq` (two blockers, F1 record failures hidden behind unverifiable and F2 older records skipping the per-file report, both fixed; ended `malformed_output` on a verdict over separate findings only), `20260923-100641-877ad1b-hcoyl11f` (`no_blocking_findings`, 6/6), and after the rebase onto DS-001 `20260923-101449-67db337-zs9d1axd` (`no_blocking_findings`, 6/6, 31 of 34 files examined), with the `tests` workflow green on the merged head.

**Links introduced:** none. The check reads the existing `severity`, `file` and `line` of each finding and the existing subject record; it adds no field.

`build_prompt()` tells the reviewer that when a judgement needs a file the surface does not carry, it reports "a finding with severity `separate` naming the file". Reviewers do exactly that, at line 0, because there is no line to name. `verify_links()` then treats the finding as a location to re-resolve: a line-0 finding against a file that exists at the head fails `line_exists` and is counted as a `link` failure, and `release` refuses the whole review as `stale_link`. DS-001's review `20260923-095118-c5b5358-7kb81jmu` reached `fixes_verified` and was refused this way, on five such findings. The contract asked for the finding, and the verifier punished the review for having it.

1. In `verify_links()`, a finding with severity `separate` and line 0 is recorded as `unverifiable`, with a detail saying it names a file the review surface did not carry and was not checked. It is not a `link` failure. This is decided before the `bound` and `line_exists` checks, so it holds for records written before this change, and for paths inside and outside the packet repositories alike.
2. Every other finding is judged as before. A `blocking` or `follow_up` finding at line 0, or a `separate` finding at a real line, still has to re-resolve.
3. A review whose only broken checks are these reports `links_unverifiable`, which `release` already accepts, and the release record carries that outcome and the count, so the handoff says what was not checked.
4. Tests in `test_evidence_links.py`: a round with a `separate` line-0 finding against an existing file reports `links_unverifiable`, not `stale_link`, and its check detail names the file as not carried; the same finding marked `blocking` still reports `stale_link`; and `cmd_release` on a passing review carrying such a finding reaches `awaiting_human_release`.
5. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.33.0, and the top-level marketplace version moves, per CI-002.
6. `peer_review.py --selftest` passes, and `scripts/run_all_tests.py` reports what it examined with a nonzero count.

## Fifth objective: session memory

Premise: a session's context window should be filled from the sources that hold state, not from a prose copy of them, and what a session learns should go back as pointers those sources can check. Today it runs the other way. `/session-start` reads a handoff that restates state in prose, and `/session-end` writes one. On 2026-09-19 the handoff said PR #10 was open and EV-006 through EV-008 were unstarted. `git log origin/main` said all of it had merged two days earlier. The session spent its first calls and its first premise on the copy. That's XE-008's two-homes defect at the scale of a whole session.

The objective borrows a three-layer model: the context window is text, the knowledge graph holds the entities and the links between them, and the ontology says what those links mean. The arrows between the layers are where the value is and where the drift starts. This objective builds all four in `project-init`, and it measures them the way XE-011 does, because structure has to earn its keep.

What the board looked like when this was written, counted through the Atlassian connector on 2026-09-19: MOXY holds 129 issues. 102 carry no label at all, and 50 of those are open. Of the 27 labeled, 4 carry the bare `moxywolf-plugins` and 23 carry `project-moxywolf-crm`. So two label conventions are live on one board, and the rule `project-init` ships, "a `#project/<slug>` maps to `project-<slug>`", is right for one project and wrong for the other. That rule has seven homes, listed in SM-002. The Team Plugins instructions override it in prose. The connector itself works: `labels = moxywolf-plugins` returns 4 (1 Done, 3 To Do), and `labels = project-moxywolf-plugins` returns 0 with no error, which is the failure mode.

### SM-001 — Session start and end run on the graph, not on a copy of it

**Status:** planned.

**Links introduced:** the handoff-ref-to-subject link. A handoff names a commit, a pull request, a design item, a review ID or a Jira key, and the next session assumes it still means what it meant. Every ref is re-resolved at the next session start. The source-precedence link: where a source and the handoff disagree, the briefing assumes the source is right. Criterion 4 makes that visible every time rather than silent.

**Arrow 1, graph into context: the briefing is assembled from sources.**

1. `/session-start` builds its "Where things stand" section from sources at read time: `git log origin/main` and open pull requests for each declared repo, `**Status:**` lines in each declared repo's `DESIGN.md`, and the MOXY board. It reads no status from the handoff.
2. Moved to SM-002 on 2026-09-19, so the label fix can ship and be reviewed on its own.
3. The briefing prints a coverage line naming each source it examined and how many records each returned. For the board, it prints the label it queried, the count, and the count of open issues on MOXY that carry no label at all, since any project's work could be among them and none of it can be shown. A source it could not reach is shown as `SKIP` with the reason, never as an empty result, per EV-001. Zero records from a reachable source is printed as zero records, not as "nothing open".
4. When the handoff asserts a state a source contradicts, the briefing shows both values and the source, and says the source wins. Fixture test: a handoff whose open work names PR #10 against a git fixture where PR #10 is merged produces a `resolved_since_handoff` line naming both, and PR #10 is not listed as open.
5. The handoff contributes only what no source holds: intent and priority order, decisions not yet recorded as DRs, production-data state no repo carries (the row counts "What landed" is written to hold), procedural reminders, and the suggested opening line. The briefing labels those as carried from the handoff, with its date.
6. A handoff with no `refs:` block, which is every handoff written before this item, is read as prose only, and the briefing says so in one line rather than failing.

**Arrow 2, context into graph: session end writes pointers, not prose state.**

7. `/session-end` writes a `refs:` block in the handoff frontmatter. Each entry is a typed pointer: `{kind, id, repo, relation}`, for example `{kind: commit, id: 7b72605, repo: moxywolf-plugins, relation: merged}`. For each declared repo it also records the branch and `git rev-parse HEAD` at write time, because a second session can commit into the same checkout (team-shared rule, 2026-09-18).
8. "Commit & push state" is rendered from the `refs:` block, not written beside it. "What landed" stays a prose paragraph, because it carries production-data state no repo holds, but every commit, PR, item or Jira key it names also appears in `refs:`. Each open-work item that names a PR, item or Jira key carries a ref, so criterion 4 can check it next time.
9. The suggested opening line names refs, not their status. It says "PR #10", not "PR #10 is waiting on review", because the status is the part that goes stale.
10. Every ref is resolved at write time: commits with `git cat-file -e` against the remote-tracking ref, pull requests and review IDs as EV-007 criterion 3 already resolves them, Jira keys through the connector. An unresolvable ref is written with `resolved: false` and its reason. The write reports how many refs it resolved. A handoff that states work landed and carries zero refs fails, per EV-001.
11. `/session-start` re-resolves every ref from the previous handoff and reports any that no longer resolves as `stale_ref`. That's a report, not a failure. A branch deleted after merge is ordinary, but a reader has to see it.
12. The frontmatter writer and the `/session-start` parser land in one change, with a round-trip test: a handoff written by `/session-end` parses in `/session-start` to the same refs. This is XE-008 criterion 2, and the session-end skill already warns that deviating from its section names breaks the parse.
13. `session_ended` takes its UTC offset from the clock at write time. The template hardcodes `-08:00`, which is wrong for half the year.

**Arrow 3, ontology into graph: relations are typed.**

14. The `relation` and `kind` values in `refs:`, and the item statuses arrow 1 reads, are XE-011 vocabulary ids. `/session-start` shows an unknown value verbatim and marked `untyped` rather than interpreting it.
15. graphify is out of scope here. Its model-extracted relation labels are the untyped-graph case this arrow names, and typing them is a separate item for the graphify plugin, raised only if this one pays.

**Arrow 4, graph into ontology: new terms are proposed, never promoted by the agent.**

16. A status spelling, relation or kind that arrow 1 or arrow 2 meets outside the vocabulary is appended to a candidates file beside `vocabulary.json`, with the value, where it was seen, and a count. The candidates file is the only thing this arrow writes.
17. Promotion into `vocabulary.json` is an amendment to this document, approved by a named human. A test asserts that no code path in `project-init` or `gstack-execution` writes to `vocabulary.json`. This follows the team's HITL rule: the machine surfaces and recommends, and the human decides.

**Dependencies and the decision rule.**

18. Arrows 1 and 2 need no vocabulary and ship on their own. Arrows 3 and 4 depend on XE-011. If XE-011's decision rule freezes the vocabulary, criteria 14, 16 and 17 are dropped and recorded as dropped, not left planned.
19. Baseline before arrow 1 lands and the same measurement after: at least five `/session-start` runs on this project. Per run, record input and output tokens, tool calls, and whether the briefing's open-work list matched the sources, as judged by the named human. Report cost per correct briefing before and after, and include the tokens spent writing handoffs at session end, since arrow 2 moves cost there. If cost per correct briefing does not fall, arrows 1 and 2 are reported as not earning their keep, and the handoff format reverts to the one before this item. SM-002 is kept either way, because it's a correctness fix, not an economy one. A win is never claimed from a single run.
20. `project-init` and `team-kanban` each get a minor version bump, and each `plugin.json` changelog states which arrows shipped and which were dropped.

### SM-002 — The board label is declared, never derived

**Status:** review. Merged as `c20699a` (PR #24) on 2026-09-20 with XE-011 as one checkpoint. All seven homes of the derived-label mapping are removed and `test_no_derived_label.py` keeps them out. The review state of that merge is not recorded in this document and was not established when this status was written.

**Links introduced:** the declared-label link. A project's instructions name its exact Jira label, and every board query and every issue write assumes that label is the one the board uses. Criterion 5 makes a wrong one visible in every briefing.

Split out of SM-001 on 2026-09-19. The rule "a `#project/<slug>` maps to the label `project-<slug>`" is right for `moxywolf-crm` and wrong for `moxywolf-plugins`, and it lives in seven places, not the three SM-001 first named.

1. A project's instructions carry a `Jira label(s):` value beside the `#project/` tag: the exact label or labels as they appear on MOXY, or `none`. `/session-start` queries MOXY with those labels as written.
2. No skill, command or reference derives a label from a slug. The derivation is removed from all seven homes. In the repo: `project-init/skills/session-start/SKILL.md`, `project-init/commands/session-start.md`, `project-init/skills/project-init/SKILL.md`, `project-init/commands/init-project.md` and `team-kanban/skills/team-kanban/references/jira-board-mapping.md`. In the vault: `_Shared Knowledge/Agents and Plugins/project-instructions-loader-stub.md` and `_Templates/Cowork Project Instructions Template.md`. `plugin.json` changelogs are exempt, because they record what was.
3. A test in the repo asserts that none of the five repo files states the mapping, and it reports how many files it examined; zero examined is a failure, per EV-001. The vault has no CI, so the same check is run by hand against the two vault files and its output goes into the review packet.
4. Instructions with a `#project/` tag and no `Jira label(s):` value, or with no field at all, get no board query. The briefing says in one line which field is missing. Nothing is inferred from the project name or the repo names.
5. The briefing prints the label it queried and how many issues came back, so a label that matches nothing reads as a wrong label rather than an empty backlog.
6. `/init-project` asks for the label exactly as it appears on MOXY and confirms it back verbatim.
7. team-kanban writes a project's issues with that project's declared label, never a derived one.
8. `project-init` and `team-kanban` each get a minor version bump with a changelog line.

### SM-003 — A session's mistakes become checks or rules, and a repeat escalates

**Status:** done. Merged to `main` in `c4643d7` (PR #54, head `08c2807`) on 24 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260924-210422-ec3b581-wnlj4d2k` (codex/gpt-6-astra): round 1 found the zero-mistake path could not finish; round 2 found the fix skipped criterion 8's ledger creation; round 3 `fixes_verified`, 12/12, with the `tests` workflow green at the reviewed head and read by the dispatcher. The review before it (`20260924-205455-da5bfac-60y_oekp`) raised three blockers, all fixed and verified: rows written before validation, rows after a blank line never examined, and a same-target repeat refusal weaker than criterion 5. Not yet exercised in a real `/session-end`.

**Links introduced:** the mistake-to-remedy link. Each ledger entry names the check, rule or item it became, by repository path or item ID, and a later session assumes that target still exists and still covers the mistake. The repeat link: an entry may name an earlier entry it repeats, and the ledger assumes that earlier entry's remedy did not work.

A lesson written down is not a lesson applied. On 2026-09-24 the macOS `/tmp` vs `/private/tmp` resolution was already recorded twice, in the peer-review project memory and in PR #42, and the session had read that memory at start. It still named `/tmp/xe019` in a review packet, and review `20260924-162903-25a6677-7hrcgdnp` spent a Codex round on it. A journal read once at session start is not in front of the agent at the moment of action. A check is, and so is a rule in the skill that runs at that moment. The same session made two more mistakes worth keeping, and something other than the agent caught two of the three: the Codex review found both the packet path and a plaintext key the secret scan missed. A session reviewing itself from recall under-reports, so the step reads evidence first.

1. `/session-end` gains a step before the handoff is composed that gathers mistakes from evidence, not recall: review rounds opened this session whose outcome was not `no_blocking_findings` or `fixes_verified`, or which carried findings; test or CI runs this session that failed; and turns in the conversation where the user corrected the agent. It prints a coverage line naming each source it examined and how many records each returned. A source it could not reach is `SKIP` with the reason, per EV-001, and zero mistakes from examined sources is printed as zero, not omitted.
2. Each mistake is one entry: what happened in a sentence, `caught_by` (one of `user`, `reviewer`, `test`, `ci`, `self`), and an evidence ref (review ID, run ID, or the date and a short quote of the correction).
3. Each entry takes exactly one `disposition`. `became_check` names the test or check that now fails on a recurrence, by path, or the planned design item that will build it. `became_rule` names the file the rule was written into, and that file must be one loaded at the point of action (a skill, a command, a reference it cites, or the shared team rules), never the handoff or a session-start-only memory file. `one_off` is recorded in the handoff only.
4. Before writing a `became_rule`, the step searches the target file, the project's memory files and the shared team rules for an existing rule on the same point. A match is updated in place and the entry names it, rather than adding a near-duplicate.
5. An entry may declare `repeats: <earlier entry id>`. A repeat cannot be `one_off`, and it cannot be `became_rule` naming the same target the earlier entry named: a rule that did not prevent the recurrence is escalated to a check, or to a different point of action, and the entry says which.
6. Entries are appended to `MoxyWolf Vault/Projects/<project>/11-Knowledge/mistake-ledger.md`, one table row each with an ID, the date and the fields above. The handoff carries a "Mistakes this session" section listing the entry IDs and dispositions, not a restatement.
7. `caught_by` and `disposition` are vocabulary groups in `vocabulary.json`, promoted by this amendment under SM-001 criterion 17. Values outside them are refused by the ledger check, not interpreted.
8. `project-init/scripts/mistake_ledger.py` (stdlib) validates the ledger and is run by the step before it writes: every row has the required fields, IDs are unique, a `repeats` target exists, and criterion 5's two refusals hold. It reports how many rows it examined, and a ledger with no rows FAILS rather than passing. A project with no ledger file yet gets one created by the step, never a pass over nothing.
9. Tests in `project-init/tests/test_mistake_ledger.py`: a valid ledger passes; a missing field, an unknown `caught_by`, an unknown `disposition` and a duplicate ID each fail by name; a repeat marked `one_off` fails; a repeat marked `became_rule` with the same target as the entry it repeats fails; the same repeat with a different target passes; and an empty ledger fails.
10. The ledger is seeded with the three mistakes from 2026-09-24, each dispositioned: the `ci_runs` packet path (`became_check`, naming XE-020), the date-based staleness call on `CHARTER.md` (`became_rule`, into the repo analyzer's technical-debt step: count references before calling a document stale), and the missed `ak_` key format (`became_rule`, into the repo analyzer's security-posture step: vendor key prefixes).
11. `project-init` moves from 0.30.1 and the top-level marketplace version moves, per CI-002. The analyzer rule edits in criterion 10 move `github-repo-analyzer` too.
12. `scripts/run_all_tests.py` reports what it examined with a nonzero count and no failures.

## Sixth objective: trust boundaries

Opened 2026-09-20. The fourth objective asks what the loop's memory costs. This one asks where its records come from.

The premise: **a record the loop reads as settled is a record nobody re-derives, and that is the property worth attacking.** EV-001 made a check say what it examined. Nothing makes a record say where it came from.

gstack's own writes are narrow: its gates produce them from repository artifacts, they land through a pull request, and they live in git, where a write nobody asked for appears in a diff. The wider exposure is elsewhere in this marketplace. `obsidian-update`'s memory extraction and `vault-skills`' capture write durable notes that later sessions read as established. `research-pipeline` ingests web sources into a library with no inclusion rubric. `synergy-engine` scores text scraped from LinkedIn. `document-analysis` converts documents other people wrote. Each of those turns outside text into a record, and none of them records that it did.

Scope is the write path, not the model. These items don't claim to make a prompt injection-proof.

### TB-001 — Every record says where it came from

**Status:** building. Criteria 1 to 5 are built in this change; criterion 6 follows when the weekly report scores P5 from the origin field.

**Links introduced:** the record-to-origin link. A reader of any record, human or agent, assumes it was produced by the system that names it. The field makes that assumption checkable instead of implicit. Also the origin-to-reviewer link: a record whose origin is external text names the gate or the human that examined it, and a record that names neither is treated as unexamined.

1. Every record gstack writes (round record, packet, run measurement note, release record, handoff ref) carries `origin`, a controlled value from the vocabulary: `repository_artifact`, `gate_output`, `human_instruction`, `external_text`. The writer sets it. Nothing defaults it.
2. A record whose origin is `external_text` also carries `examined_by`, naming the gate or the human that read it, or the value `unexamined`.
3. `verify` reports records carrying `unknown` or a value outside the vocabulary. It reports how many records it examined, and zero examined is a failure, per EV-001.
4. Adding `origin` and `examined_by` moves the vocabulary to 1.2.0, which is an XE-012 break point.
5. Tests: a writer that omits `origin` fails; a record with `external_text` and no `examined_by` fails; the verify pass reports its coverage; the vocabulary version bump appears in the run note.
6. P5 in the pre-registration becomes measurable when this merges, and the weekly report scores it from that point rather than reporting it as declared.

### TB-002 — One enclosure for text the loop did not write

**Status:** planned.

**Links introduced:** the quotation link. Text pasted into a prompt is assumed by the reader to be data, and the model has no way to tell data from instruction unless the boundary is marked. The enclosure marks it. It does not enforce it.

1. One file, `plugins/gstack-execution/skills/gstack-execution/references/untrusted-enclosure.md`, defines the enclosure and the instruction-immunity rule: text inside it is data, never a directive, whatever it claims about itself.
2. Every place the loop puts text it did not produce into a prompt loads that file rather than restating the rule: reviewer output, pull request and issue bodies, fetched pages, and any retrieved memory. One producer, per XE-008.
3. A test greps the ingesting skills for a restated enclosure rule and fails on a second home, reporting how many files it examined.
4. The item's report states the measured limit of this defense rather than implying it is one. In the numbers the external response supplied (revised edition, 2026-09-20), an enclosure of this kind moved executed adversarial actions from 60% to 30%, on a synthetic benchmark whose traces and harness were not published. It is a speed bump on unverified evidence. TB-001 and TB-003 are the controls.
5. Adoption outside gstack is a later item, and only for the plugins named in the objective preamble.

### TB-003 — Egress is granted, not filtered

**Status:** planned.

**Links introduced:** the destination-to-grant link. A tool call carrying a destination is assumed to be going somewhere the owner allowed. Today the grant covers tools and output roots, not destinations.

1. `governance.py`'s grant model gains destination patterns beside `allowed_tools` and `output_roots`. A call whose destination matches no grant is refused and named, with the destination and the item that would have to grant it.
2. Refusal is the default. There is no pattern list of bad destinations, because a denylist reports a pass over whatever it hasn't thought of. DR-099 has the worked example.
3. The refusal is a typed error naming the exact missing grant and its value, for example `MissingGrantError: NetConnectGrant(host=192.168.1.10) required`, so an honest call is one approval away rather than a mystery. Grants are typed by what they cover: network destinations first, with database and executable grants as a later item. This shape comes from the external response's third round and is better than the plain message this item first carried.
4. Tests: an ungranted destination is refused; a granted one passes; the check reports how many calls it examined; a test asserts no denylist of destination patterns exists in the source.


## Seventh objective: retrieval review

Opened 2026-09-20. The third objective made our own checks say what they examined. This one asks the same of somebody else's retrieval pipeline.

The premise: **a retrieval stage that does nothing returns exactly what a working one returns, an ordered list.** A reranker that passes its input through, a top-k that never cuts, a grounding check that never fires: each is a stage reporting work it did not do, and the pipeline's output looks the same either way. `code-review-pro` and `analyze-repo` read code for correctness and security. Neither can tell whether a reranking step reorders anything.

### RR-001 — A retrieval stage proves it did its work

**Status:** done. Merged to `main` in `6c9912c` (PR #32, head `991dd34`) on 21 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded as `agent_merge_on_instruction`. Review `20260921-185258-991dd34-a61iuonn` (gemini/gemini-3.1-pro-preview, `no_blocking_findings`, 13/13 acceptance).

**Links introduced:** findings carry chunk and citation identifiers belonging to the *analyzed* repository, not this one. They are names, not handles: they re-resolve only against that repository at the commit examined, and each finding records that commit so a later reader cannot mistake a stale id for a live one.

1. The reviewer identifies the reranking stage and reports whether the post-rerank top result differs from the raw-similarity top result over a sample of queries. Where it cannot execute the pipeline, it reports the static finding (stage absent, output unused, score discarded) and says it did not execute, rather than a verdict it did not earn.
2. The reviewer names the line where top-k is cut before the model call, or reports that no cut exists.
3. The reviewer reports the absence of an explicit insufficient-grounding path as a finding, not a note. A pipeline that answers regardless of retrieval quality has no floor.
4. Where the pipeline emits citations, each is checked to resolve to a chunk that was in the context window, not merely in the corpus. Where the reviewer cannot execute the pipeline, it reports that it did not execute and returns a counted SKIP, rather than a verdict it did not earn. RR-002 provides the execution path.
5. Every check reports what it examined, per EV-001. A repository with no reranking stage returns SKIP for criterion 1, counted in the summary, never folded into a green line.
6. Tests: a fixture whose reranker returns input order unchanged is caught by 1; a fixture with no grounding fallback is caught by 3; a repository with no retrieval pipeline SKIPs every criterion and reports zero coverage rather than a pass.

### RR-002 — The probe runs the pipeline, or says it did not

**Status:** done. Merged to `main` in `6c9912c` (PR #32, head `991dd34`) on 21 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded as `agent_merge_on_instruction`. Review `20260921-185258-991dd34-a61iuonn` (gemini/gemini-3.1-pro-preview, `no_blocking_findings`, 13/13 acceptance).

**Links introduced:** the probe holds, for one run, the chunk identifiers captured at the model-call boundary and the citation identifiers captured at the answer boundary. Both belong to the executed repository and to that run only. They are compared and discarded; nothing is retained across runs, so a later reader cannot mistake a captured id for a durable handle.

1. Execution is opt-in and explicit. Absent a named entry point supplied by the operator, nothing is executed, and RR-001 criterion 4 stays a counted SKIP. The reviewer never decides on its own to run someone's code.
2. The probe captures the context window at the model-call boundary and the citations at the answer boundary, then asserts that every emitted citation identifies a chunk present in that captured context. A citation naming a corpus chunk that never entered the context is the finding.
3. It patches only those two boundaries. A probe that rewrites the pipeline is measuring itself.
4. It runs in a subprocess with no network granted by default. Egress is granted per TB-003, never filtered.
5. A run that captures zero context, or zero citations, is a FAIL naming the shortfall, never a pass. EV-001 governs the probe as it governs the static checks.
6. Tests: a fixture citing a chunk that was never in context is caught by 2; a fixture whose model boundary is never reached reports zero capture and fails by 5; a repository with no declared entry point executes nothing and returns SKIP.

## Eighth objective: the catalog imports

Opened 2026-09-21. The seventh objective reviews somebody else's retrieval pipeline. This one asks whether our own packages load.

The premise: **every check in this repository tests the scripts, and nothing tests the catalog they ship inside.** A skill whose frontmatter will not parse, or whose description the loader truncates, is broken at the only moment that matters, which is when somebody installs the plugin. The suites were green while ten of the 150 packages here were not loadable as written. An outside compatibility assessment found them. The gate did not, because the gate had never looked.

### CI-001 — A shipped package is one a loader can read

**Status:** done. Merged to `main` in `d619c06` (PR #33, head `69ab8e4`) on 21 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded as `agent_merge_on_instruction`. Review `20260921-134157-69ab8e4-oolg8b8m` (gemini/gemini-3.1-pro-preview, `no_blocking_findings`, 9/9 acceptance), with the `tests` workflow green on the same head.

**No release record.** `record-release` has recorded no release for this item, and none was fabricated to close the gap. The handoff step was skipped: the review landed, the checkpoint was presented for a decision in conversation rather than through `peer_review.py release`, and the merge followed. `record-release` refuses on that order twice over, first because no `release.json` exists for the revision and then because a handoff prepared now would postdate the merge. The review itself is intact and the merge is recorded on the pull request; what is missing is the artifact that binds the two, and it cannot be produced after the fact without lying about when it was made.

**Links introduced:** none. The check reads files already in the tree and names them by repository path, so there is nothing to re-resolve later.

1. Every `SKILL.md` in the repository is examined: the frontmatter block parses, `description` is present, it is not empty, and it is at most 1024 characters.
2. The check asserts what the compatibility assessment asserted, and nothing it did not. No judgement of wording, tone or usefulness. A check that grows opinions is a check people start overriding, and then the loadability finding goes out with the opinions.
3. It reports what it examined, per EV-001, and a run that finds no packages FAILS rather than reporting a clean catalog it never located.
4. It is stdlib-only, as the rest of this repository's checks are. The CI runner is a bare `setup-python` with no install step, so a check that needs PyYAML is a check that stops running the first time it matters. The frontmatter reader covers the subset this catalog uses and reports anything outside it as unreadable, which is the honest answer for a block a simple loader also could not read. Its agreement with PyYAML was measured over all 150 real packages, text and length, before and after the fixes: 150 of 150, including the two files PyYAML rejects.
5. The ten failures are fixed in the same change, because a check that lands red is a check somebody turns off. Where a description was shortened to fit the limit, its original text is preserved in the body under `## When this skill applies`, so no trigger wording is lost. Two of the ten were only malformed, never too long, and their text is unchanged.
6. Tests: a description over the limit, an empty one, an absent one, an unquoted colon in a plain scalar, and an unterminated block are each caught by a fixture; a description of exactly 1024 characters passes; and an empty tree FAILS rather than passing, which is criterion 3 as a test. The gate also runs the check over this repository's own 150 packages, not only over fixtures: a check whose only caller is its own selftest is a check nobody is running.

### CI-002 — A change ships to installs only if its version moves

**Status:** done. Merged to `main` in `e28909b` (PR #38, head `008099a`) on 22 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction. Review `20260922-105812-008099a-vs3gs2t4` (openrouter-gemini/google/gemini-3.1-pro-preview, `no_blocking_findings`, 20/20 acceptance across XE-013 and CI-002, run as a recorded fallback with no cross-family corroboration).

**No release record.** `peer_review.py release` was never run for that review, and its packet names the cloud container's checkout, so `record-release` cannot resolve it from the device. None was fabricated; see `Taskade/Team Plugins/00 – Project Hub/note-2026-09-22-pr38-no-release-record.md`.

**Links introduced:** none. The check resolves a diff range at run time, names plugins by their marketplace roster name and repository path, and retains nothing.

`github-repo-analyzer` shipped RR-001 and RR-002 in `6c9912c` and stayed on 0.11.0 for most of a day. The marketplace gates updates on a version, so nobody installed would have received any of it. It was found by hand. `test_manifest_consistency.py` cannot catch this class: it asserts `plugin.json` and `marketplace.json` agree, and they agreed perfectly at 0.11.0. DR-100.

The version has three homes, not two, and DR-013 (2026-06-14) says which one the client reads. A plugin's own `plugin.json`, its entry in `marketplace.json`, and the **top-level** `marketplace.json` version. The plugin manager gates "is there an update?" on the top-level one: bumping the first two leaves the client never re-pulling the marketplace, so it never sees them. Measured across this objective's own merges, the top-level moved 1.56.0 to 1.57.0 at `6c9912c` and then stayed at 1.57.0 through `d619c06`, `27fd672` and `94926c0`. One bump across four merges, so `github-repo-analyzer` 0.12.0, which was itself the fix for the 0.11.0 miss, has still not reached anyone.

1. For a given diff range, every plugin whose tracked files changed has a `version` in its `.claude-plugin/plugin.json` differing from its version at the base of that range. A plugin that did not change is not examined and is not required to move.
2. When any plugin changed in the range, the **top-level** `marketplace.json` version differs from its value at the base as well. Per-plugin alone passes a change no client can see, which is the failure this item exists to catch.
3. The roster is `marketplace.json`'s own entries, because that file is what the marketplace serves. A plugin directory absent from the roster is reported by name rather than silently skipped.
4. A plugin new within the range has no base version and is not required to bump.
5. It reports what it examined per EV-001: the range it resolved, the changed-file count, and every plugin it checked by name. A range it cannot resolve FAILS rather than reporting a clean tree it never diffed.
6. Stdlib only, per DR-101. git is invoked as a subprocess; the CI runner has it from `actions/checkout`.
7. The workflow gives the check the history it needs. `actions/checkout` at its default depth of 1 has no base commit, so this is a workflow change as well as a script.
8. The catalog is clean when the check lands, per DR-102. The top-level version is bumped in this same change, which is what finally ships 0.12.0.
9. Tests: a changed plugin at an unmoved version FAILS; the same plugin with a moved version passes; a changed plugin whose own version moved while the top-level did not FAILS, which is criterion 2 as a test; a new plugin passes; a range touching no plugin passes while reporting zero examined; an unresolvable base FAILS; and the check runs over this repository's real history: across `6c9912c`, where it must catch `gstack-execution` at an unmoved 0.27.0, and across `d619c06..2293ff6`, where six consecutive merges sit at an unmoved top-level version and it must fail the three of them that changed a plugin while passing the three that changed none.

## Ninth objective: design craft

Opened 2026-09-22. `saas-frontend-designer:baseline-ui` is the single home for design taste in this marketplace (fold-in plan, 2026-06-25). It carries impeccable's playbooks as of v3.8.0. Upstream is now v4.3.1 and has added playbooks we lack, next to a Rust engine we won't ship.

### DS-001 — Port impeccable v4.3.1's missing playbooks, without its engine

**Status:** done. Merged to `main` in `bc0b33e` (PR #46, head `aa4feea`) on 23 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260923-095118-c5b5358-7kb81jmu` (codex/gpt-6-astra): round 1 two blockers in `critique.md`, round 2 `fixes_verified`, 8/8 acceptance, with the `tests` workflow green on the same head. Five `separate` findings named files the review surface never carried (impeccable's originals, the untouched references, `commands/polish.md`); the release record carries them as `links_unverifiable`, not checked, per XE-017. Fidelity to upstream and the whole-skill link check rest on the builder's verbatim diff and sweep output in the review packet.

**Links introduced:** the NOTICE names the upstream source as impeccable v4.3.1 at commit `e0881d2`, which re-resolves by cloning that commit. `SKILL.md` names each new reference by relative path, which resolves inside the tree and is checked by criterion 3.

1. `skills/baseline-ui/reference/` gains `critique.md`, `clarify.md`, `onboard.md`, `animate.md` and `craft-floor.md`, taken from impeccable at `e0881d2`. Files with nothing to strip go in verbatim. Files that call the engine or link to references we don't carry are modified, and each modified file says so at its top (Apache-2.0 section 4(b)).
2. Every engine dependency is removed or re-expressed as something the agent does by hand: launcher calls, `detect`, `live-server`, `critique-storage`, and the editor-hook sentence in `craft-floor.md`. No step in a ported file needs a binary, a network download or a script.
3. A grep of `skills/baseline-ui/` finds no `scripts/impeccable`, no `skill-base-dir` and no `live-server`, and every relative `.md` link in the skill resolves to a file that exists. Run over the whole skill, not only the new files.
4. `SKILL.md` gains the four page modes (Persuade, Operate, Read, Experience), written in our words, and a table saying when to load each new reference. Its description stays within the CI-001 limit.
5. The ten references already vendored keep their content. The one exception is link repair: `craft.md` and `typeset.md` link to `adapt.md`, `codex.md` and `brand.md`, which were never vendored, and those four links are rewritten to point at material this skill carries. Both files are then marked modified, here and in the NOTICE. Refreshing the ten to v4.3.1 is a separate decision.
6. `NOTICE` and `README.md` name v4.3.1 at `e0881d2`, list each new file as verbatim or modified, and list what was not taken: the engine and its detector rules, live mode, `generate`, hooks, `doctor`, and `init` and `document`, because `DESIGN.md` belongs to `/gstack-design-doc`.
7. `saas-frontend-designer` moves 1.2.0 to 1.3.0 in `plugin.json` and its `marketplace.json` entry, and the top-level marketplace version moves too (CI-002). Versions change by surgical text replace, and the diff on both JSON files shows version lines only.
8. Tests: `run_all_tests.py` green on the branch, with the CI-001 packaging check and the CI-002 version check both reporting `saas-frontend-designer` among what they examined.

### XE-018 — A reviewer sees what the change names, and CI results the dispatcher fetched itself

**Status:** done. Merged to `main` in `b213899` (PR #50, head `53cb396`) on 24 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260924-145914-09e6ee3-gtge526o` (codex/gpt-6-astra): round 1 found three blockers (F1 single-component paths, F2 one page of jobs, F3 Step 5 folders), all fixed; round 2 `fixes_verified`, 10/10, with the `tests` workflow green at the reviewed head and read by the dispatcher itself. First use: SAMS PL-001 review `20260924-150655-40254e8-b7gynlsz` passed 4/4 after four earlier rounds could not.

**Links introduced:** `tests.ci_runs` in the packet names GitHub Actions runs by ID. The round record carries what the dispatcher fetched for each one, including the run's `head_sha`, and a run is evidence only for the head it ran at. A run ID that later points at nothing is reported as not read, never dropped.

PL-001 on `MoxyWolfLLC/SAMS` (PR #290) went through four codex reviews on 24 September 2026 and none could pass. Every round found no code defect. Every round marked a criterion that needs a command to succeed as not established, and said why. The surface carries the diff, the changed files, and files that name a changed file's stem in `.py`, `.sh` or `.yml`. It never carries a file the change itself names. `ci.yml` calls `scripts/local-supabase.ts` and the new test imports `./client`, and the reviewer was shown neither. The only execution evidence it had was the builder's own account in `tests.results`, which the contract tells it to treat as a claim. The green CI run at the reviewed head existed, and nothing put it in front of the reviewer in a form the builder could not have written. Round 3 accepted the type check on that account and round 4 refused the same words, so the outcome turned on the reviewer's reading rather than on evidence. Rounds 1, 2 and 4 then ended `malformed_output`, because a reviewer that cannot establish a criterion calls the verdict blocking with no blocking finding.

1. The surface gains `dependencies/`: tracked files, not changed and not already callers, that a changed file names by repository-relative path or imports by a relative specifier (`./x`, `../x`, resolved with the extensions `.ts`, `.tsx`, `.js`, `.mjs`, `.py`, `.json` and `/index.ts`), and files an acceptance criterion names by path. A criterion that names a directory brings that directory's `package.json` or `pyproject.toml`. The set is bounded by the same cap as callers and the withheld count is reported.
2. `SURFACE.md` lists the dependencies and says why each is there, and the round record's `surface` block counts them.
3. The packet may carry `tests.ci_runs`, a list of `{repo, run_id}` where `repo` is a packet repository path or directory name. For each, the dispatcher reads the GitHub Actions run and its jobs through `github_get` and writes `evidence/ci-<run_id>.json` into the surface with `origin` `gate_output`: the run URL, `head_sha`, the reviewed head, `head_matches`, the conclusion, and every job and step with its conclusion. The builder never writes this file.
4. A run whose `head_sha` is not the reviewed head is still written, with `head_matches: false`, and `SURFACE.md` says it is not evidence for this head. A run that cannot be read is written with `read: false` and the error, and the round continues. Neither is silently dropped.
5. The prompt tells the reviewer that `evidence/` was fetched by the dispatcher from the CI provider, not written by the builder, and that a step with conclusion `success` in a run whose `head_matches` is true is evidence that step ran and passed at the reviewed head.
6. The round record carries an `evidence` block: runs requested, runs read, and runs whose head matched.
7. Tests in `test_review_evidence.py` drive `build_surface` over a temporary repository: a changed file naming another by path, a relative import, and a criterion naming a file and a directory each bring the named file into `dependencies/`; the cap reports what it withheld; a CI run is written with `head_matches` true and false as the fake GitHub answers; and a run GitHub refuses is written with `read: false` without raising.
8. The peer-review contract's packet table and scope section, and `/gstack-build`'s Step 5, name `tests.ci_runs` and the two new surface folders, each in one place.
9. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.34.0, and the top-level marketplace version moves, per CI-002.
10. `peer_review.py --selftest` passes, and `scripts/run_all_tests.py` reports what it examined with a nonzero count.

### XE-019 — A test that fakes GitHub cannot reach the real one

**Status:** done. Merged to `main` in `fda18ed` (PR #52, head `247c448`) on 24 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260924-163849-247c448-m56xedwi` (codex/gpt-6-astra, `no_blocking_findings`, 4/4), with the `tests` workflow green at the reviewed head and read by the dispatcher itself. The review before it (`20260924-163251-860613c-9aou_1nn`, also clean) raised a separate finding: a plaintext Composio API key in the archived May handoff, public since `0bea07b`. It is redacted from the tree in `247c448`; it remains in history, so rotating the key is the fix, and that is Dorian's act.

**Links introduced:** none. The test drops two variables from the environment it hands its subprocess; nothing is named, cached or retained.

`test_governed_review.py` builds its subprocess environment from `os.environ` and fakes GitHub two ways: a `gh` stub on `PATH`, and a local HTTP server named by `GSTACK_GITHUB_API`. `github_get` takes the REST path whenever `GITHUB_TOKEN` is set, which is right in production, where `agent_token.py exec` supplies the app's token. But the test inherits the token from whatever shell runs it. In a Cowork cloud session, which exports one, nine cases skip the `gh` stub, call the live `api.github.com`, and fail `release_unavailable ... HTTP Error 403`. Measured on 24 September 2026 at `b213899`: 27 tests, 9 failures, and 27 of 27 once the two variables are dropped. CI passes only because Actions does not export the token into the step. A test whose result depends on the caller's credentials is testing the caller.

1. `test_governed_review.py` drops `GITHUB_TOKEN` and `GSTACK_GITHUB_API` from `self.env` in `setUp`, beside the variables it already drops. The one test that sets them for its stub server still does, after `setUp`.
2. With `GITHUB_TOKEN` exported to a value GitHub would refuse, `test_governed_review.py` passes in full. That is the evidence: the suite no longer reads the caller's token.
3. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.35.0, and the top-level marketplace version moves, per CI-002.
4. `scripts/run_all_tests.py` reports what it examined with a nonzero count and no failures.

**Also in this change (administrative, no criteria):** `MIGRATION-rube-commits.md` and the May 2026 root `cowork-session-handoff.md` move to `docs/archive/`. Nothing in the repository references either. The other two `MIGRATION-*` files stay, because the `composio` and `daily-ops` READMEs cite them by name, and `CHARTER.md` and `PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md` are active governance cited by 35 `GOVERNANCE.md` files. The status lines of CI-002, XE-013, XE-015 and GA-007 are brought to what merged, from the review records and pull requests.

### XE-020 — A CI run is named by the same path the repository is

**Status:** done. Merged to `main` in `fec5031` (PR #57, head `f477e5f`) on 25 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260924-221356-49b2a74-usjozs79` (codex/gpt-6-astra): round 1 found `.` and `..` treated as directory names and `dispatch` resolving relative paths against the review directory; both fixed through one `as_repo_ref()` rule that `--head` now shares; round 2 `fixes_verified`, 4/4, with the `tests` workflow green at the reviewed head. The builder's own gate run caught a third defect before review (a packet with no repos raised KeyError). Closes SM-003 ledger entry M-001.

**Links introduced:** none. It resolves a value the packet already carries.

Opening a review resolves each `repos[].path` (on macOS, `/tmp/x` becomes `/private/tmp/x`), but `fetch_ci_evidence` compares `tests.ci_runs[].repo` against those resolved paths unresolved, at round time, and nothing checks it at open. A packet naming `/tmp/xe019` for both passes the repository check and fails the CI read with `repo is not a repository in this packet`, which a reviewer then reports as missing evidence. Review `20260924-162903-25a6677-7hrcgdnp` spent a round on exactly this, after the same resolution had already been recorded in project memory and PR #42.

1. A `tests.ci_runs[].repo` that is a path is resolved the same way `repos[].path` is, both in the packet at open and from `--ci-run` on `round` and `dispatch`, before it is matched.
2. A `ci_runs` entry that still matches no repository after resolution refuses the open with the entry named, rather than opening a review whose evidence will read nothing.
3. Tests: a `/tmp` alias resolving to a `/private/tmp` repository matches; an entry naming no repository refuses at open.
4. `gstack-execution` moves its version, and the top-level marketplace version moves, per CI-002.

### XE-021 — A note on a non-blocking finding doesn't void a clean round

**Status:** done. Merged to `main` in `cbc803c` (PR #55, head `d16e285`) on 25 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260924-205619-0bb753e-ff9ubeaz` (codex/gpt-6-astra): round 1 found one blocker (F1, a duplicated non-blocking entry passed because the skip ran before the duplicate check), fixed in `086b529`; round 2 `fixes_verified`. Main then moved (XE-020 for CI-run paths merged first), so the branch took main, the item was renumbered from XE-020, and review `20260925-073122-d16e285-nhf26_0s` passed the merged head `no_blocking_findings`, 6/6, with the `tests` workflow green at that head and read by the dispatcher itself. The branch keeps its pre-renumber name.

**Links introduced:** none. The validator drops rows it already knows are not blocker resolutions; nothing is named, cached or retained.

STIGViewer PL-004 review `20260924-202346-8e39522-hibt89yr` round 2 came back `no_blocking_findings`, 5 of 5 criteria met, both prior findings resolved with evidence, and CI read by the dispatcher at the reviewed head. The round was recorded `malformed_output`, which is terminal, because `blocker_resolutions` carried an entry for F2, a prior finding of severity `separate`. `validate` accepts a resolution only for a prior blocker and rejects the whole reply on any other id. The prompt hands the reviewer every prior finding with its disposition, so resolving the non-blocking one too is the natural reading, and a clean verdict was thrown away over an entry the contract never asked for. A review that ends on the reviewer's thoroughness rather than on the code is the same failure XE-018 closed from the other side.

1. `validate` ignores a `blocker_resolutions` entry whose id is a prior finding that was not blocking, and removes it from the recorded reply. An id that names no prior finding, and a duplicate, are still `malformed_output`.
2. Coverage is unchanged: every prior blocker still needs exactly one entry, and a resolved blocker still needs a `fixed` or `disproved` disposition.
3. The peer-review contract says non-blocking prior findings get no entry and that one given is ignored, in the paragraph that defines `blocker_resolutions`.
4. Tests: a fix round whose reply resolves a prior blocker and also a prior `separate` finding passes and records only the blocker's entry; a reply resolving an id that was never a finding is still `malformed_output`.
5. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.38.0, and the top-level marketplace version moves, per CI-002.
6. `peer_review.py --selftest` passes, and `scripts/run_all_tests.py` reports what it examined with a nonzero count and no failures.

### XE-022 — A test that stages an absent reviewer cannot find the real one

**Status:** done. Merged to `main` in `e715da2` (PR #61, head `c400a53`) on 25 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260925-080303-c400a53-vpkvgbxq` (codex/gpt-6-astra, `no_blocking_findings`, 5/5), with the `tests` workflow green at the reviewed head and read by the dispatcher itself. The review before it (`20260925-075306-d939046-6xn07qgh`) found F1, relative and empty `PATH` entries judged from the wrong working directory, fixed in `932eca7` and verified resolved; it ended `malformed_output` on a verdict that disagreed with its own severities, so the pass is a new review.

**Links introduced:** none. The test narrows the environment it hands its subprocess; nothing is named, cached or retained.

`test_a_reviewer_that_exits_nonzero_completes_the_round_as_unavailable` in `test_dispatch_collect.py` means to prove that a round with no reviewer completes as `review_unavailable`. It stages the absence by putting an empty directory at the front of `PATH` and keeping the rest, and `run_reviewer` finds `codex` with `shutil.which`. So on any machine with the CLI installed, the real one answers. Measured on the Release Owner's Mac on 25 September 2026 at `cbc803c`: the round record names reviewer `codex`, model `gpt-6-astra`, transport `cli`, with usage parsed from codex's own "tokens used" line, which the stub never prints. It read 3 of 5 files and returned a verdict that disagreed with its severities, recorded `malformed_output`. Four of the file's five tests pass; this one fails. CI passes only because the Actions runner has no reviewer installed. It's XE-019's defect with a different credential: a test whose result depends on what the caller has installed is testing the caller, and every local run of the suite spends a real Codex review.

1. When the fixture is handed a bin directory, it removes from the subprocess `PATH` every entry holding an executable named for a CLI reviewer in `peer_review.REVIEWERS`, read from the module rather than restated, and drops `GSTACK_OPENROUTER_ENV` so no api reviewer can resolve. Other entries stay, so `git` still resolves.
2. The test asserts its own precondition before it dispatches: no reviewer in `REVIEWER_ORDER` resolves under the environment it hands the subprocess. A test that can't stage the absence fails as a setup error, not on a real review.
3. On the Release Owner's Mac, with `codex` installed and on `PATH`, `test_dispatch_collect.py` passes 5 of 5, and the round record for the unavailable case names no reviewer model.
4. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.39.0, and the top-level marketplace version moves, per CI-002.
5. `scripts/run_all_tests.py` in CI reports what it examined with a nonzero count and no failures.

**Not in this item:** `endform_workflow --selftest`'s `/tmp` vs `/private/tmp` failure, a separate defect in `_tsconfig_extends`. The three other tests that put a stub on `PATH` stub the reviewer they reach, so they shadow the real one rather than miss it.

### XE-023 — The E2E preflight resolves the repo before it compares paths under it

**Status:** done. Merged to `main` in `1d87f01` (PR #63, head `6004064`) on 25 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260925-091247-c1e8f75-wn8thxfc` (codex/gpt-6-astra, `fixes_verified`, 2 rounds): round 1 found F1, the first symlink case never reached the comparison that crashed, fixed in `8f70d6f` and verified resolved. The `tests` workflow was green at the reviewed head and read by the dispatcher itself.

**Links introduced:** none. `preflight()` resolves the path it's handed; nothing is named, cached or retained.

`endform_workflow.py --selftest` fails on macOS and passes on Linux CI. `_tsconfig_extends` resolves the package root, so a `tsconfig.json` under it comes back as `/private/tmp/...`, then compares it with `relative_to()` against a repo path that was never resolved, `/tmp/...`. On macOS `/tmp` is a link to `/private/tmp`, so `relative_to()` raises `ValueError` and the selftest dies. `main()` resolves `--repo` before it calls `preflight()`, so the command a user runs is safe; the selftest isn't, because it hands `preflight()` the raw `tempfile.mkdtemp()` path. Measured on the Release Owner's Mac on 25 September 2026 at `74f0048`: it fails the same way on `main`. It's the second of the two macOS-only failures open since PR #42.

1. `preflight()` resolves the repo it is given, once, before any helper compares a path against it. Every caller routes through it, so no helper resolves on its own.
2. The selftest runs `preflight()` through a symlink to a repo whose `tsconfig.json` extends a relative path, so the case is exercised on Linux CI and not only on a Mac.
3. On the Release Owner's Mac, `endform_workflow.py --selftest` passes, captured by script into `docs/evidence/` with the SHA-256 of every file it ran, as XE-022 did.
4. `plugins/gstack-execution/.claude-plugin/plugin.json` moves from 0.39.1, and the top-level marketplace version moves, per CI-002. XE-024 ships under the same bump.
5. `scripts/run_all_tests.py` in CI reports what it examined with a nonzero count and no failures, and on the Release Owner's Mac, captured into the same evidence file, it reports no failures.


### XE-024 — A task-graph test that fails says why

**Status:** done. Merged to `main` in `1d87f01` (PR #63, head `6004064`) on 25 September 2026 by `moxywolf-agent[bot]` on Dorian's instruction, recorded by `record-release` as `agent_merge_on_instruction`. Review `20260925-091247-c1e8f75-wn8thxfc` (codex/gpt-6-astra, `fixes_verified`, 2 rounds): round 1 found F1, the first symlink case never reached the comparison that crashed, fixed in `8f70d6f` and verified resolved. The `tests` workflow was green at the reviewed head and read by the dispatcher itself. The root cause of the intermittent failure is still open; the next failure carries its stderr.

**Links introduced:** none. A test helper adds the executor's stderr to an assertion message; nothing is named, cached or retained.

`test_task_graph.py`'s `test_changed_revision_and_evidence_invalidate_cached_success` failed once in a full Linux run at `b847b6c` on 24 September 2026, and once in 33 isolated runs on the Release Owner's Mac on 25 September, both times on the first `execute()` with return code 1, before any caching is involved. 150 in-process runs, 150 under full CPU load, and 218 subprocess runs, four at a time, didn't reproduce it. The cause is unknown, and the test destroys the only evidence: `assertEqual(r.returncode, 0)` prints `1 != 0` and throws the executor's stderr away. Guessing a fix for a failure nobody can see would be a second defect.

1. Every assertion in `test_task_graph.py` that an executor call returned 0 goes through one helper whose failure message carries that call's stderr. No assertion that a call succeeded is left without it.
2. The root cause is not claimed here. The next failure's stderr is filed as its own item.
3. It ships with XE-023, under XE-023 criterion 4's version bump.

## Validation

Write failing behavioral tests before implementation. Exercise real dispatcher and state transitions using temporary repositories. Use controlled reviewer responses for malformed-output and failure cases, followed by a live cross-tool review to verify integration.

Test stale approvals, incomplete acceptance, dropped blockers, failed branches, changed inputs, interrupted runs, and duplicate release attempts. No production release is required to prove refusal behavior.

## Amendments log

- 2026-09-25: Added XE-023 and XE-024 on Dorian's instruction ("fix the last four") to close the two macOS-only failures open since PR #42 (XE-022 closed the other) and the intermittent `test_task_graph` failure. XE-024 makes that test report its cause rather than guessing one: 518 runs could not reproduce it.

- 2026-09-25: GA-007 and XE-015 marked done on Dorian's ruling. Both merged on 22 September without cross-tool review; each was reviewed clean on 25 September at exactly the head that merged. `record-release` refuses both as `merge predates the release handoff`, by design, so neither carries a release record.

- 2026-09-25: Added XE-022 on Dorian's instruction ("do that, yes") after `test_dispatch_collect.py`'s macOS-only failure, open since PR #42, was traced to the real `codex` answering a test that meant to have no reviewer.

- 2026-09-24: Added XE-021 (drafted as XE-020, renumbered when XE-020 merged first for CI-run paths) on Dorian's instruction ("fix the review tool first") after STIGViewer PL-004 round 2 returned a clean verdict that `validate` recorded as `malformed_output` because the reviewer also resolved a non-blocking finding.

- 2026-09-24: Dorian approved SM-003 after asking whether session end should review the session's mistakes into a journal. The answer was a ledger whose entries must become a check or a rule at the point of action, because the day's own `/private/tmp` mistake repeated a lesson already in memory. XE-020 is declared planned as the check SM-003's first seeded entry becomes.

- 2026-09-24: Dorian approved XE-019 after a health pass (graphify plus github-repo-analyzer) found `test_governed_review.py` failing 9 of 27 in any shell that exports `GITHUB_TOKEN`. The same change archives two unreferenced root documents and brings four status lines to what merged.

- 2026-09-24: Added XE-018 on Dorian's instruction ("fix the gstack plugin first") after four codex reviews of SAMS PL-001 found no code defect and still could not pass: the surface never carried the files the change names, and the green CI run at the reviewed head reached the reviewer only as the builder's account of it.

- 2026-09-23: Added XE-017 on Dorian's instruction ("Handle it like XE-016") after DS-001's passing review was refused at release as `stale_link`, on five line-0 `separate` findings the contract itself had asked the reviewer to write.

- 2026-09-23: Added XE-016 on Dorian's instruction after DS-001's review round 2 crashed inside `reviewer_usage()` on a comma-only codex usage match, losing a completed codex round. Fixed as its own item rather than inside DS-001.

- 2026-09-22: Dorian approved a ninth objective, design craft, after a fit review of impeccable v4.3.1 against the v3.8.0 material already in `saas-frontend-designer` (`Taskade/Team Plugins/06 – Engineering/impeccable-v4-delta-fit-2026-09-22.md`). DS-001 ports five playbooks and the four page modes and leaves the engine out.

- 2026-09-22: Dorian amended DS-001 criterion 5 during the build. Criterion 3's whole-skill link check found four dead links in two of the ten June-vendored references (`craft.md`, `typeset.md`); criterion 5 had forbidden touching them. Link repair only is now allowed in those two files.

- 2026-09-22: Added XE-015, drafted by Claude for Dorian after a live BD-001 review on `MoxyWolfLLC/crm` came back having opened none of the eleven files it was offered. The prompt told it no commands could be run; `codex exec --sandbox read-only` withholds writes, not shell, and shell is how codex opens a file. Proved on the Release Owner's Mac at codex-cli 0.154.0 with the flags `run_reviewer` passes, twice, once with `--output-schema` to rule out structured output disabling tools: codex ran `cat` and returned the file both times. The round was refused only because its verdict disagreed with its severities, so the second half of this item applies `examined_nothing`, which the vocabulary already defines and already applies to the verifier, to the reviewer as well. Also restored XE-014 in the preceding commit: it was approved the same day and existed only in a checkout whose `.git` points at a missing `.git.nosync`, with no objects, refs or history.

- 2026-09-22: XE-014 declared and approved by Dorian, and its first two criteria rewritten before any code. The item was approved on the premise that XE-010's scorer records `unavailable` because the gateway credential is unreachable. Measured rather than assumed, and the premise was wrong in its mechanism. `packet_coverage.mjs` imports `ai` and no `package.json` exists anywhere in this repository, so the script exits 1 at `ERR_MODULE_NOT_FOUND` before `main()` runs and writes nothing to the packet. The credential branch it was supposed to reach is downstream of an import that has never resolved. `tests.yml` is `setup-python` only, with no `setup-node`, no install step and no invocation of the scorer, so CI has never run it either, and `test_packet_coverage.py` exercises `coverage_verdict` alone over hand-built dicts. The suite is green over a producer that has never executed once, which is XE-010 criterion 6 one level up: that criterion made the extractor prove its own coverage, and nothing made the scorer prove it can start. The credential finding stands on its own evidence and is kept: `aigateway.env` holds a working 60-character `vck_` key that returns HTTP 200 from `typesafe-ai/jev` in 135ms and separates a covered criterion at 0.90 from an absurd one at 0.05, while nothing in `.zshrc`, `.zprofile` or `.profile` exports it and a fresh login shell has `AI_GATEWAY_API_KEY`, `GSTACK_OPENROUTER_ENV` and `GSTACK_AGENT_APP_ENV` all unset. Two defects stacked, and only the second one was declared. What is NOT a defect, and was claimed as one in the first draft: there is no silent false pass. `coverage_verdict` returns `not_run` for an absent report and the review state records `coverage_checked: false`, which is XE-010 criterion 5 working as written. The gate is absent and says so; what failed is that nothing reads the saying. Criterion 6 was added for that. Not verified: whether `experimental_evaluate` reads `AI_GATEWAY_API_KEY` from the process environment rather than from an argument. The script's `key` is used only as a guard and is never passed to the call, so the fix must set it into `process.env` rather than hand it over, and that inference rests on Vercel's documentation naming the variable for all three integration paths, not on reading the package, which is installed nowhere on this machine.

- 2026-09-22: CI-002 criterion 9's worked example corrected before any code, approved by Dorian. The criterion named `github-repo-analyzer` at 0.11.0 as the real-history catch at `6c9912c`. Measured, it bumped there, 0.10.0 to 0.11.0. What `6c9912c` actually ships at an unmoved version is `gstack-execution`, which changed in that merge and stayed at 0.27.0. The premise is untouched and only the example was wrong, but a test written to the old wording asserts something false, and a check that lands red is a check somebody turns off, per DR-102. The criterion now names `gstack-execution` and adds the range `d619c06..2293ff6`, where the top-level version is unmoved across six consecutive merges. Three of those six changed a plugin and are caught; the other three changed no plugin and owe no bump, which is criterion 2 read exactly. A first draft of this entry claimed all six were catches. The real-history test refuted it on the first run, which is the test doing its job on the sentence that introduced it.

- 2026-09-21: GA-007 declared and built in the same change, on Dorian's instruction to fix it and merge. It follows directly from GA-006. GA-006 made the installation resolve per repository, which is right, and made the credential's reach a thing that varies per repository, which nothing could then inspect. A permission accepted on one installation and pending on another is invisible: the refusal reads the same as never having asked. The information was already in the response `mint()` parses. This item prints it.

- 2026-09-21: CI-002 declared and approved by Dorian, and its top-level criterion added before any code. The item was approved checking the per-plugin version only. Reading DR-013 before writing it found the version has three homes and that the client gates on the top-level `marketplace.json` version, so the approved criteria would have passed a change nobody can install. Measured rather than assumed: the top-level moved once, at `6c9912c`, across four merges, so `github-repo-analyzer` 0.12.0 has not reached clients either. Criterion 2 added and approved, and the top-level bump rides in the CI-002 change so the check lands over a clean catalog, per DR-102. Not verified: that the plugin manager still gates this way today. DR-013 is taken on the document's word.

- 2026-09-21: XE-013 declared and approved by Dorian, ahead of CI-002, prompted by his question about using OpenRouter for reviews instead of coding each CLI in. The finding is that XE-005 finished the table and never finished the dispatch path, so a new reviewer is still a code change, all three entries declare headroom they cannot enforce, and a missing binary is why 21 September's reviews were single-family. The item's shape follows from OpenRouter being a transport rather than a reviewer: one entry named for it would span every family and re-encode the error XE-005 removed. Criterion 6 was the one open question and Dorian settled it: what a reviewer was sent is recorded under its own field, and EV-008's measurement of what a reviewer chose to open is left alone.

- 2026-09-21: GA-006 merged as `27fd672`. Its release handoff was prepared before the merge, which CI-001's was not, but `record-release` was still blocked: the review ran in the session cloud container because the reviewer needs more wall time than the device shell allows, so the record names that container's checkout, and `api.github.com` answers 403 there through the agent proxy. The host with the credential cannot see the record and the host with the record cannot reach GitHub. Verified rather than assumed: the same installation token reads PR #31 from the device and returns 403 from the cloud, and a bare `curl` to `api.github.com` from the cloud returns 403 as well. No record was fabricated. The lesson is about where a review is opened, not about what the contract demands.

- 2026-09-21: `test_agent_token` fixed-slot defect fixed, carried in the GA-006 checkpoint. It read `GIT_CONFIG_KEY_0` and asserted the extraheader sat there, but `token_env` APPENDS at the existing `GIT_CONFIG_COUNT`, so slot 0 only holds when the ambient environment sets no git config entry. The production code was right; the test asserted an empty environment instead of the contract and went red on a host that sets `credential.interactive`. Demonstrated both ways before and after the fix. Pre-existing on `main`, not introduced by GA-006. No criteria changed.

- 2026-09-21: `test_agent_token` defect found and fixed while bringing GA-006 current. It read `GIT_CONFIG_KEY_0` and asserted the extraheader sat there, but `token_env` APPENDS at the existing `GIT_CONFIG_COUNT`, so slot 0 only holds when the ambient environment sets no git config entry. The production code was right and the test asserted an empty environment instead of the contract: on a host that sets `credential.interactive` the suite went red with `'credential.interactive' != 'http.https://github.com/.extraheader'` while nothing was wrong. The test now derives the slot from the count and names it when the assertion fails. Pre-existing on `main`, not introduced by GA-006, and carried in this checkpoint because GA-006 already edits that file. No criteria changed.

- 2026-09-21: CI-001 merged as `d619c06`, and the release handoff was skipped. The review passed and the merge was instructed, but `peer_review.py release` never ran, so `record-release` has no `release.json` to verify against and a handoff prepared now would postdate the merge. No record was fabricated. The loop treated "present the checkpoint to the named human" as satisfied by saying so in conversation; the contract means the artifact. Carried here as a note rather than a criterion change, because nothing in the contract needs changing: the step exists and was not run.

- 2026-09-21: Peer-review host defect found and fixed. Two consecutive rounds against the CI-001 checkpoint returned `empty_output`, which the gate's error text attributes to quota or headroom. Neither was the cause. Replaying the round prompt directly showed the reviewer attempting `run_shell_command` twice, being told the tool does not exist, and then exiting 0 with an empty response: `--approval-mode plan` is read-only and withholds shell execution, and nothing in the prompt said so, so the reviewer spent its whole turn discovering it. The packet's `tests.commands` read as an instruction to re-run them. The prompt now states that no commands can be run, that the commands are a record rather than an instruction, and that a judgement genuinely needing execution is reported with severity `separate`. No criteria changed. Carried in the CI-001 checkpoint and covered by its review, per the XE-005.4 precedent.

- 2026-09-21: Eighth objective, the catalog imports, and CI-001, approved by Dorian. Prompted by an outside compatibility assessment of this repository's plugins, which found ten `SKILL.md` packages that a loader cannot read: eight descriptions over the 1024-character limit, and two whose plain-scalar descriptions contain an unquoted colon, which YAML reads as a nested key. Every one of them shipped under a green build, because this repository's suites examine its scripts and never its catalog. CI-001 adds the check and fixes all ten in the same change. The fix is the same in every case, a folded (`>`) block, which is immune to the colon; the eight shortened descriptions keep their original text in the body.

- 2026-09-21: RR-002 declared and approved by Dorian, and RR-001 criterion 4 given criterion 1's "did not execute" clause. Three peer-review rounds landed on the same point: criterion 4 as written demanded runtime verification that a static reviewer cannot supply, and the reviewer's own note was that the criteria must be relaxed to match the static design or the tool needs a dynamic component. Dorian chose the dynamic component. RR-001 stays the static reviewer; RR-002 carries the execution, opt-in only, because running a reviewed repository's code is a different risk posture from reading it.

- 2026-09-21: XE-005 criterion 4 defect found and fixed (see its status). No criteria changed; the code now does what the approved criterion already required. Carried in the RR-001 checkpoint and covered by its review.

- 2026-09-20: Seventh objective, retrieval review, approved by Dorian after the ECC upstream refresh (`Taskade/Team Plugins/06 – Engineering/ecc-refresh-2026-09-20.md`). RR-001 concept-ports the checks from ECC's `rag-pipeline-reviewer` (MIT, (c) Affaan Mustafa), taking the ideas and no code. It is EV-001's rule applied to somebody else's pipeline. The refresh's three other concept-ports are not proposed here.

- 2026-09-20: GA-006 declared, and the app-identity constraint stops naming one installation. GA-005 criterion 9 asked Dorian to decide the OpenControls-AI path. He decided it this session, making the app public and installing it on OpenControls-AI, which immediately exposed what criterion 1 had assumed: one installation id in `github-app.env`. A token minted from the MoxyWolfLLC installation answers 404 for `OpenControls-AI/cki`, the same answer GitHub gives for a repository that does not exist, so the credential's reach fails in the shape hardest to read. GA-006 resolves the installation from the repository instead, and it is what makes criterion 9's remaining step safe: the PAT cannot leave the vault while OpenControls-AI pushes depend on it. A third installation, on GRCSchema, was created by the agent misclicking a row during the same session and is Dorian's to keep or remove.

- 2026-09-20: Sixth objective, trust boundaries, declared and approved by Dorian. TB-001 puts an `origin` on every record, which is what makes the fifth prediction in "Paid in the Bottom Layer" measurable. TB-002 puts the untrusted-text enclosure in one file. TB-003 extends the existing grant model to destinations rather than adding a denylist, with the reasoning and the test evidence in DR-099: a four-pattern denylist allowed nine of twelve attacks from its own author's list, and its seven-pattern successor blocked four of six ordinary engineering calls while still allowing four attacks. XE-012 gains criterion 10, recording packet and context size, with no prediction attached. The vocabulary goes to 1.2.0 when TB-001 merges, which is an XE-012 break point. Prompted by three rounds of external response to the pre-registration; the security literature verified on reading and the proposed fix did not.

- 2026-09-20: Status lines corrected for GA-005, XE-012, XE-011 and SM-002, which all read `building` after they had merged. GA-005 (`ce7a5e6`, PR #27) and XE-012 (`56dca19`, PR #25) were merged by `moxywolf-agent[bot]` on Dorian's recorded instruction **without peer review at the merged head**, because no reviewer was available, and each status now says so. `record-release` requires a passing review and has recorded no release for either; no record was fabricated to close the gap. XE-012's status also carries the two open defects in its first report, both of which report a zero for a value the record holds as null.

- 2026-09-20: GA-005 declared, pending Dorian's approval, with three new constraints: the agent's GitHub identity is the `moxywolf-agent` app, `main` carries a ruleset the app bypasses for pull requests only, and the agent merges when Dorian tells it to, recorded as agent-executed. The first draft said the agent never merges; Dorian rejected that the same day. It closes the gap the 2026-09-12 entry below named and node 14 of the memory graph. The GitHub settings were made and tested by hand before this entry, and GA-005 records that test. XE-012's DESIGN.md changes are on `build/XE-012-run-measurement` and aren't in this copy; the two branches touch different sections.
- 2026-09-19: P1's "net of tokens spent in commits that change vocabulary.json" read two ways. The builder took it as "including" and two independent reviews read it as "subtract". Dorian settled it as subtract: correct runs that changed `vocabulary.json` leave P1's comparison and their tokens are reported apart. The text is unchanged; this line records which reading it means.

- 2026-09-19: XE-012 approved by Dorian, in the session rather than with the editor's button, on text identical to the editor's draft. Before any code, its opening figures were corrected. The first count of the session's tokens summed transcript entries, and the transcript repeats one message's usage across several entries, so turns and cache reads were overstated by about 1.9 times. The corrected count, deduplicated by message ID, replaces it, and the error is recorded in the item as its first finding.

- 2026-09-19: XE-012 declared, pending Dorian's approval. It measures every gstack run's cost from here on, into the vault, with each vocabulary version as a break point, and states four predictions with their refutation conditions before any data exists. XE-011 criteria 6 to 8 are superseded by it, because the baseline they required was lost when XE-011 merged before measurement ran; their original text is in git history at `3df35d0`. Dorian chose to measure forward rather than replay tasks against the pre-vocabulary commit.

- 2026-09-19: XE-011, SM-001 and SM-002 headings take the ` — ` separator the other items use. It is a machine format, not prose: `packet_coverage.mjs` finds items by it, and with a colon it reported "DESIGN.md declares no criteria" for all three. The same extractor only recognised the XE, EV, GA and GS prefixes, so AP and SM items could never be claimed by a packet; it now takes any two-letter prefix. Both found while opening the SM-002 and XE-011 review.

- 2026-09-19: SM-001 criterion 2 split into SM-002, approved by Dorian, so the label fix can ship and be reviewed without the rest of SM-001. Building one criterion under SM-001's ID would have been refused by XE-010's packet-coverage gate, correctly. Reading the files showed the mapping lives in seven places, five in the repo and two in the vault, not the three SM-001 named, so SM-002 lists all seven. SM-002 and XE-011 are built on one branch and reviewed as one checkpoint, per XE-004.

- 2026-09-19: Fifth objective, session memory, and SM-001 declared, pending Dorian's approval. SM-001 builds all four arrows between the context window, the graph and the vocabulary in `project-init`'s session start and end. Arrows 1 and 2 ship alone, and arrows 3 and 4 wait on XE-011's decision rule. Prompted the same day, when `/session-start` read a handoff saying PR #10 was open two days after it had merged. Revised the same day after reading the whole `/session-end` skill and querying MOXY: the label rule is removed rather than corrected, because two conventions are live on the board; "What landed" stays prose for production-data state; refs record branch and HEAD per repo; and the `-08:00` offset is fixed.

- 2026-09-19: XE-011 declared, pending Dorian's approval. It asks whether a shared vocabulary for the loop's own contracts lowers cost per correct answer, and it fixes the decision rule before the measurement runs. It depends on EV-006 criterion 1 and EV-008 criteria 1 (second half) and 3 for full measurement, and names what it can't see until they're built. Same refresh, status lines only: EV-009 and XE-006 through XE-010 read `building` or `declared, building in this change` after they had merged, and XE-003 and XE-004 read `human merge pending` after `d26c18a`. Each now cites its merge commit from `git log origin/main`. Review IDs for those merges weren't carried into this doc, and this refresh didn't add them. GA-001 through GA-004 still read `review`. PR #4 (`9f08abe`) and PR #5 (`47fb530`) are merged, but the item-to-PR mapping wasn't verified here, so those lines are unchanged. No acceptance criterion on any existing item was edited.

- 2026-09-17: XE-005 declared after the checkpoint for XE-001 and XE-002 landed unreviewed. Two review records for `5761c37` both returned `review_unavailable`, first because the `codex` CLI was absent and then, once it was installed and authenticated, because the OpenAI account had no credits. Dorian merged as Release Owner with the gap recorded on the pull request, which the release-boundary contract already allows: a passing machine review was never release authorization. Cursor and Gemini were both considered as a third reviewer. Gemini is the better fit on independence, since Cursor can run the builder's own model family, and the item is written so that neither can be added without declaring what actually differs.

- 2026-09-17: XE-002 built alongside XE-001 and reviewed with it in one checkpoint, per XE-004. Capability grants extend `governance.py` rather than adding a parallel authority path: the packet's `data_use` policy already carried an owner, an exact-match `allowed_tools` list and pattern-matched `output_roots`, and the defect was that the policy is re-declared per invocation and matched by exact string. Grants persist, match by pattern, and record the granting human. The classes that matter are unreachable by any grant.

- 2026-09-17: Dorian approved a fourth objective after an audit of the 2026-09-15/16 support-platform session. The audit counted 2,319 tool calls against 54 file changes, 1,039 browser calls where connectors were configured, 43 approval interruptions, and 193 failed commands. XE-001 is built in this change; XE-002 through XE-004 are declared and not started. The session's own self-diagnosis, recorded in its transcript, agrees: the implementation stayed small and the loop around it did not.

- 2026-09-12: Dorian approved a third objective after reading "When Structure Pays", which reports three defects in this executor and three false passes in this repository's own completeness gate. EV-001 through EV-005 are built in this change; EV-006 through EV-008 are declared and not started. The paper's central claim is the reason the objective exists: completeness is a property of an artifact, evidential force is a property of the relationship between the artifact and the work, and that relationship is not in the artifact.

- 2026-09-11: Approved by Dorian in the Codex Team Plugins conversation. Establishes the Governed Autonomy objective and acceptance criteria above. Initial implementation is GA-001; subsequent items begin only when requested.

- 2026-09-11: Dorian requested the remaining task graph implementation ("Then build it"). GA-002 through GA-004 retain the approved criteria.

- 2026-09-11: Dorian approved a second objective for this repository after a naming defect surfaced during an academic-pipeline run: the deliverable was written to a hardcoded `complete_document.md` and the formatting skill carried a fabricated author surname. AP-001 through AP-003 add derived naming, producers for declared requirements, and a mechanical release gate.

- 2026-09-12: AP-001 through AP-003 complete. Two reviews, four blocking findings, all false passes in either the acceptance test or the gate itself. Both merges were executed by Claude with the vault PAT at Dorian's explicit instruction rather than by a human clicking Merge; the merge commits record that, and record-release cannot distinguish the two because the PAT carries the owner's identity. Closing that gap needs an agent credential without merge rights, which the release-boundary contract already assumes exists.
