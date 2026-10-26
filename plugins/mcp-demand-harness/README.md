# mcp-demand-harness

Works out what a product's customers will ask its MCP server and REST gateway, and turns those questions into tests that MCPJam and mcp-eval can run.

The plugin does not decide what customers want. It keeps every question tied to where it came from, and it is honest about how strong that evidence is. A question a real user asked is `observed`. A question from a support ticket or a sales call is `reported`. A question someone wrote down from a persona doc is `hypothesis`. A question the model wrote is `generated`, and it always points at the question it came from.

## How it works

1. **Inventory.** Read the repo and write `capability-map.json`: MCP tools, prompts, `/api/v1` routes, and which routes no tool reaches.
2. **Seed.** Build the bank from what already exists: persona docs, question inventories, in-repo golden sets, and, after a named person approves the release, real usage logs.
3. **Expand.** Claude drafts questions for thin personas and fills in inputs for questions that need customer data. The drafts stay as drafts until a person accepts them.
4. **Export.** Write MCPJam v6 suites, mcp-eval datasets, and a probe plan. Every case carries its bank id. Anything the target format cannot express exactly is marked as approximated, never silently dropped.
5. **Run.** Discovery first, with no expected tools, to see what the model reaches for. Then strict tests. Probes call tools and REST routes directly, with no model involved.
6. **Results.** Read the reports back, sort failures into patterns, and propose changes. Nothing changes in the bank until a named person runs `apply`.

## Install

Python 3.10 or later for the scripts. They use only the standard library, except for the mcp-eval runner.

For MCPJam (v6 CLI):

```bash
npm i -g @mcpjam/cli@6        # or: npx @mcpjam/cli@6 ...
```

For mcp-eval, in its own virtual environment:

```bash
python3 -m venv .venv-mcpeval
.venv-mcpeval/bin/pip install "mcpevals==0.1.10" "mcp<2"
```

Pin `mcp<2`. mcpevals 0.1.10 does not work with MCP Python SDK 2.x.

`golden_to_json.mjs` needs the `typescript` package available to Node.

## Commands

| Command | What it does |
|---|---|
| `/mcp-demand-harness:demand-inventory` | Read a repo and write its capability map |
| `/mcp-demand-harness:demand-seed` | Build or refresh the bank from existing sources |
| `/mcp-demand-harness:demand-expand` | Draft questions for gaps and thin personas |
| `/mcp-demand-harness:demand-export` | Write MCPJam, mcp-eval, and probe files |
| `/mcp-demand-harness:demand-run` | Run discovery, strict, or probe passes against staging (gated) |
| `/mcp-demand-harness:demand-results` | Ingest reports, write the gap report, propose changes |

## Profiles

Each product gets a profile in `profiles/`. It names the tool and route files, the hosts, the auth environment variable, the models, the persona map, and the test orgs whose traffic must never count as demand. `profiles/stigviewer.json` is the first one.

## What lives where

The plugin holds the scripts and the rules. Each product repo holds its own bank and exports, in the `bank_dir` its profile names. For STIGViewer that is `apps/web/scripts/eval/demand/`, with MCPJam suites in `.mcpjam/evals/`.

See `GOVERNANCE.md` for risk tiers and who has to sign what.
