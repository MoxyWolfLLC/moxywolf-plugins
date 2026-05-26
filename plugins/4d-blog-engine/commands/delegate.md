---
description: Phase 1 — Delegation. Triage the topic, pick the angle, force the earned-secret stall.
argument-hint: <path-or-url-to-base-doc> [--angle "<question>"]
allowed-tools: [Read, Write, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:delegate — Phase 1 only

Invoke the `4d-blog-engine` orchestrator skill and run **only Phase 1**.

Phase 1 answers: *Is this the right work to hand to AI in the first place, and what part of it?*

It does:

1. Locate and classify the base document.
2. Capability triage — fast yes/no on "does this topic warrant a post against the jagged frontier?" Exits with a clean message on NO.
3. Angle elicitation — propose 3-5 candidate angles (or accept `--angle` if supplied). Each angle must be genuinely different from the others.
4. **The earned-secret stall.** Ask the user to name something they know from direct experience that the audience doesn't. The phase will not advance until a concrete, lived-experience answer is given. This is the feature.
5. Modality decision — automation / augmentation / agency (default: automation).
6. Write `<piece>/01-delegation.md` with `_phase: 01, _status: passed, _timestamp, earned_secret, modality` in frontmatter, plus the angle, audience persona (forced to specifics), and rejected-angle log.

Use this command when you want to scope and frame a piece without committing to writing it yet — useful for triaging a backlog of base documents before doing the heavy Discernment work on any of them.

Read `skills/4d-blog-engine/SKILL.md` §"Phase 1 — Delegation" for the full workflow.
