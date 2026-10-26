# mcp-eval traps (mcpevals 0.1.10)

Each of these was reproduced in this plugin's test environment.

1. **MCP SDK 2.x breaks it.** Its dependency `mcp-agent` imports `mcp.server.fastmcp`, which SDK 2.x renamed to `MCPServer`. Install `"mcpevals==0.1.10" "mcp<2"`.
2. **Unknown evaluator names are dropped without an error.** A misspelled evaluator means a check that never runs, and the case still passes. `run_mcpeval.py --check` counts evaluators in the YAML against what loaded, and fails on any difference.
3. **Inline `agent_spec` in a dataset is ignored**, even though the upstream example dataset uses one. Declare the agent once as `default_agent` in `mcpeval.yaml`.
4. **Case-insensitive regex lowercases the pattern**, which turns `\S` into `\s` and `\D` into `\d`. The exporter writes `case_sensitive: true` with a leading `(?i)`.
5. **The report keeps only a tool-call count**, not the names. The exporter adds a `ToolSequence` recorder (or `FirstToolIn`) to every case, so the names reach the report.
6. **`to_dict()` leaves evaluator results as pydantic objects.** `json.dump(default=str)` turns them into strings and drops `details`. `run_mcpeval.py` serializes them with `model_dump`.
7. **Custom evaluators must be registered before the dataset loads.** `run_mcpeval.py` imports `mcpeval_evaluators` first.
