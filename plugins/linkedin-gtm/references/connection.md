# Connecting to GTM API

The GTM API MCP server is `https://mcp.gtm-api.com/mcp` (JSON-RPC over streamable HTTP). It exposes three meta-tools: `list_toolsets`, `get_toolset_tools` (`toolset`, `verbose`) and `call_tool` (`name`, `arguments`). Every LinkedIn tool is reached through `call_tool`. Vendor docs: [docs.gtm-api.com](https://docs.gtm-api.com/llms.txt); vendor skill: [gtm-api/linkedin-mcp](https://github.com/gtm-api/linkedin-mcp/tree/master/skills/gtm-api-linkedin).

There are two ways in, and two ways this plugin uses them.

## OAuth (interactive, Claude Code and Cowork)

Add the server as a remote MCP server and sign in when prompted:

```
claude mcp add --transport http gtm-api https://mcp.gtm-api.com/mcp
```

In Cowork, add it as a custom connector with the same URL. The tools then appear as `mcp__gtm-api__call_tool` and friends.

Through OAuth, the model calls `call_tool` directly, and nothing in this plugin's scripts sits in the path. So in that mode the gate is an instruction: the skills tell the model to run outward work only through `scripts/gtm_mcp.py execute`. Use OAuth for reads and exploration. For outward work, prefer an API key so the script's checks apply.

## API key (scripts, scheduled runs)

Create a key in the GTM API dashboard (it starts `gtm_live_`). Keep it out of the repo and out of chat.

```
export GTM_API_KEY=...        # from your password manager or secret store
python3 "$P/scripts/gtm_mcp.py" toolsets
```

The client sends `Authorization: Bearer <key>` and never prints it. Only the operator's environment holds it.

## Perplexity credential proxy

In a Perplexity Computer session the key is stored as a custom credential and injected by a proxy, so the script never sees it:

```
pplx credentials run custom-cred:<credential-id>@mcp.gtm-api.com -- \
  python3 "$P/scripts/gtm_mcp.py" --proxy-auth read get_linkedin_account --args '{"sid": "ln_ac_..."}'
```

`--proxy-auth` (or `GTM_AUTH_VIA_PROXY=1`) tells the client to send no header of its own. The credential id belongs in the operator's notes, not in this repo.

## Endpoint override

`GTM_MCP_URL` or `--endpoint` points the client somewhere else (a staging server, or the local test server the tests start).

## Checking the connection without spending anything

```
python3 "$P/scripts/gtm_mcp.py" read get_linkedin_account \
  --args '{"sid": "ln_ac_0voWEjtk3uzK", "include": ["antidetect_browser", "linkedin_account_snapshot"]}'
```

`get_linkedin_account` spends no LinkedIn bucket. If it answers `unauthorized`, the key is wrong or revoked. If `included.antidetect_browser.status` is `login_issue`, the LinkedIn session is signed out and only Dorian can sign it back in through the GTM API dashboard.

## What the client refuses, whichever way you connect

Through the script: any tool not on the read list, unless it is an approved batch item run with `execute`; and every tool on the never list (mass actions, profile edits, smart-limit changes, webhooks, browser operations, custom requests, InMail, voice). Through OAuth: the same rules, held by instruction only. `GOVERNANCE.md` says which is which.
