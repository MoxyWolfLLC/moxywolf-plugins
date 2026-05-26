#!/usr/bin/env python3
"""
preflight.py — Release Owner Gate orchestrator (the 5-stage nonce-bound contract).

Implements stages from references/release-owner-rubric.md:
  Stage 1 — Capability        (no [F] / [CITATION NEEDED] in body)
  Stage 2 — Format            (frontmatter, typography rules)
  Stage 3 — Visual            (hero image present, file exists, prompt artifact)
  Stage 4 — Content Review    (BLOCKING reviewer agent output parsed + nonce verified)
  Stage 5 — Asset Integrity   (all referenced media files exist on disk)

This script does not write content. It reads:
  <piece>/04-diligence/blog.md
  <piece>/04-diligence/review.md (optional; required for Stage 4)
  <piece>/.review-nonce          (generated if absent)
and writes:
  <piece>/04-diligence/preflight-report.json
  <piece>/04-diligence/preflight-report.md

Stage 4 nonce verification: the reviewer must echo the .review-nonce verbatim
in its scorecard. If it doesn't match, this script REJECTS the review entirely
(per agricidaniel/claude-blog's nonce-bound provenance pattern), preventing
any process from faking BLOCKING:false by reproducing the format.

Exit codes:
  0 — gate passes (clean BLOCKING:false, score ≥ 90, no critical failures)
  1 — gate fails, iteration possible (round < 3)
  2 — gate fails, escalate (round 3 still failing, or structural failure)
  3 — gate fails on Stage 1-3 or Stage 5 (no need to invoke reviewer yet)

Usage:
  python3 preflight.py --piece /path/to/piece-dir --round 1
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NONCE_BYTES = 16  # 32 hex chars


# ─── Stage runners ───


def stage1_capability(blog_md: str) -> dict[str, Any]:
    """No [F] data or [CITATION NEEDED] placeholders in body."""
    findings: list[str] = []
    if "[F]" in blog_md:
        findings.append("Body contains [F] (fetch-failed) data — forbidden.")
    if "[CITATION NEEDED]" in blog_md:
        findings.append("Body contains [CITATION NEEDED] placeholders — un-resolved.")
    # Also check for "unverified" / "TBD" tells.
    for sentinel in ("TBD", "TODO:", "FIXME:"):
        if sentinel in blog_md:
            findings.append(f"Body contains '{sentinel}' — unresolved.")
    return {"stage": "capability", "passed": not findings, "findings": findings}


def stage2_format(blog_md: str) -> dict[str, Any]:
    """Frontmatter validity and typography rules."""
    findings: list[str] = []
    m = re.match(r"^---\n(.*?)\n---\n", blog_md, re.DOTALL)
    if not m:
        findings.append("Missing YAML frontmatter (--- ... ---) at top of file.")
    else:
        fm = m.group(1)
        for required in ("title:", "slug:", "date:", "author:", "excerpt:"):
            if required not in fm:
                findings.append(f"Frontmatter missing required field: {required}")
        # date must be ISO 8601
        date_m = re.search(r"date:\s*([0-9TZ:\-+\.]+)", fm)
        if date_m:
            try:
                datetime.fromisoformat(date_m.group(1).rstrip("Z"))
            except ValueError:
                findings.append(f"Frontmatter `date` is not ISO-8601: {date_m.group(1)}")
        else:
            findings.append("Frontmatter `date` missing or unparseable.")

    if "—" in blog_md:
        em_count = blog_md.count("—")
        findings.append(f"Body contains {em_count} em-dash character(s) — replace with spaced en-dash.")
    # straight quotes
    body = re.sub(r"^---\n.*?\n---\n", "", blog_md, count=1, flags=re.DOTALL)
    if '"' in body:
        findings.append("Body contains straight double-quotes; use typographer's quotes.")
    return {"stage": "format", "passed": not findings, "findings": findings}


def stage3_visual(piece: Path, blog_md: str) -> dict[str, Any]:
    """Hero image exists and prompt artifact is present."""
    findings: list[str] = []
    diligence = piece / "04-diligence"
    hero = diligence / "og-hero.png"
    prompt = diligence / "og-hero-prompt.md"
    if not hero.exists():
        findings.append(f"Hero image missing: {hero}")
    if not prompt.exists():
        findings.append(f"og-hero-prompt artifact missing: {prompt} (AI transparency requirement).")
    # heroImage frontmatter
    if "heroImage:" not in blog_md:
        findings.append("Frontmatter missing `heroImage:` field.")
    return {"stage": "visual", "passed": not findings, "findings": findings}


_NONCE_LINE = re.compile(r"^\s*NONCE:\s*([a-fA-F0-9]+)\s*$", re.MULTILINE)
_VERDICT_LINE = re.compile(
    r"^\s*BLOCKING:\s*(true|false)\s*\(([^)]*)\)\s*$", re.MULTILINE
)
_TOTAL_ROW = re.compile(
    r"\|\s*\*\*Total\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*100\*\*\s*\|"
)


def stage4_content_review(piece: Path, expected_nonce: str) -> dict[str, Any]:
    """Parse the reviewer's review.md, verify nonce, extract verdict + score."""
    review_path = piece / "04-diligence" / "review.md"
    if not review_path.exists():
        return {
            "stage": "content_review",
            "passed": False,
            "findings": [
                f"Reviewer output not yet present at {review_path}. "
                "Dispatch the BLOCKING reviewer agent before re-running."
            ],
            "score": None,
            "verdict": None,
        }
    review = review_path.read_text(encoding="utf-8")
    findings: list[str] = []

    nonce_match = _NONCE_LINE.search(review)
    if not nonce_match:
        findings.append("Reviewer output missing `NONCE: <hex>` line at the top — rejecting review entirely.")
        return {
            "stage": "content_review",
            "passed": False,
            "findings": findings,
            "score": None,
            "verdict": None,
        }
    if nonce_match.group(1).lower() != expected_nonce.lower():
        findings.append(
            f"Reviewer NONCE mismatch. Expected {expected_nonce}, got {nonce_match.group(1)}. "
            "Rejecting review entirely (nonce-bound provenance failure)."
        )
        return {
            "stage": "content_review",
            "passed": False,
            "findings": findings,
            "score": None,
            "verdict": None,
        }

    verdict_match = _VERDICT_LINE.search(review)
    if not verdict_match:
        findings.append("Reviewer output missing `BLOCKING: true|false (reason)` line.")
    blocking = verdict_match.group(1) == "true" if verdict_match else None
    blocking_reason = verdict_match.group(2).strip() if verdict_match else None

    total_match = _TOTAL_ROW.search(review)
    score = int(total_match.group(1)) if total_match else None
    if score is None:
        findings.append("Reviewer output missing the `**Total**` row in the scorecard table.")
    elif score < 90:
        findings.append(f"Score {score}/100 below pass threshold (90).")

    passed = (blocking is False) and score is not None and score >= 90 and not findings
    return {
        "stage": "content_review",
        "passed": passed,
        "findings": findings,
        "score": score,
        "verdict": (
            "BLOCKING:true" if blocking else ("BLOCKING:false" if blocking is False else "unparseable")
        ),
        "blocking_reason": blocking_reason,
    }


