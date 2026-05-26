#!/usr/bin/env python3
"""
linkedin_score.py — LinkedIn format compliance checker + 3-axis scorecard scaffold.

What this script does (deterministic):
  - Verifies the LinkedIn post complies with mechanical rules from
    references/hook-library.md and the platform conventions baked into the
    plugin's discipline:
      * hook lands before character 210 (the mobile "See more" fold)
      * total char count within the article (800-1200 words) or teaser
        (~1,300 chars) target band per --type
      * no external links in body (link in first comment convention)
      * hashtag count and placement
      * no banned hooks-to-retire matches
      * line-break density (LinkedIn-native formatting)

What this script does NOT do:
  - It does NOT fill in the 3-axis /10 scores (thought leadership / pain /
    audience fit). That's an LLM judgment task done by the linkedin-deriver
    skill against references/release-owner-rubric.md and the angle from
    01-delegation.md. The script emits the scaffold the skill fills in.

Usage:
  python3 linkedin_score.py --file 04-diligence/linkedin-teaser.md --type teaser
  python3 linkedin_score.py --file 04-diligence/linkedin-article.md --type article

Exit codes:
  0 — format checks pass
  1 — format checks fail (script returns findings; do not ship)
  2 — usage / I/O error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FOLD_CHAR = 210

BANNED_HOOKS = [
    r"this one (thing|trick) (made|got) me",
    r"the (CEO|VP|founder) (pulled me aside|told me)",
    r"i'?m (excited|thrilled|delighted) to (share|announce)",
    r"most people don'?t realize",
    r"nobody tells you",
    r"here'?s what they'?re missing",
    r"i'?ve been wrong about",
    r"welcome to (this|the) (issue|edition|post|article)",
    r"happy [a-z]+( day)?[!.]?",
    r"before we (get started|begin)",
    r"sound familiar\?",
    r"here'?s the (thing|kicker|deal)",
    r"the catch\?",
    r"in conclusion",
    r"comment yes if",
    r"dm me if you",
]

TYPE_BANDS = {
    "teaser": {
        "min_chars": 600,
        "max_chars": 1500,
        "min_words": 90,
        "max_words": 280,
    },
    "article": {
        "min_chars": 4000,
        "max_chars": 9000,
        "min_words": 800,
        "max_words": 1200,
    },
}


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)


def extract_body_section(text: str) -> str:
    """Extract the postable body.

    For teaser files (and any file that follows the hook-library.md output
    contract), the postable content is the `## Body` section — not the whole
    file. Scaffold sections (Selected hook, Alternates considered, Posting
    metadata) are LLM workspace, not LinkedIn-bound text.

    For article files (which don't carry scaffold sections), no `## Body`
    header is expected; return the text as-is in that case.

    Heuristic: if the file contains a `## Body` heading, return everything
    between that heading and the next `## ` heading (or EOF). Otherwise,
    return the input unchanged.
    """
    m = re.search(r"^##\s+Body\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    if not m:
        return text
    start = m.end()
    # find next H2 (or EOF) — that's where the body section ends
    rest = text[start:]
    end_m = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    body = rest[: end_m.start()] if end_m else rest
    return body.strip()


def first_n_chars_visible(text: str, n: int) -> str:
    """Approximate the first-N-chars view (strip markdown headers/lists for fold check)."""
    cleaned = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"^[-*]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    return cleaned[:n]


def check_hook_position(body: str) -> dict[str, Any]:
    """The hook must be a complete unit landing before char FOLD_CHAR."""
    sample = first_n_chars_visible(body, FOLD_CHAR)
    # find first sentence terminator inside the sample
    m = re.search(r"[.!?](\s|$)", sample)
    if not m:
        return {
            "passed": False,
            "first_visible_chars": sample,
            "finding": (
                f"No sentence terminator within the first {FOLD_CHAR} chars; "
                "the hook does not land before the mobile fold."
            ),
        }
    return {
        "passed": True,
        "first_visible_chars": sample,
        "hook_ends_at": m.start() + 1,
    }


def check_banned_hooks(body: str) -> list[str]:
    findings: list[str] = []
    # only check the first 300 chars (where the hook lives)
    head = first_n_chars_visible(body, 300).lower()
    for pat in BANNED_HOOKS:
        if re.search(pat, head, flags=re.IGNORECASE):
            findings.append(f"Banned hook pattern matched in opener: `{pat}`")
    return findings


def check_external_links_in_body(body: str) -> list[str]:
    findings: list[str] = []
    # find all markdown links and bare URLs
    md_links = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", body)
    bare_links = re.findall(r"(?<![\(\w])(https?://\S+)", body)
    all_links = set(md_links) | set(bare_links)
    if all_links:
        findings.append(
            f"Body contains {len(all_links)} external link(s); LinkedIn deprioritizes link posts. "
            "Move blog link to the first comment per references/hook-library.md."
        )
    return findings


def check_hashtags(body: str) -> tuple[int, list[str]]:
    """Hashtags should appear ONLY at the end, max 3 (teaser) or 5 (article)."""
    findings: list[str] = []
    hashtags = re.findall(r"(?<![\w/])#\w+", body)
    if not hashtags:
        return 0, []
    # Where do hashtags appear? Find their positions.
    last_inline = 0
    for m in re.finditer(r"(?<![\w/])#\w+", body):
        last_inline = m.start()
    # If a hashtag appears in the first 80% of the document, that's inline
    # placement — penalty.
    doc_len = len(body)
    if doc_len and last_inline < int(doc_len * 0.8):
        findings.append(
            f"Hashtag(s) appear inline (last hashtag at char {last_inline} of {doc_len}); "
            "place hashtags only at end after a line break."
        )
    return len(hashtags), findings


def check_paragraph_density(body: str) -> list[str]:
    """LinkedIn-native: short paragraphs, generous whitespace."""
    findings: list[str] = []
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    long_paras = [p for p in paras if len(p) > 600]
    if long_paras:
        findings.append(
            f"{len(long_paras)} paragraph(s) exceed 600 chars; "
            "break into shorter blocks for LinkedIn-native rhythm."
        )
    return findings


def render_scorecard_scaffold(piece_name: str, post_type: str) -> str:
    """Emit the markdown scaffold the LLM fills in."""
    return (
        f"# LinkedIn Scorecard — {piece_name} ({post_type})\n"
        "\n"
        "> The /10 scores below are filled in by the linkedin-deriver skill "
        "via LLM judgment against references/release-owner-rubric.md and the "
        "angle defined in 01-delegation.md. This script provides the scaffold "
        "and the format-compliance findings.\n"
        "\n"
        "## 3-Axis Scorecard (LLM-filled)\n"
        "\n"
        "| Axis | Score | Justification (one sentence) |\n"
        "|---|:---:|---|\n"
        "| Thought leadership | _/10 | _ |\n"
        "| Pain (lands on the reader, not a third party) | _/10 | _ |\n"
        "| Audience fit | _/10 | _ |\n"
        "\n"
        "**Recommendation (LLM-filled):** _ship | revise | discard_\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="LinkedIn format checker.")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--type", choices=["teaser", "article"], required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if not args.file.exists():
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        return 2

    text = args.file.read_text(encoding="utf-8")
    body = strip_frontmatter(text)
    # v0.1.2 fix: if the file follows hook-library.md's output contract
    # (teaser scaffold with Selected hook / Alternates / Body / Posting metadata
    # sections), score only the postable Body section, not the whole file.
    body = extract_body_section(body)

    findings: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}

    # char + word count
    char_count = len(body.strip())
    word_count = len(re.findall(r"\b[\w']+\b", body))
    band = TYPE_BANDS[args.type]
    metrics["char_count"] = char_count
    metrics["word_count"] = word_count

    if char_count < band["min_chars"] or char_count > band["max_chars"]:
        findings.append(
            {
                "severity": "Major",
                "rule": "length_out_of_band",
                "detail": f"Char count {char_count} outside band [{band['min_chars']}, {band['max_chars']}] for type={args.type}.",
            }
        )
    if word_count < band["min_words"] or word_count > band["max_words"]:
        findings.append(
            {
                "severity": "Major",
                "rule": "word_count_out_of_band",
                "detail": f"Word count {word_count} outside band [{band['min_words']}, {band['max_words']}] for type={args.type}.",
            }
        )

    # hook
    hook = check_hook_position(body)
    metrics["hook_position"] = hook
    if not hook["passed"]:
        findings.append({"severity": "Major", "rule": "hook_position", "detail": hook["finding"]})

    # banned hooks
    for hit in check_banned_hooks(body):
        findings.append({"severity": "Major", "rule": "banned_hook", "detail": hit})

    # external links
    for hit in check_external_links_in_body(body):
        findings.append({"severity": "Medium", "rule": "external_link_in_body", "detail": hit})

    # hashtags
    hashtag_count, hashtag_findings = check_hashtags(body)
    metrics["hashtag_count"] = hashtag_count
    max_hash = 3 if args.type == "teaser" else 5
    if hashtag_count > max_hash:
        findings.append(
            {
                "severity": "Medium",
                "rule": "hashtag_count",
                "detail": f"{hashtag_count} hashtags found; max for {args.type} is {max_hash}.",
            }
        )
    for hit in hashtag_findings:
        findings.append({"severity": "Medium", "rule": "hashtag_placement", "detail": hit})

    # paragraph density
    for hit in check_paragraph_density(body):
        findings.append({"severity": "Minor", "rule": "paragraph_density", "detail": hit})

    passed = not any(f["severity"] == "Major" for f in findings)

    result = {
        "file": str(args.file),
        "type": args.type,
        "passed": passed,
        "metrics": metrics,
        "findings": findings,
        "scorecard_scaffold_path": None,
    }

    # write scaffold + JSON sidecar
    out = args.out or args.file.with_name(args.file.stem + ".score.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_scorecard_scaffold(args.file.stem, args.type), encoding="utf-8")
    json_out = out.with_suffix(".json")
    json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["scorecard_scaffold_path"] = str(out)

    print(
        f"STATUS={'pass' if passed else 'fail'} TYPE={args.type} "
        f"CHARS={char_count} WORDS={word_count} HASHTAGS={hashtag_count} "
        f"FINDINGS={len(findings)} SCAFFOLD={out}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
