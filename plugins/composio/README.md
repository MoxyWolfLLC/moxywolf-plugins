# composio

Composio integration for Cowork. Composio's Tool Router gives Claude access to 1000+ app toolkits — Notion, Linear, Jira, HubSpot, Salesforce, Stripe, Airtable, Calendly, and many more — through a single session-based MCP connector.

## What this plugin is

- `composio-tools` skill — teaches Claude how to use Composio: the meta-tool discover/authenticate/execute loop, sessions, the workbench, and when to use Composio versus a native MCP.
- `/composio-setup` command — a guided walkthrough for installing the Composio connector in Cowork.

The plugin does not bundle an MCP server. Composio's MCP endpoint is org-specific (a URL plus an API key) and cannot be hardcoded in a marketplace plugin — the connector is added once at the Cowork level via `/composio-setup`.

## When to use Composio

Native MCP connectors first — GitHub, Gmail, Calendar, Slack, Drive, Supabase. Composio is the breadth layer for apps with no native connector.

## History

Composio's old gateway, Rube, was retired in May 2026 (`MIGRATION-rube-deprecation.md`). That migration deliberately replaced a single gateway with native MCPs. Composio re-enters here as an additive reach layer, not a gateway the other plugins route through. The eight former Rube-era plugins each carry a short "Composio fallback" note pointing here for apps their native connectors do not cover — see `MIGRATION-composio-integration.md`.

## Related

- `composio-connector-setup.md` in the MoxyWolf Vault (`_Shared Knowledge/Agents and Plugins/`) — canonical connector setup reference.
- `GitHub/composio-agent/` — a standalone Claude Agent SDK + Composio program (a runnable app, not a plugin).
