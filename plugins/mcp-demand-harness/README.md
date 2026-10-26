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

## Probe response contracts and evidence

Probe runs now fail on non-2xx MCP responses, malformed/mismatched JSON-RPC replies, RPC errors, `isError` tool results and parsed application-error bodies. An unsuccessful structured envelope requires an explicit matching response contract; liveness alone cannot excuse it. Successful REST replies must have a nonempty JSON object/array without an application error. This probe targets JSON APIs; binary/CSV endpoints require a different explicit adapter and are not graded as JSON success.

A payload or REST section may declare `json_any_of`: a nonempty list of alternative branches, each a nonempty list of JSON Pointer predicates. Every predicate in one branch must pass. Predicates support `path`, `type` (`object`, `array`, `string`, `boolean`, `number`, `null`), `nonempty: true` and `equals`. Missing fields fail. Unlike legacy substring absence allowances, these structural assertions are never excused by a word appearing elsewhere in the response. Use a separate, typed absence branch with a specific reason and explanation when absence is acceptable. Empty arrays need an explicit alternative rather than being treated as useful content.

Example:
```json
{"json_any_of": [[{"path":"/workRoles","type":"array","nonempty":true}], [{"path":"/absence/reason","equals":"no_work_roles_match_filters"},{"path":"/absence/message","type":"string","nonempty":true}]]}
```

These checks apply to direct probes only, not the model answer judge. MCP predicates inspect `structuredContent.data` (or structuredContent itself), falling back to JSON in text content. REST predicates inspect the JSON response body. The report labels layers `structured`, `content`, `negative_only` or `liveness`; a green liveness layer is not proof of answer quality.

Each report records frozen plan/profile SHA-256, the bank hash declared by the plan (not an independent bank verification), local repository revisions and harness source hashes, plus the server name/version observed during initialize. A version or surface digest is not proof of a deployed git commit. Each layer retains the canonical original-response hash and up to 16384 characters of sanitized evidence with explicit redaction/truncation flags. Redaction covers known run credentials, sensitive key names, bearer tokens, GitHub tokens and JWT-shaped strings; it is best effort, not a privacy guarantee. Evidence is untrusted server content. Do not publish reports without review. Only untruncated and unredacted evidence can support exact offline regrading.

Runs refuse an existing output file and an empty executable selection before sending traffic. Use a new timestamped output path to preserve prior baselines. Preflight production approval and draft restrictions are unchanged. No production or paid evaluation runs are implied by these changes.

`results.py ingest` retains each probe layer's assertion-strength label and renders a separate coverage table. Reports produced before these labels existed are marked `unknown_legacy`; their strength is not inferred from a green verdict. A named 404/not_found denial is acceptable only through a contract branch explicitly matching `/absence/reason` and a nonempty `/absence/message`. Authentication, entitlement, rate-limit and server-error envelopes cannot borrow a success branch.
