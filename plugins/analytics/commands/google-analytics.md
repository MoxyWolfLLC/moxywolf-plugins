---
description: Run a read-only Google Analytics 4 report (generic or Lens-Test campaign reports) via the GA4 Data API.
argument-hint: '[overview | pages | sources | acquisition | signup-source | segment | scoreboard | daily | realtime | custom] [--days N] [--save PATH]'
allowed-tools: [Bash, Read, Write]
---

# /analytics:google-analytics — query GA4 (read-only)

Run a GA4 report with the source script. Credentials come from the environment
(`GOOGLE_APPLICATION_CREDENTIALS`, `GA4_PROPERTY_ID`) — see the `google-analytics`
skill and the `ga4-reporting-setup-runbook` for provisioning.

This is the Google Analytics source in the `analytics` plugin; other sources
(Clarity, Ahrefs, PostHog) are added as their own commands alongside this one.

## Steps

1. Confirm env config is present: `GOOGLE_APPLICATION_CREDENTIALS` points at a
   readable JSON key and `GA4_PROPERTY_ID` is set. If not, stop and point the user
   at the runbook (`_Shared Knowledge/Agents and Plugins/ga4-reporting-setup-runbook`).
2. Ensure the dependency: `pip install google-analytics-data --break-system-packages` (idempotent).
3. Run the requested report:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/google-analytics/ga_query.py" --report <type> [--days N] [--output md] [--save PATH]
   ```

   Default to `--report overview` if the user didn't specify one. For the campaign
   Friday read, use `--report scoreboard --days 7 --save lens-test-ga4-scoreboard-<date>.md`.
4. Present the result. For `scoreboard`, the script writes a markdown file — share it.

## Notes

- Read-only. The script cannot change GA4 settings.
- GA4 covers acquisition; the Lens-Test conversion verdict is in PostHog.
- The `segment` and per-segment `scoreboard` need a registered GA4 custom dimension
  (`--segment customUser:user_type` for RPO vs non-RPO).
- Never echo or commit the service-account key.
