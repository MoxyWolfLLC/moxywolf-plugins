#!/usr/bin/env python3
"""
Google Analytics 4 Data API query tool (MoxyWolf google-analytics plugin).

Read-only GA4 reporting via a service account. Credentials and property ID are
read from the environment (never hardcoded), so the same script is safe to run
in the Cowork sandbox, on a host, or from a scheduled task.

Configuration (environment variables):
  GOOGLE_APPLICATION_CREDENTIALS  Absolute path to the service-account JSON key.
  GA4_PROPERTY_ID                 Numeric GA4 property ID (e.g. 363186564).

Both can be overridden per-invocation with --credentials and --property.

Originated from Anthony Lee's "Google Analytics as a Claude Code skill" walkthrough;
adapted for MoxyWolf: env-based credentials, campaign reports, and --save.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta


# ----------------------------------------------------------------------------
# Configuration — resolved from the environment, with CLI overrides.
# ----------------------------------------------------------------------------
def resolve_config(args):
    cred = args.credentials or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    prop = args.property or os.environ.get("GA4_PROPERTY_ID")
    if not cred:
        sys.exit("Error: no credentials. Set GOOGLE_APPLICATION_CREDENTIALS or pass --credentials "
                 "(path to the service-account JSON key).")
    if not os.path.isfile(cred):
        sys.exit(f"Error: credentials file not found at: {cred}")
    if not prop:
        sys.exit("Error: no property. Set GA4_PROPERTY_ID or pass --property (numeric GA4 property ID).")
    prop = str(prop).replace("properties/", "").strip()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred
    return prop


def get_client():
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient()


# ----------------------------------------------------------------------------
# Request building + response formatting
# ----------------------------------------------------------------------------
def build_request(prop, metrics, dimensions, days=30, start=None, end=None,
                  limit=10, order_by_metric=None, desc=True):
    from google.analytics.data_v1beta.types import (
        RunReportRequest, Metric, Dimension, DateRange, OrderBy
    )
    end_date = end or datetime.now().strftime("%Y-%m-%d")
    start_date = start or (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    request = RunReportRequest(
        property=f"properties/{prop}",
        metrics=[Metric(name=m.strip()) for m in metrics],
        dimensions=[Dimension(name=d.strip()) for d in dimensions] if dimensions else [],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        limit=limit,
    )
    if order_by_metric:
        request.order_bys = [
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=desc)
        ]
    return request


def _rows(response):
    headers = ([h.name for h in response.dimension_headers]
               + [h.name for h in response.metric_headers])
    rows = []
    for row in response.rows:
        rows.append([dv.value for dv in row.dimension_values]
                    + [mv.value for mv in row.metric_values])
    return headers, rows


def format_response(response, output="table"):
    headers, rows = _rows(response)
    return render(headers, rows, output, getattr(response, "row_count", None))


def render(headers, rows, output="table", row_count=None):
    if output == "json":
        return json.dumps([dict(zip(headers, r)) for r in rows], indent=2)
    if output == "csv":
        return "\n".join([",".join(headers)] + [",".join(r) for r in rows])
    if output == "md":
        lines = ["| " + " | ".join(headers) + " |",
                 "| " + " | ".join("---" for _ in headers) + " |"]
        lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in rows]
        return "\n".join(lines)
    # table
    if not rows:
        return "(no rows)"
    widths = [len(h) for h in headers]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(str(v)))
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    head = "|" + "|".join(f" {h:<{widths[i]}} " for i, h in enumerate(headers)) + "|"
    out = [sep, head, sep]
    out += ["|" + "|".join(f" {str(v):<{widths[i]}} " for i, v in enumerate(r)) + "|" for r in rows]
    out.append(sep)
    if row_count:
        out.append(f"\nTotal rows: {row_count}")
    return "\n".join(out)


# ----------------------------------------------------------------------------
# Generic reports
# ----------------------------------------------------------------------------
def report_overview(client, prop, args):
    req = build_request(prop,
        metrics=["totalUsers", "newUsers", "sessions", "screenPageViews",
                 "averageSessionDuration", "engagementRate", "bounceRate"],
        dimensions=[], days=args.days, start=args.start, end=args.end, limit=1)
    return format_response(client.run_report(req), args.output)


def report_pages(client, prop, args):
    req = build_request(prop,
        metrics=["screenPageViews", "totalUsers", "averageSessionDuration"],
        dimensions=["pagePath", "pageTitle"], days=args.days, start=args.start,
        end=args.end, limit=args.limit, order_by_metric="screenPageViews")
    return format_response(client.run_report(req), args.output)


def report_sources(client, prop, args):
    req = build_request(prop,
        metrics=["sessions", "totalUsers", "engagementRate", "conversions"],
        dimensions=["sessionSource", "sessionMedium"], days=args.days, start=args.start,
        end=args.end, limit=args.limit, order_by_metric="sessions")
    return format_response(client.run_report(req), args.output)


def report_countries(client, prop, args):
    req = build_request(prop,
        metrics=["sessions", "totalUsers", "engagementRate"],
        dimensions=["country"], days=args.days, start=args.start, end=args.end,
        limit=args.limit, order_by_metric="sessions")
    return format_response(client.run_report(req), args.output)


def report_devices(client, prop, args):
    req = build_request(prop,
        metrics=["sessions", "totalUsers", "engagementRate"],
        dimensions=["deviceCategory"], days=args.days, start=args.start, end=args.end,
        limit=args.limit, order_by_metric="sessions")
    return format_response(client.run_report(req), args.output)


def report_daily(client, prop, args):
    from google.analytics.data_v1beta.types import OrderBy
    req = build_request(prop,
        metrics=["totalUsers", "sessions", "screenPageViews"],
        dimensions=["date"], days=args.days, start=args.start, end=args.end,
        limit=args.days or 30)
    req.order_bys = [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"), desc=False)]
    return format_response(client.run_report(req), args.output)


def report_realtime(client, prop, args):
    from google.analytics.data_v1beta.types import (
        RunRealtimeReportRequest, Metric, Dimension)
    req = RunRealtimeReportRequest(
        property=f"properties/{prop}",
        metrics=[Metric(name="activeUsers")],
        dimensions=[Dimension(name="unifiedScreenName")],
        limit=args.limit)
    resp = client.run_realtime_report(req)
    headers, rows = _rows(resp)
    if not rows:
        return "No active users right now."
    return render(headers, rows, args.output)


def report_custom(client, prop, args):
    if not args.metrics:
        return "Error: --metrics required for custom report (comma-separated)"
    metrics = [m.strip() for m in args.metrics.split(",")]
    dimensions = [d.strip() for d in args.dimensions.split(",")] if args.dimensions else []
    req = build_request(prop, metrics=metrics, dimensions=dimensions, days=args.days,
        start=args.start, end=args.end, limit=args.limit, order_by_metric=metrics[0])
    return format_response(client.run_report(req), args.output)


# ----------------------------------------------------------------------------
# Lens-Test campaign reports
# ----------------------------------------------------------------------------
def report_acquisition(client, prop, args):
    """Acquisition by default channel group — the campaign's 'visits by source' read."""
    req = build_request(prop,
        metrics=["sessions", "totalUsers", "newUsers", "engagementRate", "conversions"],
        dimensions=["sessionDefaultChannelGroup"], days=args.days, start=args.start,
        end=args.end, limit=args.limit, order_by_metric="sessions")
    return format_response(client.run_report(req), args.output)


