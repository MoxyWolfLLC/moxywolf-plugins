# STIGViewer profile

`profiles/stigviewer.json`. The bank lives in `apps/web/scripts/eval/demand/` in the stigviewer repo, and the MCPJam suites live in `.mcpjam/evals/`.

## Sources the first bank was seeded from (commit b366078)

| Source | What it gave |
|---|---|
| `apps/web/lib/mcp/tools.ts`, `prompts.ts` | 11 tools and 8 prompts |
| `apps/web/app/api/v1/**/route.ts` | 60 routes, 39 of them reached by no MCP tool |
| `docs/design/feature/content-expansion/product-marketing-context-2026-07-16.md` | 5 personas |
| `docs/design/feature/mcp-server/2026-08-16-mcp-icp-question-inventory.md` | 52 questions. The doc calls itself "a hypothesis about demand, not evidence of it" |
| `apps/web/scripts/eval/golden-set.ts` | 21 golden questions, merged into inventory items where they match |
| `cklb-samples/red_hat_enterprise_linux_9.cklb` | Real RHEL 9 rule ids for synthetic finding sets |

## Things to know

- `apps/web/scripts/verify-eval.ts` defaults to `https://stigviewer-mcp.vercel.app`, `API_TEST_TOKEN` and `EVAL_MODEL=claude-sonnet-5`. The profile uses the same model, so a demand-bank run and the golden run grade the same model.
- Real demand is in `api_access_logs.mcp_intent`. Importing it needs a named approval, and the test orgs in `evidence_exclusions` are dropped, because this harness's own runs land there.
- The server does not set `isError` on typed absences, so MCPJam's `noToolErrors` passes them. The probe checks for the explained-absence markers instead.
- WBS, RASCI and minimum-roles have REST routes (`/api/v1/stigs/{slug}/wbs`, `/rasci`, `/roles/minimum`) that no MCP tool reaches. `stigviewer_plan_work` covers similar ground for a user's own findings.
- The marketing doc's customer-language section is marked thin and carries a standing rule against invented quotes. Every pain-point line in it still needs checking against CAB and survey sources.
- Inventory inputs IN-1 to IN-6 are customer artifacts, such as scan exports and system scope. Until real ones arrive, questions that need them run only as generated children with synthetic inputs.
