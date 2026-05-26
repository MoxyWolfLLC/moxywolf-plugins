#!/usr/bin/env python3
"""
prose_lint.py — Layer-1 deterministic anti-AI-slop linter.

Implements the Tier-1 catalog from references/ai-anti-patterns.md:
  - vocabulary blocklist (single-word AI tells)
  - regex banned phrases
  - banned sentence-initial transitions
  - typographic rules (em-dash, straight quotes, semicolons)
  - measurable metrics (burstiness, TTR, passive rate, mean sentence length,
    paragraph length SD, list-item word-count SD)

Run modes:
  --report    Read-only: emit findings to JSON and markdown.
  --fix       Auto-replace em-dashes with spaced en-dashes and straight quotes
              with typographer's quotes. Other findings remain advisory.

Tier-2 (LLM structural patterns — question-H2 ratio, three-clause rhythm,
hedge stacking, etc.) is NOT scanned by this script; the Discernment skill
runs an LLM sub-agent against ai-anti-patterns.md §Tier-2 for that.

Exit codes:
  0 — pass (no findings or only Minors)
  1 — issues found (Mediums or Majors present); see report
  2 — usage / I/O error

Usage:
  python3 prose_lint.py --report draft.md --out slop-findings.md
  python3 prose_lint.py --fix draft.md
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

# ─── Tier-1 vocabulary catalogs (mirror references/ai-anti-patterns.md) ───

BANNED_WORDS: set[str] = {
    "delve", "leverage", "utilize", "robust", "seamless", "seamlessly",
    "tapestry", "multifaceted", "testament", "pivotal", "paradigm", "holistic",
    "synergize", "synergy", "foster", "comprehensive", "cutting-edge",
    "revolutionize", "harness", "unlock", "thrilled",
    "landscape", "navigate", "crucial", "vital",
    "game-changer", "game-changing", "transformative", "journey",
    "empower", "ecosystem", "pillar",
    "ascertain", "commence", "disseminate", "facilitate",
    "ever-evolving", "ever-changing", "dynamic", "innovative",
}

BANNED_PHRASES: list[str] = [
    r"in today'?s (fast-paced|digital|modern|ever-evolving|rapidly changing) (world|landscape|era|environment)",
    r"in the (era|age) of",
    r"it'?s (worth|important) (noting|to note|to understand|to consider)",
    r"it is (worth|important) (noting|to note)",
    r"needless to say",
    r"that being said",
    r"let'?s (dive|delve|jump|explore|unpack|talk about|take a (closer|deeper) look)",
    r"buckle up",
    r"the catch\?",
    r"here'?s the (thing|kicker|deal)",
    r"sound familiar\?",
    r"in conclusion",
    r"to wrap (up|things up)",
    r"moving forward",
    r"in order to",
    r"the fact that",
    r"as we (all )?know",
    r"welcome to (this|the) (issue|edition|post|article)",
    r"in this (post|article|blog|piece) ?,? ?(we'?(ll| will)|i'?(ll| will))",
    r"i'?m (thrilled|excited|delighted) to (share|announce)",
    r"without further ado",
]

BANNED_TRANSITIONS: set[str] = {
    "furthermore", "additionally", "moreover", "nevertheless",
    "in conclusion", "however it should be noted", "that being said",
    "with that said", "all in all", "to summarize",
}

# ─── Measurable thresholds (mirror references/ai-anti-patterns.md) ───

THRESHOLDS = {
    "burstiness_min": 0.30,        # below = AI-uniform
    "ttr_min": 0.40,                # below = AI-repetitive vocabulary
    "passive_max": 0.20,            # above = too passive
    "mean_sentence_min": 10,
    "mean_sentence_max": 26,
    "paragraph_sd_min": 25,         # below = AI-uniform
    "list_item_sd_min": 5,          # below = symmetric-list-bloat
}

# ─── Helpers ───


def split_sentences(text: str) -> list[str]:
    # Simple but effective: break on sentence terminators, keep the terminator.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def split_paragraphs(text: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def is_passive(sentence: str) -> bool:
    # crude heuristic; finds `to be` + past participle.
    return bool(
        re.search(
            r"\b(am|is|are|was|were|be|been|being)\s+\w+(ed|en|t)\b",
            sentence,
            re.IGNORECASE,
        )
    )


def find_locations(text: str, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """Return list of (line_number, matched_text) for every regex hit."""
    locs: list[tuple[int, str]] = []
    for ln, line in enumerate(text.splitlines(), start=1):
        for m in pattern.finditer(line):
            locs.append((ln, m.group(0)))
    return locs


# ─── Scan ───


def scan(text: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    body = text  # full document including frontmatter; YAML matters too

    # banned words (whole-word, case-insensitive)
    for word in sorted(BANNED_WORDS):
        pat = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        for ln, hit in find_locations(body, pat):
            findings.append(
                {
                    "severity": "Major",
                    "category": "vocab",
                    "rule": f"banned_word:{word}",
                    "line": ln,
                    "match": hit,
                    "fix": "Replace with the specific, concrete word for the actual thing.",
                }
            )

    # banned phrases
    for raw in BANNED_PHRASES:
        pat = re.compile(raw, re.IGNORECASE)
        for ln, hit in find_locations(body, pat):
            findings.append(
                {
                    "severity": "Major",
                    "category": "phrase",
                    "rule": f"banned_phrase:{raw}",
                    "line": ln,
                    "match": hit,
                    "fix": "Cut entirely or rewrite as a specific claim.",
                }
            )

    # banned transitions (sentence-initial)
    for line_no, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        for trans in BANNED_TRANSITIONS:
            if re.match(rf"^{re.escape(trans)}\b", stripped, re.IGNORECASE):
                findings.append(
                    {
                        "severity": "Medium",
                        "category": "transition",
                        "rule": f"banned_transition:{trans}",
                        "line": line_no,
                        "match": stripped[: len(trans) + 1],
                        "fix": "Cut the transition; the next sentence speaks for itself.",
                    }
                )

    # em-dash detection
    em_pat = re.compile(r"—")
    em_hits = find_locations(body, em_pat)
    for ln, _ in em_hits:
        findings.append(
            {
                "severity": "Major",
                "category": "typography",
                "rule": "em_dash",
                "line": ln,
                "match": "—",
                "fix": "Replace with spaced en-dash ` – ` or a comma/period. MoxyWolf style forbids em-dashes.",
            }
        )

    # semicolons in body (advisory)
    semi_pat = re.compile(r";")
    for ln, _ in find_locations(body, semi_pat):
        findings.append(
            {
                "severity": "Minor",
                "category": "typography",
                "rule": "semicolon",
                "line": ln,
                "match": ";",
                "fix": "MoxyWolf style prefers two sentences over a semicolon.",
            }
        )

    # ─── Measurable metrics (operate on prose only, strip frontmatter) ───
    prose = re.sub(r"^---\n.*?\n---\n", "", body, count=1, flags=re.DOTALL)
    # strip code fences before measuring
    prose = re.sub(r"```[^\n]*\n.*?\n```", "", prose, flags=re.DOTALL)
    sentences = split_sentences(prose)
    paragraphs = split_paragraphs(prose)
    sentence_lengths = [word_count(s) for s in sentences if word_count(s) > 0]
    metrics: dict[str, Any] = {}

    if sentence_lengths:
        mean_sl = statistics.fmean(sentence_lengths)
        stdev_sl = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0.0
        burstiness = round(stdev_sl / mean_sl, 3) if mean_sl else 0.0
        metrics["mean_sentence_length"] = round(mean_sl, 2)
        metrics["burstiness"] = burstiness
        metrics["sentence_count"] = len(sentence_lengths)
        if burstiness < THRESHOLDS["burstiness_min"]:
            findings.append(
                {
                    "severity": "Major",
                    "category": "metric",
                    "rule": "burstiness_low",
                    "value": burstiness,
                    "threshold": THRESHOLDS["burstiness_min"],
                    "fix": "Mix sentence lengths — some 4-word fragments alongside 30-word builds.",
                }
            )
        if mean_sl < THRESHOLDS["mean_sentence_min"] or mean_sl > THRESHOLDS["mean_sentence_max"]:
            findings.append(
                {
                    "severity": "Medium",
                    "category": "metric",
                    "rule": "mean_sentence_length_out_of_range",
                    "value": round(mean_sl, 2),
                    "threshold": f"[{THRESHOLDS['mean_sentence_min']}, {THRESHOLDS['mean_sentence_max']}]",
                    "fix": "Adjust sentence length distribution.",
                }
            )
        # passive
        passive_count = sum(1 for s in sentences if is_passive(s))
        passive_rate = passive_count / max(1, len(sentences))
        metrics["passive_rate"] = round(passive_rate, 3)
        if passive_rate > THRESHOLDS["passive_max"]:
            findings.append(
                {
                    "severity": "Medium",
                    "category": "metric",
                    "rule": "passive_voice_high",
                    "value": round(passive_rate, 3),
                    "threshold": THRESHOLDS["passive_max"],
                    "fix": "Convert passive constructions to active where possible.",
                }
            )

    # TTR
    words = [w.lower() for w in re.findall(r"\b[\w']+\b", prose)]
    if words:
        ttr = round(len(set(words)) / len(words), 3)
        metrics["ttr"] = ttr
        metrics["total_words"] = len(words)
        if ttr < THRESHOLDS["ttr_min"]:
            findings.append(
                {
                    "severity": "Medium",
                    "category": "metric",
                    "rule": "ttr_low",
                    "value": ttr,
                    "threshold": THRESHOLDS["ttr_min"],
                    "fix": "Vocabulary is repetitive; vary word choice in noun and verb positions.",
                }
            )

    # paragraph SD
    para_word_counts = [word_count(p) for p in paragraphs]
    metrics["paragraph_count"] = len(paragraphs)
    if len(para_word_counts) > 1:
        para_sd = statistics.stdev(para_word_counts)
        metrics["paragraph_length_sd"] = round(para_sd, 2)
        if para_sd < THRESHOLDS["paragraph_sd_min"]:
            findings.append(
                {
                    "severity": "Medium",
                    "category": "metric",
                    "rule": "paragraph_length_uniform",
                    "value": round(para_sd, 2),
                    "threshold": THRESHOLDS["paragraph_sd_min"],
                    "fix": "Vary paragraph length — some single-sentence, some 5-sentence.",
                }
            )

    # list-item SD (look at flat bullet blocks)
    for m in re.finditer(r"((?:^[-*]\s+.*?$\n?)+)", prose, re.MULTILINE):
        bullets = [b.strip() for b in m.group(0).splitlines() if b.strip()]
        if len(bullets) < 3:
            continue
        bullet_word_counts = [word_count(b) for b in bullets]
        if len(bullet_word_counts) > 1:
            bsd = statistics.stdev(bullet_word_counts)
            if bsd < THRESHOLDS["list_item_sd_min"]:
                findings.append(
                    {
                        "severity": "Medium",
                        "category": "metric",
                        "rule": "symmetric_list_bloat",
                        "value": round(bsd, 2),
                        "threshold": THRESHOLDS["list_item_sd_min"],
                        "fix": "Vary bullet length — current list reads as AI-padded for symmetry.",
                    }
                )

    # ─── Letter grade ───
    weight = {"Major": 3, "Medium": 2, "Minor": 1}
    score = sum(weight[f["severity"]] for f in findings)
    majors = sum(1 for f in findings if f["severity"] == "Major")

    if score >= 20 or majors >= 3 or len(findings) >= 6:
        grade = "F"
    elif score >= 13 or majors >= 2:
        grade = "D"
    elif score >= 8:
        grade = "C"
    elif score >= 4:
        grade = "B"
    else:
        grade = "A"

    return {
        "findings": findings,
        "metrics": metrics,
        "score": score,
        "majors": majors,
        "total_findings": len(findings),
        "grade": grade,
    }


def auto_fix(text: str) -> tuple[str, dict[str, int]]:
    """Auto-replace em-dashes and straight quotes; return (new_text, counts)."""
    counts: dict[str, int] = {"em_dash": 0, "straight_double": 0, "straight_single": 0}
    new = text.replace("—", " – ")
    counts["em_dash"] = text.count("—")
    # straight double quotes → typographer's. Naive alternating heuristic.
    def replace_doubles(s: str) -> str:
        out: list[str] = []
        open_q = True
        for ch in s:
            if ch == '"':
                out.append("“" if open_q else "”")
                counts["straight_double"] += 1
                open_q = not open_q
            else:
                out.append(ch)
        return "".join(out)

    def replace_singles(s: str) -> str:
        out: list[str] = []
        prev = " "
        for ch in s:
            if ch == "'":
                # treat as apostrophe if preceded by a letter; otherwise as a quote
                out.append("’" if prev.isalpha() else "‘")
                counts["straight_single"] += 1
            else:
                out.append(ch)
            prev = ch
        return "".join(out)

    new = replace_doubles(new)
    new = replace_singles(new)
    return new, counts


def render_findings_md(scan_result: dict[str, Any], target: Path) -> str:
    lines: list[str] = []
    lines.append(f"# Slop findings — {target.name}")
    lines.append("")
    lines.append(f"**Grade:** {scan_result['grade']}")
    lines.append(
        f"**Weighted score:** {scan_result['score']} · "
        f"**Total findings:** {scan_result['total_findings']} · "
        f"**Majors:** {scan_result['majors']}"
    )
    lines.append("")
    lines.append("## Metrics")
    for k, v in scan_result["metrics"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## Findings")
    if not scan_result["findings"]:
        lines.append("_None — clean pass._")
    for i, f in enumerate(scan_result["findings"], 1):
        loc = f"line {f.get('line')}" if f.get("line") else "metric"
        match = f.get("match") or f.get("value")
        lines.append(
            f"{i}. **[{f['severity']}]** `{f['rule']}` at {loc} — "
            f"`{match}` — _Fix:_ {f['fix']}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer-1 anti-AI-slop linter.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--report", action="store_true", help="Read-only; emit findings.")
    parser.add_argument("--fix", action="store_true", help="Auto-fix em-dashes and quotes.")
    parser.add_argument("--out", type=Path, default=None, help="Findings markdown path.")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        return 2

    text = args.file.read_text(encoding="utf-8")

    if args.fix:
        new_text, counts = auto_fix(text)
        args.file.write_text(new_text, encoding="utf-8")
        print(
            f"STATUS=fixed em_dash={counts['em_dash']} "
            f"double_quotes={counts['straight_double']} "
            f"single_quotes={counts['straight_single']}"
        )
        # scan after fix
        text = new_text

    result = scan(text)
    out = args.out or args.file.with_name(args.file.stem + ".slop.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_findings_md(result, args.file), encoding="utf-8")
    json_out = out.with_suffix(".json")
    json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(
        f"STATUS=scanned GRADE={result['grade']} "
        f"SCORE={result['score']} FINDINGS={result['total_findings']} "
        f"MAJORS={result['majors']} OUT={out}"
    )
    if result["grade"] in ("D", "F"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