def stage5_asset_integrity(piece: Path, blog_md: str) -> dict[str, Any]:
    """Every referenced local image / bibliography file exists."""
    findings: list[str] = []
    # find ![alt](path) image refs in body
    body = re.sub(r"^---\n.*?\n---\n", "", blog_md, count=1, flags=re.DOTALL)
    for m in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)\)", body):
        ref = m.group(1)
        if ref.startswith(("http://", "https://", "data:")):
            continue
        rel = (piece / "04-diligence" / ref).resolve() if not Path(ref).is_absolute() else Path(ref)
        if not rel.exists():
            findings.append(f"Referenced image file missing: {ref} (resolved: {rel})")
    # bibliography sidecar
    bib = piece / "03-discernment" / "bibliography.bib"
    if not bib.exists():
        findings.append(f"Bibliography sidecar missing: {bib}")
    return {"stage": "asset_integrity", "passed": not findings, "findings": findings}


# ─── Main ───


def ensure_nonce(piece: Path) -> str:
    nonce_path = piece / ".review-nonce"
    if not nonce_path.exists():
        nonce = secrets.token_hex(NONCE_BYTES)
        nonce_path.write_text(nonce, encoding="utf-8")
        return nonce
    return nonce_path.read_text(encoding="utf-8").strip()


