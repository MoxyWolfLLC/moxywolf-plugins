---
description: Build or refresh the question bank from persona docs, question inventories, in-repo golden sets, and (after release approval) real usage logs.
argument-hint: '[personas | inventory | golden | evidence | approve-release] ...'
allowed-tools: [Bash, Read, Write]
---

# /mcp-demand-harness:demand-seed

Seeds come from sources that already exist. Do not write questions here; drafting belongs in `demand-expand`.

Order for a new bank:

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"; PR=<profile>; B=<repo>/<bank_dir>/demand-bank.json
python3 $S/seed.py --profile $PR personas  --bank $B --doc <persona doc> --doc-ref <repo-relative path>
python3 $S/seed.py --profile $PR inventory --bank $B --doc <inventory doc> --doc-ref <path> --doc-date YYYY-MM-DD
node    $S/golden_to_json.mjs <repo> <golden-set.ts> <cache>/golden-set.json   # needs the typescript package
python3 $S/seed.py --profile $PR golden    --bank $B --json <cache>/golden-set.json --ref <golden-set.ts>
python3 $S/bank.py validate --bank $B --capability-map <capability-map.json>
```

## Real usage (evidence)

This is the only source that shows real demand, so it is worth the gate.

1. A named person approves pulling the rows. For STIGViewer, that means `api_access_logs` (`mcp_intent`, tool, timestamp, org) from Supabase. Pull them into a local CSV. Do not paste the rows into chat.
2. Import. The profile's `evidence_exclusions` drops test-org traffic, which includes this harness's own runs:

   ```bash
   python3 $S/seed.py --profile $PR evidence --bank $B --file rows.csv --source-name api_access_logs \
     --class observed --text-col mcp_intent --date-col created_at --org-col org_name --id-col id
   ```

3. A person reads each imported question, because redaction misses names and free-text identifiers. Then they release the ones they read:

   ```bash
   python3 $S/seed.py --profile $PR approve-release --bank $B --approver "First Last" --ids Q-0101 Q-0102
   ```

Exports refuse to run while any `observed` question is unreleased.
