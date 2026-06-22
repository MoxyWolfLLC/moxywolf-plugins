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
