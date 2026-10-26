# MCP probe evidence implementation plan

Goal: make deterministic probe passes distinguish transport liveness from verified response contracts and preserve bounded sanitized evidence.

1. Add probe_checks.py with strict RPC decoding, HTTP/tool error guards, JSON Pointer predicates (type, nonempty, equals), explicit alternative branches, and bounded redacted response receipts. Test malformed/RPC/tool errors, empty and negative-only answers, valid absence and secret redaction.
2. Integrate probe.py: validate contracts before traffic, preserve initialize serverInfo, plan/profile/bank hashes and local revisions, classify assertion strength, refuse overwrite/empty selections, and save evidence for each layer. Tests use only a local HTTP fixture.
3. Extend bank validation and probe export with json_any_of. Other exporters retain existing answer expectations; structural checks are direct-probe only. Test invalid contracts and exported preservation.
4. On the STIGViewer case branch, strengthen six representative cases from actual server contracts, record source references, and generate a separate pilot plan. Preserve baseline and original exports. No production requests, paid evaluations, bank promotion, pushes or releases.
5. Run the harness suite and relevant integration checks; record review limits and rollout instructions. Existing graph implementation stays isolated on its original branch.
