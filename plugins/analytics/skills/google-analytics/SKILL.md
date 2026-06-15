---
name: google-analytics
description: Query Google Analytics 4 (GA4) data, read-only, via the GA4 Data API and a service account. Use when the user asks about website traffic, page views, sessions, users, conversions, top pages, traffic sources, acquisition channels, signup source, or campaign acquisition reads (e.g. the Lens Test Friday scoreboard). Trigger on "analytics", "GA4", "traffic", "visitors", "page views", "sessions", "bounce rate", "conversions", "top pages", "referrals", "acquisition", "signup source", "scoreboard".
---

# Google Analytics 4 Skill

Query a GA4 property with the Data API v1 (read-only). The script never changes GA4 config.

## Setup (read this first)

Credentials and property ID come from the **environment**, never hardcoded:

- `GOOGLE_APPLICATION_CREDENTIALS` — absolute path to the service-account JSON key.
- `GA4_PROPERTY_ID` — the numeric property ID (e.g. `363186564`), not `properties/363186564`.

Both can be overridden per call with `--credentials` and `--property`. The Python
dependency is `google-analytics-data` (`pip install google-analytics-data --break-system-packages`).

Full provisioning steps (GCP project, enable the Data API, create the service
account, grant it Viewer on the property, find the property ID) are in the
runbook: `ga4-reporting-setup-runbook` in the MoxyWolf Vault `_Shared Knowledge/Agents and Plugins/`
and STIGViewer `06 – Engineering/`.

**Cowork sandbox caveat:** this needs (a) the key file readable by the runner and
(b) network reach to `analyticsdata.googleapis.com`. If the sandbox can't do both,
run the script on a host. Never commit the key or place it in the Drive-synced vault.

## How to use

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/google-analytics/ga_query.py" --report <report_type> [options]
```

## Generic reports

| Report | What it returns |
|---|---|
| `overview` | totals: users, new users, sessions, views, avg session duration, engagement, bounce |
| `pages` | top pages by views (path, title, views, users, engagement time) |
| `sources` | traffic sources (source/medium, sessions, users, conversions) |
| `countries` | geographic breakdown |
| `devices` | desktop/mobile/tablet split |
| `daily` | day-by-day trend |
| `realtime` | active users in the last 30 minutes |
| `custom` | pass `--metrics` and `--dimensions` (comma-separated GA4 API names) |

## Lens-Test campaign reports

| Report | What it returns |
|---|---|
| `acquisition` | sessions/users/conversions by **default channel group** — slide 12's "visits by source" |
| `signup-source` | first-touch acquisition by `firstUserSource`/`firstUserMedium` — where signups originate |
| `segment` | conversion split by a GA4 **custom dimension** (`--segment customUser:user_type`) — e.g. RPO vs non-RPO. Requires the custom dimension to be registered in GA4 Admin first |
| `scoreboard` | one markdown doc: acquisition by channel + first-touch signup source + week-over-week totals. The Friday read. Pair with `--save` and a scheduled task |

The conversion verdict (`pricing_modal_view` → `pricing_modal_upgrade_complete`,
RPO vs non-RPO) lives in **PostHog**, not GA4. GA4 is the acquisition end only.

## Options

| Option | Default | Description |
|---|---|---|
| `--days` | 30 (7 for scoreboard) | lookback window |
| `--start` / `--end` | — | explicit YYYY-MM-DD range (overrides `--days`) |
| `--limit` | 10 | max rows |
| `--output` | table | `table`, `json`, `csv`, or `md` |
| `--segment` | — | GA4 custom-dimension API name (segment / scoreboard) |
| `--metrics` / `--dimensions` | — | for `custom` |
| `--property` / `--credentials` | env | override the env config |
| `--save <path>` | — | write the report to a file instead of stdout |

## Examples

```bash
# Friday scoreboard, last 7 days, written to a dated file
python "${CLAUDE_PLUGIN_ROOT}/scripts/google-analytics/ga_query.py" --report scoreboard --days 7 \
  --save "lens-test-ga4-scoreboard-$(date +%F).md"

# Acquisition by channel, last 14 days, markdown
python "${CLAUDE_PLUGIN_ROOT}/scripts/google-analytics/ga_query.py" --report acquisition --days 14 --output md

# Where signups came from, last 30 days
python "${CLAUDE_PLUGIN_ROOT}/scripts/google-analytics/ga_query.py" --report signup-source --days 30
```

## GA4 reference (for custom queries)

**Metrics:** totalUsers, newUsers, activeUsers, sessions, screenPageViews,
averageSessionDuration, bounceRate, engagementRate, conversions, eventCount.

**Dimensions:** date, pagePath, pageTitle, sessionSource, sessionMedium,
sessionDefaultChannelGroup, firstUserSource, firstUserMedium, country, city,
deviceCategory, browser, landingPage.

## Troubleshooting

- `ModuleNotFoundError: google` → `pip install google-analytics-data --break-system-packages`.
- `403 / PERMISSION_DENIED` → the service account isn't a Viewer on the property (runbook step).
- credentials not found → check `GOOGLE_APPLICATION_CREDENTIALS` path.
- `API not enabled` → enable the Google Analytics Data API in the GCP project.
- `property not found` → use the numeric ID only.
