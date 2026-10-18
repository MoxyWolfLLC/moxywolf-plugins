---
description: Put a typed question to the decider council (three decision models, majority wins) and get each voice, the majority and a ledger receipt
allowed-tools: Bash, Read
argument-hint: <question> [--choices a,b,c | --levels low,medium,high] [--input <file>] [--ref <id>]
---

Ask the decider council (DC-001). Three decision models from three vendors answer one typed question about one input, on the AI Gateway's `/v1/decisions` wire; the majority answers; a tie comes back as a tie. This is the hand-run form of `scripts/decider_council.py`, which plugins call by path.

Parse `$ARGUMENTS`:
- the question is everything that is not a flag;
- `--choices a,b,c` makes it a `choice` question (1 to 255 values); `--levels low,medium,high` makes it a `score` question (2 to 10 ordered levels); neither makes it a `predicate` (yes or no, answered as a probability);
- `--input <file>` is the thing under decision; without it, ask the user to paste it, or use the question itself as the input when it is self-contained;
- `--ref <id>` labels the ledger line (default: `hand`).

Build the questions JSON and run, from the council plugin root:

```bash
Q='[{"type":"predicate","name":"q1","instructions":"<the question>"}]'          # or choice / score as above
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/decider_council.py" ask --caller decide --ref <id> --input <file or -> --questions "$Q"
```

The gateway is reachable from the macOS shell; the Cowork device VM's proxy refuses it (probe of 2026-10-18), so in Cowork run it through Desktop Commander or report that the wire is unreachable from this shell. The key resolves from `AI_GATEWAY_API_KEY`, then the file `GSTACK_AIGATEWAY_ENV` names, then the vault's `aigateway.env` the way `jev_route.py` finds it.

Present the result as one table: a row per voice (model, its answer, latency, cost, or `unavailable` with the reason), then the majority, whether the voices agreed, and whether it is a tie. Quote the ledger line id and path from the output; a person who later learns how the decision turned out records it with `decider_council.py outcome --line <id> --result '<json>'`. Never map the answer to an action here: that is the caller's rule, in code.
