# Noridoc: Execution Scripts

Path: @/plugins/gstack-execution/scripts

### Overview

- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) executes bounded cross-tool review and records revision-bound human release handoffs.
- The scripts support the command workflows in [commands](/plugins/gstack-execution/commands); the [peer-review contract](/plugins/gstack-execution/skills/gstack-execution/references/peer-review-contract.md) supplies the reviewer-facing rules.

### How it fits into the larger codebase

- [gstack-build.md](/plugins/gstack-execution/commands/gstack-build.md) supplies approved acceptance criteria and the human Release Owner's GitHub login to [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py). Machine review establishes readiness for a human release decision.
- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) routes Claude builders to Codex and Codex builders to Claude, using detached Git snapshots and explicit model floors. The reviewer receives the packet and contract; the builder owns fixes.

### Core Implementation

- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) resolves packet refs to commit SHAs and persists packets, rounds, dispositions, and state under the review ID. `GSTACK_PEER_REVIEW_DIR` overrides the default local review root.
- `validate()` in [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) requires exact acceptance coverage, boolean results, and nonblank evidence. Fix rounds account for every prior blocker with an explicit resolution and compatible disposition. Malformed or incomplete results cannot produce a passing round.
- `cmd_round()` in [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) advances fix-round bases to preceding heads, records failures as named outcomes, and tears down snapshots. Nonpassing rounds exit nonzero; terminal outcomes require a new review.
- `cmd_release()` in [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) revalidates evidence and clean local heads, writes a handoff, and stops with `awaiting_human_release`. `cmd_record_release()` reads GitHub's merge record and writes the exact head, actor, merge commit, and source into a local decision.

### Things to Know

- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) rejects blocking deferral and evidence-free disproof. A deferred blocker requires an approved design amendment and a new review under the [contract](/plugins/gstack-execution/skills/gstack-execution/references/peer-review-contract.md).
- [GOVERNANCE.md](/plugins/gstack-execution/GOVERNANCE.md) separates authorized branch work from human merge authority. Local records are writable and are not signatures; external branch protection and withholding human merge credentials from agents establish the operational boundary.

Created and maintained by Nori.
