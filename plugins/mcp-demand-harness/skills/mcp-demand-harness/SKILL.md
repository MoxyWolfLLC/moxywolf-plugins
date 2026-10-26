---
name: mcp-demand-harness
description: Work out what a product's customers will ask its MCP server and REST/API gateway, and turn that into tests. Use when the user wants to know what end users or the ICP will ask an MCP server or API, wants an eval or question bank for an MCP server, wants MCPJam or mcp-eval test suites generated from a repo, or wants eval results turned into a gap report. Trigger on "MCP evals", "what will users ask", "question bank", "MCPJam", "mcp-eval", "API gateway tests", "ICP questions", "discovery pass", "golden set".
risk_tier: side-effectful-gated
---

# MCP demand harness

The bank (`demand-bank.json`) is the only file anyone edits. MCPJam suites, mcp-eval datasets and probe plans are generated from it. If someone edits one of them by hand, the next export throws the edit away and the evidence trail stops matching.

## The loop

1. **Inventory** (`demand-inventory`). This is what the product can do today. Do it first, because every expectation is checked against it.
2. **Seed** (`demand-seed`). Pull in what already exists, strongest evidence first: real usage (released by a named person), reported questions, then persona docs, question inventories and golden sets.
3. **Report.** Run `bank.py report`. Look at persona coverage, evidence strength, blocked questions and REST-only routes. Say plainly when every question is a hypothesis. That is normal at the start, and it is the most important thing to tell the user.
4. **Expand** (`demand-expand`). Draft only where the report shows a gap. Follow `references/expansion-rules.md`.
5. **Export** (`demand-export`). Validate each output with its own tool.
6. **Run** (`demand-run`). Discovery first, then strict. Staging only, unless a named approver says otherwise.
7. **Results** (`demand-results`). Ingest the reports, present the gap report, and let the named person apply proposals.

## Evidence classes

| Class | Meaning | Who may assign it |
|---|---|---|
| observed | A real user asked this (usage logs) | `seed.py evidence` only. Needs release approval |
| reported | Someone heard a customer ask it (support, sales, CAB) | A person, with the source |
| hypothesis | Someone believes a persona would ask it | Persona docs, inventories, golden sets, Claude drafts |
| generated | A model wrote it from a parent question | Claude. Must name the parent. Capped at 3x seeds per persona |

Never present model-written text as a customer's words. If a source doc says its quotes are unvalidated, it means it.

## Discovery before strict

Discovery questions name no tools. Their job is to show what the model reaches for. A strict question pins a tool choice and has to say `why`, meaning what a failure would mean for the user. Promote a discovery question to strict only after several clean runs agree on a tool. The results step proposes this; it does not do it.

## Outcome checks for generated servers

Some servers generated from an OpenAPI spec (Stainless, Speakeasy) can expose a few generic tools, such as list endpoints, describe one, and invoke it, or a single code-execution tool, instead of one tool per endpoint. In that case, tool-name checks prove little. Use `payload` (a direct call with argument and needle checks), `rest.calls`, `must_contain` on the answer, and a rubric. Keep `first_tool_any_of` broad, or leave it out.

## References

- `references/bank-schema.md`: every field the validator knows.
- `references/mcpjam-contract.md`: MCPJam v6 suite format and what cannot be expressed in it.
- `references/mcp-eval-traps.md`: the ways mcp-eval 0.1.10 fails without telling you.
- `references/expansion-rules.md`: how to draft without polluting the evidence.
- `references/stigviewer-profile.md`: the first product profile and what the first pass found.

## Gates

See `GOVERNANCE.md`. The short version: named approvers for evidence release, draft acceptance, production runs and applying results. No approve-all. No git writes. Claude writes the commit text, and a human pushes through GitHub Desktop.
