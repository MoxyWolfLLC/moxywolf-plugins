---
description: Set up the Composio MCP connector in Cowork — retire the old Rube connector, create a Composio Tool Router URL, and add it as a custom connector.
---

Walk the user through installing the Composio connector in Cowork. This is a one-time setup. Most steps are actions the user takes in the Cowork and Composio UIs, so guide them one step at a time and confirm each before moving on.

## Step 1 — Retire the old Rube connector

Rube was Composio's previous gateway and is dead. If a connector named Rube — or a server exposing `RUBE_*` tools — is still connected, have the user remove it: Cowork → Settings → Connectors → select the Rube server → disconnect. This is a manual UI action; there is no tool that disconnects a connector.

## Step 2 — Create a Composio MCP server URL

In the Composio dashboard (https://dashboard.composio.dev), open the Connect / Clients section. Create an MCP server config and choose which toolkits it exposes. Composio returns a hosted MCP server URL of the form `https://backend.composio.dev/v3/mcp/<SERVER_ID>?user_id=<USER_ID>`, authenticated with an `x-api-key` header carrying the Composio API key.

Composio publishes a Cowork-specific walkthrough — "How to better your Claude Cowork experience with MCPs" — point the user there for the current exact flow.

## Step 3 — Add it as a Cowork connector

For team-wide use on a Team or Enterprise plan, an Owner adds it once: Organization settings → Connectors → Add, pasting the Composio MCP server URL. Members then enable it individually and connect their own app accounts. Solo or personal: Settings → Connectors → Add custom connector.

Auth note: if the connector dialog exposes a header field, set `x-api-key: <COMPOSIO_API_KEY>`. If it does not, use the OAuth-enabled option from the Composio dashboard's Clients flow.

## Step 4 — Confirm

Once the connector is added, Composio's meta-tools (`COMPOSIO_SEARCH_TOOLS`, `COMPOSIO_MANAGE_CONNECTIONS`) are available. The `composio-tools` skill covers how to use them.

The canonical reference is `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/composio-connector-setup.md` — keep that as the source of truth. This command is the in-Cowork guided version.
