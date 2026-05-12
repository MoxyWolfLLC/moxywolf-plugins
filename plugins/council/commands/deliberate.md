---
description: Run a multi-model AI deliberation on a question
allowed-tools: Read, Write, Grep, Bash(echo:*), mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_SEARCH_TOOLS, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MULTI_EXECUTE_TOOL, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MANAGE_CONNECTIONS, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_GET_TOOL_SCHEMAS, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_WORKBENCH
argument-hint: <question to deliberate on> [--size small|medium|large] [--fast] [--deep] [--thorough] [--template <name>] [--budget 0.15]
---

Run a Council deliberation on the user's question using the deliberation-engine skill.

**Important:** The `/deliberate` command always runs the full Council pipeline. It sets `routing_decision: "explicit_command"` and skips the smart-router's Pre-Step decision. This is intentional — when a user explicitly calls `/deliberate`, they want the full multi-model experience regardless of what the router would recommend.

Parse any flags from the arguments:
- `--size small|medium|large` → 2, 4, or 6 models (default: medium)
- `--fast` → skip Stage 2 peer review, go straight from collect to synthesis
- `--deep` → MoA two-round collection — models see all Round 1 responses before responding again
- `--thorough` → add a Collective Improvement round between Stage 1 and Stage 2
- `--template <name>` → use a pre-built deliberation template (code-review, architecture, writing-critique, research-synthesis, compliance-check, business-strategy)
- `--models model1,model2,...` → override the default model lineup
- `--budget 0.15` → max cost in USD for this deliberation

The query is everything in `$ARGUMENTS` that is not a flag.

Load the deliberation-engine skill from `${CLAUDE_PLUGIN_ROOT}/skills/deliberation-engine/SKILL.md` and follow its execution steps (starting at Step 1, since Pre-Step routing is bypassed).

If this is the first deliberation in this session, verify the OpenRouter connection is active by calling `RUBE_SEARCH_TOOLS` for `OPENROUTER_CREATE_CHAT_COMPLETION`. If not connected, call `RUBE_MANAGE_CONNECTIONS` with toolkit `openrouter` and present the auth link to the user.

After the deliberation completes:
1. Present the formatted output as specified in the deliberation-engine skill (Step 7)
2. Log the outcome to pattern memory (Step 8) — requires Write tool for `council-memory.json`
3. Watch for user rating in the next 1-2 messages (Step 8c)
