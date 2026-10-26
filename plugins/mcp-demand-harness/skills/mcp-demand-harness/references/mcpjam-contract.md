# MCPJam v6 contract (as verified against @mcpjam/cli 6.0.0, sdk 10.0.0)

Checked against the installed CLI and SDK source, not the older docs at docs.mcpjam.com/evals/installation, which describe the v5 commands.

## Commands

- `mcpjam evals run -t/-e` is gone. Local runs are `mcpjam test <suite.yaml>`. Hosted runs are `mcpjam cloud eval run`.
- `mcpjam cloud eval validate --file <suite> --format json` validates offline, with no account. Run it on every export.
- Bind the server at run time: `--server <name>=<url>` plus `--access-token`, or `--mcp-config <file>`.
- BYOK inference reads `ANTHROPIC_API_KEY`. Use `--inference byok`.
- `--reporter json-summary --out <file>` writes the report that `results.py` reads.

## Suite format

- Suites live in `.mcpjam/evals/*.yaml` with `schemaVersion: "2"`. Use `iterations`, not `runs`.
- Every object is closed. There are no `tags` or `metadata` fields, so the bank id travels in the case `id` (`q-0014`), the `title`, and `import.sourceCaseKey`.
- `intent` is at most 64 characters. The exporter writes `persona:kind`, and `scenario` carries persona and evidence.
- An `import` block needs `status` (`exact` or `approximated`) and `sourceCaseKey`. `exact` needs a `note` citing the mapping rule.
- Approximated cases are written `disabled`. They run only with `--allow-approximated <case>` and `--approval-reason`.

## What cannot be expressed

| Bank feature | MCPJam | What the exporter does |
|---|---|---|
| `first_tool_any_of` with more than one tool | No any-of predicate | Approximated, disabled |
| `must_not_match` | No negation, and regex takes no flags | Exact via a negative-lookahead whole-response pattern, with letters case-folded into classes (M-5) |
| `rubric` | The local run never executes the judge (`skipReason: localJudgeUnsupported`) | Approximated, and the gap report notes the rubric went unchecked |
| `payload`, `rest.calls` | Not model assertions | Run by `probe.py` |

## Report shape

`kind: "eval-local-run"`. The top-level `cases[]` has `id`, `title` and `passed`, but no tool calls. Tool calls live in `metadata.cases[].iterations[].toolCalls[].toolName`, and verdicts in `iterations[].taskVerdict`. Read one or the other, never both, or every case is counted twice.

## Server behaviour that matters

If a server never sets `isError` on a typed absence, MCPJam's `noToolErrors` passes it. That is correct for "we don't hold this", but it means discovery liveness cannot catch a tool that answers "not found" to everything. The probe layer covers that.
