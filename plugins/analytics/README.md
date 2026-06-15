# analytics

MoxyWolf's analytics plugin — read-only reporting across data sources, **one
command per source**. Built to grow: today it ships Google Analytics; Microsoft
Clarity, Ahrefs, PostHog, and others can be added as their own commands without
touching the existing ones.

## Sources

| Source | Command | Skill | Script |
|---|---|---|---|
| Google Analytics 4 | `/analytics:google-analytics` | `google-analytics` | `scripts/google-analytics/ga_query.py` |
| _(future)_ | — | — | `scripts/<source>/…` |

## Google Analytics command

Read-only GA4 via the Data API and a service account. Reports:

- Generic: `overview`, `pages`, `sources`, `countries`, `devices`, `daily`,
  `realtime`, `custom`.
- Lens-Test campaign: `acquisition` (by channel), `signup-source` (first-touch),
  `segment` (GA4 custom dimension, e.g. RPO vs non-RPO), `scoreboard` (one markdown
  Friday read with week-over-week).

Read-only — it cannot modify GA4 configuration.

### Configuration

Set in the environment (never hardcode, never commit the key):

- `GOOGLE_APPLICATION_CREDENTIALS` — path to the service-account JSON key.
- `GA4_PROPERTY_ID` — numeric property ID.

Dependency: `pip install google-analytics-data --break-system-packages`.

### Setup

Full provisioning (GCP project, enable Data API, service account, grant Viewer on
the property, find the property ID, Cowork-sandbox notes) is in the runbook:
`MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/ga4-reporting-setup-runbook-2026-06-14.md`
(mirror in STIGViewer `06 – Engineering/`).

### Scheduled scoreboard

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/google-analytics/ga_query.py" \
  --report scoreboard --days 7 --save "lens-test-ga4-scoreboard-$(date +%F).md"
```

Wire that into a weekly scheduled task for the Friday read.

## Adding a new source

1. Add `scripts/<source>/` with the source's script (env-based credentials).
2. Add `commands/<source>.md` → `/analytics:<source>`.
3. Add `skills/<source>/SKILL.md` for natural-language triggering.
4. Bump this plugin's version and re-register in the marketplace.

## Scope

GA4 is the acquisition end of the Lens Test funnel. The conversion verdict
(`pricing_modal_view` → `pricing_modal_upgrade_complete`, RPO vs non-RPO) lives in
PostHog. Google Analytics command adapted from Anthony Lee's "Google Analytics as
a Claude Code skill" walkthrough, re-homed with env-based credentials and campaign
reports.
