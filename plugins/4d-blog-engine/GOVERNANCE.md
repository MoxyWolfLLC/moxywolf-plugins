# 4d-blog-engine — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

**Reference implementation.** 4d-blog-engine is the EXEMPLAR for the fleet: its nonce-bound 5-stage **Release Owner Gate** (preflight + BLOCKING reviewer + 100-point rubric + iteration cap, never auto-signs, stops before every irreversible publish, verified bibliography) is the pattern other side-effectful plugins copy for Tests 1, 2, 4, and 5. The gate skills (`release-owner-gate`, `discourse-sweep`) *are the governance model* — they enforce the human-signs checkpoint rather than performing the side effect themselves.

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `4d-blog-engine` | generate | Orchestrator/router; produces pipeline artifacts, does not publish |
| skill: `blog-init` | generate | One-time setup; writes local config only |
| skill: `blog-start` | read-only | Mounts project, surfaces in-progress pieces, proposes next step |
| skill: `blog-voice` | generate | Builds local voice profile from interview |
| skill: `discourse-sweep` | read-only | 30-day discourse research sweep; reads/reports |
| skill: `release-owner-gate` | side-effectful-gated | The Release Owner Gate itself — the named-human sign-off model; nonce-bound, never auto-signs |
| skill: `blog-publish` | side-effectful-gated | Stages signed post + auto-commits; human pushes in GitHub Desktop |
| skill: `blog-social` | side-effectful-gated | Derives social posts; human posts them |
| `blog-delegate` | generate | Phase 1 delegation/triage; produces angle + stall |
| `blog-describe` | generate | Phase 2 voice interview + outline |
| `blog-discern` | generate | Phase 3 draft + anti-slop pass |
| `blog-diligence` | side-effectful-gated | Phase 4 Release Owner Gate; blocking reviewer, human signs |
| `blog-init` | generate | Local setup |
| `blog-pillar` | generate | Creates/edits pillar + linking map (local files) |
| `blog-pipeline` | side-effectful-gated | Full pipeline; ends at publish gate (human pushes) |
| `blog-publish` | side-effectful-gated | Prepares + auto-commits; human pushes origin |
| `blog-social` | side-effectful-gated | Social derivatives; human posts |
| `blog-start` | read-only | Resume/surface state |
| `blog-status` | read-only | Reports phase + gates passed |
| `blog-term` | side-effectful-gated | Edits shared hub-links map; writer commits/pushes/tags |
| `blog-voice` | generate | Voice profile interview |
| `prose-lint` | generate | Deterministic linter on any file. Report by default; `--fix` applies only em-dash and quote repairs, outside code fences. For a file with no git history, the change is stated before it is made. |
| `prose-survival` | generate | Survival measurement + rewrite brief on any file. Never asserts watermark removal. Exits 2 with no baseline rather than substituting a document that was never Claude-sampled. |
| `scripts/perturbation.py`, `scripts/rewrite_text.py` | read-only | Pure measurement, stdlib only. No network, no model call, no file mutation. |
| `hooks/writing-lint.js` | read-only | PostToolUse baseline capture + register check on every prose file. Copies a file's first Write to `~/.claude/prose-baselines/` and reports the lint grade to stderr; never mutates the file. Skips code paths and files under 400 bytes, prunes baselines after 90 days. `BLOG_LINT_HOOK=off` silences it, `PROSE_BASELINE_DIR` relocates the store. Report-only because an email has no git history to undo a silent rewrite from. |

## Text watermarking — measurement, not removal (v0.19.0)

Claude's output carries a SynthID-Text-class watermark, in the choice among equally valid words, across every Anthropic surface with no opt-out. Anthropic's support page names the conditions under which it stops being reliably detectable: text "heavily edited, paraphrased, translated, or mixed into other writing", or too short to carry a signal.

**This plugin does not claim to remove it, and no skill here may tell a writer a piece is "clean" or "de-watermarked".** Detection requires a cryptographic key we do not hold and is in private preview, so removal is unverifiable by construction. What the plugin does instead is measure token-sequence survival — the input the mark rides on — and report it as the proxy it is.

**The rewrite direction is the governed decision.** Rewriting toward entropy perturbs the distribution and degrades the prose, which the upstream watermarks-remover project concedes in its own README. Rewriting toward the writer's voice profile perturbs the same distribution and improves the piece. Only the second is permitted here, and a rewrite that lowers survival while dropping the prose grade is a failed rewrite that must be reverted.

**The 50% gate threshold is uncalibrated** and labelled as such at its definition. It must not be wired into the Release Owner Gate as a blocking check; it is reported alongside the prose grade for the named signer to weigh.

### Coverage is universal, by the hook rather than by per-skill steps (v0.20.0)

Prose is drafted across `academic-pipeline`, `research-pipeline`, `email-lifecycle`, `editorial-forge`, `frontier-founder-smb`, `obsidian-update` and this plugin. Adding a snapshot step to each is seven edits that drift out of sync and get forgotten in the eighth. The PostToolUse hook captures the baseline on any prose file's first Write instead, so coverage follows the tool rather than the skill and a new writing plugin inherits it for free.

The store holds only what Claude wrote, keyed by absolute path, pruned at 90 days, on the writer's own machine. It is never transmitted and no skill reads it except on explicit `/prose-survival` invocation.

**Academic caveat.** `research-pipeline`'s citation verifier establishes claim-to-source correspondence. Rewriting a sentence carrying a verified datum can break that correspondence without touching the citation, so `/verify-citations` re-runs after any rewrite of cited passages. This is an integrity requirement, not a style one.