def rotate_nonce(piece: Path) -> str:
    """Regenerate the nonce — called before each new review round."""
    nonce = secrets.token_hex(NONCE_BYTES)
    (piece / ".review-nonce").write_text(nonce, encoding="utf-8")
    return nonce


def main() -> int:
    parser = argparse.ArgumentParser(description="Release Owner Gate orchestrator.")
    parser.add_argument("--piece", type=Path, required=True, help="Per-piece working directory.")
    parser.add_argument("--round", type=int, default=1, help="Review iteration (1-3).")
    parser.add_argument(
        "--rotate-nonce",
        action="store_true",
        help="Rotate the nonce before this round (the orchestrator should call this before dispatching the reviewer).",
    )
    args = parser.parse_args()

    piece: Path = args.piece.resolve()
    if not piece.is_dir():
        print(f"ERROR: piece dir not found: {piece}", file=sys.stderr)
        return 2

    blog_path = piece / "04-diligence" / "blog.md"
    if not blog_path.exists():
        print(f"ERROR: no blog.md at {blog_path}", file=sys.stderr)
        return 2
    blog_md = blog_path.read_text(encoding="utf-8")

    if args.rotate_nonce:
        nonce = rotate_nonce(piece)
    else:
        nonce = ensure_nonce(piece)

    stages = [
        stage1_capability(blog_md),
        stage2_format(blog_md),
        stage3_visual(piece, blog_md),
        stage4_content_review(piece, nonce),
        stage5_asset_integrity(piece, blog_md),
    ]

    all_passed = all(s["passed"] for s in stages)
    pre_review_failures = any(
        not s["passed"]
        for s in stages
        if s["stage"] in ("capability", "format", "visual", "asset_integrity")
    )

    report = {
        "piece": str(piece),
        "round": args.round,
        "nonce": nonce,
        "stages": stages,
        "passed": all_passed,
        "_meta": {
            "schema": "4d-blog-engine.preflight-report.v1",
            "generated": datetime.now(timezone.utc).isoformat(),
        },
    }

    out_json = piece / "04-diligence" / "preflight-report.json"
    out_md = piece / "04-diligence" / "preflight-report.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [f"# Preflight Report — Round {args.round}", ""]
    lines.append(f"**Nonce:** `{nonce}`")
    lines.append(f"**Verdict:** {'PASS' if all_passed else 'FAIL'}")
    lines.append("")
    for s in stages:
        lines.append(f"## Stage: {s['stage']} — {'pass' if s['passed'] else 'fail'}")
        if s["stage"] == "content_review":
            lines.append(f"- Score: {s.get('score')}")
            lines.append(f"- Verdict: {s.get('verdict')}")
            if s.get("blocking_reason"):
                lines.append(f"- Reason: {s['blocking_reason']}")
        for f in s.get("findings", []):
            lines.append(f"- {f}")
        lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(
        f"STATUS={'pass' if all_passed else 'fail'} "
        f"ROUND={args.round} NONCE={nonce} REPORT={out_json}"
    )

    if all_passed:
        return 0
    if pre_review_failures or args.round < 3:
        return 1  # retry
    return 2  # escalate after round 3


if __name__ == "__main__":
    sys.exit(main())