def report_signup_source(client, prop, args):
    """First-touch acquisition: where users that signed up first came from.

    Maps to slide 12's 'visits by signup source'. Uses first-user attribution.
    """
    req = build_request(prop,
        metrics=["newUsers", "totalUsers", "conversions", "engagementRate"],
        dimensions=["firstUserSource", "firstUserMedium"], days=args.days, start=args.start,
        end=args.end, limit=args.limit, order_by_metric="newUsers")
    return format_response(client.run_report(req), args.output)


def report_segment(client, prop, args):
    """Conversion split by a GA4 custom dimension (e.g. RPO vs non-RPO).

    Requires a registered GA4 custom dimension. Pass its API name with --segment,
    e.g. --segment customUser:user_type  (RPO vs non-RPO must be set as a
    user-scoped custom dimension in GA4 first; otherwise this errors).
    """
    if not args.segment:
        return ("Error: --segment <customDimensionApiName> required (e.g. customUser:user_type). "
                "The dimension must already be registered in GA4 Admin.")
    req = build_request(prop,
        metrics=["totalUsers", "newUsers", "conversions", "engagementRate"],
        dimensions=[args.segment], days=args.days, start=args.start, end=args.end,
        limit=args.limit, order_by_metric="newUsers")
    return format_response(client.run_report(req), args.output)


