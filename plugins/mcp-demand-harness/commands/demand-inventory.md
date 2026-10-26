---
description: Read a product repo and write its capability map (MCP tools, prompts, REST routes, and which routes no tool reaches).
argument-hint: '<repo path> --profile <profile.json> [--commit <sha>]'
allowed-tools: [Bash, Read, Write]
---

# /mcp-demand-harness:demand-inventory (read-only)

1. Find the profile. Use `${CLAUDE_PLUGIN_ROOT}/profiles/<product>.json` if it exists. If not, write a new profile modeled on `profiles/stigviewer.json`. Read the tool and route files first so the register patterns are right.
2. Record the commit you read: `git -C <repo> rev-parse --short HEAD`. This only reads the repo.
3. Run:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inventory.py" --repo <repo> --profile <profile> \
     --out <repo>/<bank_dir>/capability-map.json --commit <sha>
   ```

4. Report the tool count, the prompt count, the route count, and the REST-only routes. A REST-only route is something an API buyer can do that an MCP user cannot. Check a sample of tools against the source before trusting the map. If the count looks low, the register pattern probably missed a wrapper.
