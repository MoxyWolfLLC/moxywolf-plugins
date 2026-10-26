# MCP demand probe hardening

Local branch: build/mcp-probe-evidence, based on caeffa6.
Companion STIGViewer branch: build/mcp-probe-cases, based on 4d025ab.
Authorization: Dorian agreed to harden the deterministic harness and a representative subset before paid discovery runs.

## Behavior

- Decode matching JSON-RPC responses and fail protocol, HTTP and tool errors. Preserve raw response bodies for evidence even when decoding fails.
- Detect parsed and recognizable text application failures. Unsuccessful API envelopes cannot pass a normal success branch: only a not_found/404 denial with an explicit matching typed-absence branch is permitted.
- Require nonempty JSON REST bodies without application errors. Text/binary REST adapters are not implemented.
- Validate JSON Pointer contracts before traffic; apply every predicate in a branch and require at least one complete branch. Structured checks cannot be excused by legacy absence substrings.
- Freeze plan/profile hashes, declared bank hash, local revisions and harness source hashes. Record the server name/version actually observed; this does not authenticate a deployed commit.
- Preserve bounded, best-effort redacted response receipts, including JSON embedded in MCP text and SSE data lines. Record truncation/redaction flags and canonical original-body hash. Safe JSON formatting is preserved rather than mislabelled as redaction. A redacted/truncated body cannot support exact regrading.
- Refuse existing outputs or empty executable selections before dispatch. Keep production named-approval and draft restrictions.
- Carry structured/content/negative_only/liveness/unknown_legacy labels into gap-report coverage. No model-driven promotion or apply logic changes.

## Verification and review

Baseline harness: 57 tests passed before edits. Final focused harness suite: 75 tests passed. Test additions were observed failing before implementation. Local HTTP fixtures verify actual subprocess runs, server identity, source hashes, receipts, failure verdicts, preflight refusals and preserved output.

A separate local reviewer identified five grading/evidence issues and two follow-up evidence issues. Each was corrected and covered by regression tests. Final reviewer result: no remaining important findings. A later focused review of results ingestion found no issues and its nine tests passed. This is local review, not the required cross-vendor release review.

Full repository runner: 95 checks examined, 93 passed. One failure captured the new probe regression tests during their intentional failing phase; all those tests subsequently passed in the final focused run. The other was the unrelated session-record suite, whose scanner was absent in this environment. Installed pinned gitleaks 8.30.1 after validating the upstream release checksum; the session-record rerun passed all 109 tests in 64.004 seconds, with existing unclosed-socket ResourceWarnings. Every discovered check now has a passing result across the full run and corrected reruns; no single all-green full-run result is claimed. No skipped test is described as passed.

STIGViewer bank validation: 96 questions, zero errors; existing Q-0077 persona/parent warning remains. Six strengthened cases are exported separately, and original probe-plan.json and runs/probe-production.json are unchanged. Python compilation and git diff --check passed.

## Boundaries

No staging/production calls, OAuth flows, paid evaluations, results apply, pushes, merges or releases occurred. All changes are uncommitted local review candidates. They are not yet available through a pull on the Mac. Existing graph-context work remains isolated on build/gstack-graph-context.
