#!/usr/bin/env python3
"""
discourse_sweep.py — 30-day discourse sweep planner and ranker.

This script does deterministic file I/O for the Discernment phase of the 4D
Blog Engine. It does NOT make network requests itself. Instead it operates in
two modes:

  --plan      Generate a JSON plan of queries the skill will dispatch via
              WebSearch / Apify / Council. The skill executes; this script
              defines what gets executed.

  --rank      Rank a harvested findings file (JSON, written by the skill from
              the search results) using relevance×0.6 + recency×0.4 with
              banded recency, dedupe via 70% title-overlap, +0.1 source-
              diversity bonus, and cross-source clustering. Outputs a ranked
              discourse.md and a discourse.json sidecar.

Boundary: the orchestrator agent does the search; the script does the math.
Per agricidaniel/claude-blog discipline.

Usage:
  python3 discourse_sweep.py --plan \\
      --topic "polish bias in AI content production" \\
      --outline 02-description.md \\
      --days 30 \\
      --out 03-discernment/sweep-plan.json

  python3 discourse_sweep.py --rank \\
      --findings 03-discernment/sweep-findings.json \\
      --topic "polish bias in AI content production" \\
      --out 03-discernment/discourse.md
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

# Platform list — locked in per sign-off (includes Facebook + Quora).
PLATFORMS: list[tuple[str, str]] = [
    ("reddit", "site:reddit.com"),
    ("x", "site:x.com OR site:twitter.com"),
    ("hn", "site:news.ycombinator.com"),
    ("substack", "site:substack.com"),
    ("devto", "site:dev.to"),
    ("github", "site:github.com"),
    ("linkedin", "site:linkedin.com/pulse"),
    ("facebook", "site:facebook.com"),
    ("quora", "site:quora.com"),
]

# Podcast and academic platforms are handled separately by the skill
# (Apify actors for podcasts; research-pipeline/literature-discovery for
# academic). Listed here so the plan file documents the full sweep.
EXTERNAL_PLATFORMS: list[str] = ["podcasts_apify", "academic_research_pipeline"]


def make_plan(topic: str, outline_path: Path | None, days: int) -> dict[str, Any]:
    """Generate the per-platform query plan for the skill to execute."""
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    queries: list[dict[str, str]] = []

    # Primary topic queries across all web platforms.
    for platform_id, site_op in PLATFORMS:
        queries.append(
            {
                "platform": platform_id,
                "query": f"{topic} {site_op} after:{since}",
                "executor": "WebSearch",
            }
        )

    # Per-outline-section evidence queries, if an outline was supplied.
    section_terms: list[str] = []
    if outline_path and outline_path.exists():
        text = outline_path.read_text(encoding="utf-8", errors="replace")
        # crude H2 extraction; the outline file uses standard markdown headers.
        section_terms = re.findall(r"^##\s+(.+?)$", text, flags=re.MULTILINE)

    for section in section_terms:
        for platform_id, site_op in PLATFORMS:
            queries.append(
                {
                    "platform": platform_id,
                    "section": section.strip(),
                    "query": f"{section} {site_op} after:{since}",
                    "executor": "WebSearch",
                }
            )

    return {
        "topic": topic,
        "outline_sections": section_terms,
        "days": days,
        "since": since,
        "queries": queries,
        "external_platforms": EXTERNAL_PLATFORMS,
        "platform_count": len(PLATFORMS) + len(EXTERNAL_PLATFORMS),
        "query_count": len(queries),
        "_meta": {
            "schema": "4d-blog-engine.discourse_sweep.plan.v1",
            "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    }


def _band_recency(days_old: int | None) -> float:
    """Bound recency to a recency score in [0.2, 1.0]."""
    if days_old is None:
        return 0.2
    if days_old <= 7:
        return 1.0
    if days_old <= 14:
        return 0.7
    if days_old <= 30:
        return 0.4
    return 0.2


def _title_tokens(title: str) -> set[str]:
    """Lowercase alphanumeric word set, > 3 chars, for dedupe overlap."""
    return {w for w in re.findall(r"[A-Za-z0-9']+", title.lower()) if len(w) > 3}


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a), len(b))


def rank_findings(findings: list[dict[str, Any]], topic: str) -> dict[str, Any]:
    """
    Rank, dedupe, cluster. Each finding must have at minimum:
        title, url, summary, source_type, platform, published_at (ISO date)
    Optional:
        relevance (float 0-1; if absent, computed from title overlap with topic)
    """
    today = datetime.date.today()
    topic_tokens = _title_tokens(topic)

    enriched: list[dict[str, Any]] = []
    for f in findings:
        title = f.get("title") or ""
        url = f.get("url") or ""
        pub = f.get("published_at")
        days_old: int | None = None
        if pub:
            try:
                d = datetime.date.fromisoformat(pub[:10])
                days_old = (today - d).days
            except ValueError:
                pass

        relevance = f.get("relevance")
        if relevance is None:
            relevance = round(_overlap(_title_tokens(title), topic_tokens), 3)
        recency = _band_recency(days_old)
        combined = round(relevance * 0.6 + recency * 0.4, 3)

        enriched.append(
            {
                **f,
                "title_tokens": sorted(_title_tokens(title)),
                "days_old": days_old,
                "relevance_score": relevance,
                "recency_score": recency,
                "combined_score": combined,
            }
        )

    # Dedupe via 70% title-overlap. Keep highest combined score in each cluster.
    enriched.sort(key=lambda r: r["combined_score"], reverse=True)
    clusters: list[list[dict[str, Any]]] = []
    for item in enriched:
        item_tokens = set(item["title_tokens"])
        placed = False
        for cluster in clusters:
            cluster_head_tokens = set(cluster[0]["title_tokens"])
            if _overlap(item_tokens, cluster_head_tokens) >= 0.7:
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])

    # Source-diversity bonus: +0.1 if a cluster has findings from ≥2 platforms.
    primaries: list[dict[str, Any]] = []
    for cluster in clusters:
        head = dict(cluster[0])
        platforms = {f.get("platform", "unknown") for f in cluster}
        if len(platforms) >= 2:
            head["combined_score"] = round(head["combined_score"] + 0.1, 3)
            head["source_diversity_bonus"] = True
        head["cluster_size"] = len(cluster)
        head["alternates"] = [
            {"title": f.get("title"), "url": f.get("url"), "platform": f.get("platform")}
            for f in cluster[1:]
        ]
        primaries.append(head)
    primaries.sort(key=lambda r: r["combined_score"], reverse=True)

    return {
        "topic": topic,
        "total_findings_input": len(findings),
        "clusters_after_dedupe": len(clusters),
        "primaries": primaries,
        "_meta": {
            "schema": "4d-blog-engine.discourse_sweep.ranked.v1",
            "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    }


def render_discourse_md(ranked: dict[str, Any]) -> str:
    """Render the ranked output as a human-readable discourse.md."""
    lines: list[str] = []
    lines.append(f"# Discourse Sweep — {ranked['topic']}")
    lines.append("")
    lines.append(
        f"_Sweep of {ranked['total_findings_input']} raw findings collapsed into "
        f"{ranked['clusters_after_dedupe']} unique clusters._"
    )
    lines.append("")
    lines.append("## Top findings (ranked by combined score)")
    lines.append("")
    for i, p in enumerate(ranked["primaries"], 1):
        title = p.get("title", "(untitled)")
        url = p.get("url", "")
        platform = p.get("platform", "unknown")
        score = p.get("combined_score", 0.0)
        summary = p.get("summary", "").strip()
        days = p.get("days_old")
        bonus = " (+diversity bonus)" if p.get("source_diversity_bonus") else ""
        days_str = f"{days}d ago" if days is not None else "undated"
        lines.append(f"### {i}. [{title}]({url})")
        lines.append("")
        lines.append(
            f"**Platform:** {platform} · **Recency:** {days_str} · "
            f"**Score:** {score}{bonus} · **Cluster size:** {p.get('cluster_size', 1)}"
        )
        lines.append("")
        if summary:
            lines.append(summary)
            lines.append("")
        if p.get("alternates"):
            lines.append("**Also surfaced (cluster paraphrases):**")
            for alt in p["alternates"]:
                lines.append(
                    f"- [{alt['title']}]({alt['url']}) ({alt['platform']})"
                )
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="30-day discourse sweep planner/ranker.")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_plan = sub.add_parser("plan", help="Generate sweep plan JSON.")
    p_plan.add_argument("--topic", required=True)
    p_plan.add_argument("--outline", type=Path, default=None)
    p_plan.add_argument("--days", type=int, default=30)
    p_plan.add_argument("--out", type=Path, required=True)

    p_rank = sub.add_parser("rank", help="Rank harvested findings into discourse.md.")
    p_rank.add_argument("--findings", type=Path, required=True)
    p_rank.add_argument("--topic", required=True)
    p_rank.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()

    if args.mode == "plan":
        plan = make_plan(args.topic, args.outline, args.days)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        print(
            f"STATUS=plan_written QUERIES={plan['query_count']} "
            f"PLATFORMS={plan['platform_count']} OUT={args.out}"
        )
        return 0

    if args.mode == "rank":
        findings_raw = args.findings.read_text(encoding="utf-8")
        findings = json.loads(findings_raw)
        if isinstance(findings, dict) and "findings" in findings:
            findings = findings["findings"]
        ranked = rank_findings(findings, args.topic)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_discourse_md(ranked), encoding="utf-8")
        sidecar = args.out.with_suffix(".json")
        sidecar.write_text(json.dumps(ranked, indent=2), encoding="utf-8")
        print(
            f"STATUS=ranked CLUSTERS={ranked['clusters_after_dedupe']} "
            f"OUT={args.out} SIDECAR={sidecar}"
        )
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