def report_scoreboard(client, prop, args):
    """The Friday read: a single markdown scoreboard for the Lens Test campaign.

    Acquisition by channel + first-touch signup source, current window vs the
    prior equal-length window (week-over-week by default).
    """
    days = args.days or 7
    today = datetime.now()
    cur_end = today.strftime("%Y-%m-%d")
    cur_start = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    prev_end = (today - timedelta(days=days + 1)).strftime("%Y-%m-%d")
    prev_start = (today - timedelta(days=2 * days)).strftime("%Y-%m-%d")

    def run(metrics, dims, start, end, order, limit=25):
        req = build_request(prop, metrics=metrics, dimensions=dims, start=start, end=end,
                            limit=limit, order_by_metric=order)
        return _rows(client.run_report(req))

    parts = [f"# Lens Test — GA4 Scoreboard ({cur_start} to {cur_end})",
             f"_Generated {today.strftime('%Y-%m-%d %H:%M')} · property {prop} · "
             f"prior window {prev_start} to {prev_end}_",
             "",
             "> GA4 covers the acquisition end only. The conversion verdict "
             "(pricing_modal_view to pricing_modal_upgrade_complete) lives in PostHog.",
             ""]

    h, r = run(["sessions", "totalUsers", "newUsers", "conversions"],
               ["sessionDefaultChannelGroup"], cur_start, cur_end, "sessions")
    parts += ["## Acquisition by channel (current window)", "", render(h, r, "md"), ""]

    h, r = run(["newUsers", "totalUsers", "conversions"],
               ["firstUserSource", "firstUserMedium"], cur_start, cur_end, "newUsers")
    parts += ["## First-touch signup source (current window)", "", render(h, r, "md"), ""]

    hp, rp = run(["sessions", "totalUsers", "newUsers"], [], prev_start, prev_end, "sessions", limit=1)
    hc, rc = run(["sessions", "totalUsers", "newUsers"], [], cur_start, cur_end, "sessions", limit=1)
    wow_headers = ["window", "sessions", "totalUsers", "newUsers"]
    wow_rows = [["prior"] + (rp[0] if rp else ["0", "0", "0"]),
                ["current"] + (rc[0] if rc else ["0", "0", "0"])]
    parts += ["## Week-over-week totals", "", render(wow_headers, wow_rows, "md"), ""]

    if args.segment:
        h, r = run(["newUsers", "totalUsers", "conversions"], [args.segment],
                   cur_start, cur_end, "newUsers")
        parts += [f"## Segment: {args.segment} (current window)", "", render(h, r, "md"), ""]

    return "\n".join(parts)


REPORTS = {
    "overview": report_overview,
    "pages": report_pages,
    "sources": report_sources,
    "countries": report_countries,
    "devices": report_devices,
    "daily": report_daily,
    "realtime": report_realtime,
    "custom": report_custom,
    # Lens Test
    "acquisition": report_acquisition,
    "signup-source": report_signup_source,
    "segment": report_segment,
    "scoreboard": report_scoreboard,
}


def main():
    p = argparse.ArgumentParser(description="Query Google Analytics 4 data (read-only).")
    p.add_argument("--report", required=True, choices=REPORTS.keys(), help="Report type")
    p.add_argument("--days", type=int, default=30, help="Lookback period in days (default: 30)")
    p.add_argument("--start", help="Start date YYYY-MM-DD (overrides --days)")
    p.add_argument("--end", help="End date YYYY-MM-DD (defaults to today)")
    p.add_argument("--limit", type=int, default=10, help="Max rows (default: 10)")
    p.add_argument("--output", choices=["table", "json", "csv", "md"], default="table",
                   help="Output format")
    p.add_argument("--metrics", help="Comma-separated metrics (custom report)")
    p.add_argument("--dimensions", help="Comma-separated dimensions (custom report)")
    p.add_argument("--segment", help="GA4 custom dimension API name for segment/scoreboard "
                                     "(e.g. customUser:user_type)")
    p.add_argument("--property", help="GA4 property ID (overrides GA4_PROPERTY_ID env)")
    p.add_argument("--credentials", help="Path to service-account JSON (overrides env)")
    p.add_argument("--save", help="Write output to this file path instead of stdout")
    args = p.parse_args()

    prop = resolve_config(args)
    try:
        client = get_client()
        result = REPORTS[args.report](client, prop, args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(result + "\n")
        print(f"Saved {args.report} report to {args.save}")
    else:
        print(result)


if __name__ == "__main__":
    main()
