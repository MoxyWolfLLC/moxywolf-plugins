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
  - rhetorical-device DENSITY (v0.2.0 — see below)

Run modes:
  --report    Read-only: emit findings to JSON and markdown.
  --fix       Auto-replace em-dashes with spaced en-dashes and straight quotes
              with typographer's quotes. Other findings remain advisory.

Tier-2 (LLM structural patterns — question-H2 ratio, three-clause rhythm,
hedge stacking, etc.) is NOT scanned by this script; the Discernment skill
runs an LLM sub-agent against ai-anti-patterns.md §Tier-2 for that.

Rhetorical-device density (v0.2.0)
----------------------------------
Contrast framing and the three-beat reveal are Tier-2 Majors in the catalog and
signature constructions in some writers' voice profiles. Counting them punishes
the writer for having a voice; spacing them is what actually separates prose
that reads as speech from prose that reads as engineered.

So this script MEASURES both devices deterministically and reports the counts as
ADVISORIES (never scored), then enforces spacing instead:

  - no rhetorical hit within `--density-gap` sentences of another
  - no more than `--max-oneliners` standalone one-line paragraphs
  - at least as many short sentences doing ordinary work as short sentences
    delivering a line

Those density rules are scored, and only for long-form pieces (over
`--longform-words`), where per-paragraph density that reads fine at 450 words
compounds into something that reads engineered at 1,600. Pass the writer's
declared signature devices with `--signature-devices` so the report tells the
Layer-2 agent which counts it must treat as advisory rather than blocking.

Exit codes:
  0 — pass (no findings or only Minors)
  1 — issues found (Mediums or Majors present); see report
  2 — usage / I/O error

Usage:
  python3 prose_lint.py --report draft.md --out slop-findings.md
  python3 prose_lint.py --report draft.md --signature-devices contrast-framing,three-beat-reveal
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
    "burstiness_target": 0.50,      # 0.30-0.50 = drifting toward uniform; advisory band
    "ttr_min": 0.40,                # below = AI-repetitive vocabulary
    "passive_max": 0.20,            # above = too passive
    "mean_sentence_min": 10,
    "mean_sentence_max": 26,
    "paragraph_sd_min": 25,         # below = AI-uniform
    "list_item_sd_min": 5,          # below = symmetric-list-bloat
}

# ─── Rhetorical-device density (v0.2.0; mirrors ai-anti-patterns.md §Long-form) ───

DENSITY_DEFAULTS = {
    "longform_words": 900,     # over this, density rules are scored
    "density_gap": 4,          # minimum sentences between two rhetorical hits
    # Budget calibrated against finished text in both directions, 2026-07-29:
    # Dorian's published "I Got the Shape Wrong" (2,146 words, signed, human-written)
    # carries 2 violations, so 2 has to pass or the rule fails his own standard.
    # The draft that failed Phase 3 three times carried 9. Medium above budget,
    # Major at density_major_at, which lands that draft in Major where it belongs.
    "density_budget": 2,       # violations tolerated before scoring anything
    "density_major_at": 6,     # violations at or above this = Major
    "max_oneliners": 2,        # standalone one-line paragraphs allowed per piece
    "short_sentence_words": 8,  # at or under this = a "short" sentence
    "multibeat_run": 3,        # consecutive fragments that make a multi-beat reveal
    "multibeat_words": 6,      # at or under this = a "beat"
}

KNOWN_SIGNATURE_DEVICES = {"contrast-framing", "three-beat-reveal"}

# "It's not X, it's Y" / "isn't X, it's Y" / "not X but Y" / "Not X." / "X, not Y."
CONTRAST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\b(?:it|this|that|they|we|you|he|she)(?:'?s|'?re| is| are| was| were)?\s+not\b"
        r"[^.?!]{2,90},\s*(?:it|this|that|they|we|you|but)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:is|are|was|were|does|do|did|has|have|can|could|would|will)n'?[o']?t\b"
        r"[^.?!]{2,90},\s*(?:it|this|that|they|we|you|but)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnot\s+[^,.?!]{2,70}\s+but\s+", re.IGNORECASE),
    re.compile(r"^\s*not\s+[^.?!]{2,70}[.?!]\s*$", re.IGNORECASE),
    re.compile(r",\s*not\s+[^,.?!]{2,70}[.?!]\s*$", re.IGNORECASE),
]

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


def _excerpt(text: str, limit: int = 90) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def detect_contrast_framing(sentences: list[str]) -> list[dict[str, Any]]:
    """Sentence indices carrying an 'it's not X, it's Y' style contrast."""
    hits: list[dict[str, Any]] = []
    for i, s in enumerate(sentences):
        for pat in CONTRAST_PATTERNS:
            if pat.search(s.strip()):
                hits.append({"device": "contrast-framing", "sentence": i, "text": _excerpt(s)})
                break
    return hits


def is_body_paragraph(par: str) -> bool:
    """True for running prose. False for headings, lists, quotes, tables, fences.

    Density is a property of body cadence. A 'Key takeaways' bullet block is
    SUPPOSED to be a stack of crisp contrast lines, and a heading is not a
    sentence. Measuring those as prose rhythm produces violations that no writer
    should fix.
    """
    t = par.strip()
    if not t:
        return False
    first = t.splitlines()[0].strip()
    if not first:
        return False
    if first[0] in "#>|" or first.startswith("```"):
        return False
    if re.match(r"^[-*+]\s", first) or re.match(r"^\d+[.)]\s", first):
        return False
    return True


def body_sentence_stream(paragraphs: list[str]) -> tuple[list[str], list[int]]:
    """Sentences of body prose only, with a parallel list of paragraph ids."""
    sentences: list[str] = []
    para_ids: list[int] = []
    for pid, par in enumerate(p for p in paragraphs if is_body_paragraph(p)):
        for s in split_sentences(par):
            if word_count(s) > 0:
                sentences.append(s)
                para_ids.append(pid)
    return sentences, para_ids


def detect_multibeat_reveal(
    sentences: list[str], para_ids: list[int], run_len: int, max_words: int
) -> list[dict[str, Any]]:
    """Runs of consecutive short fragments — 'Nine tools. Nine parsers. Same data.'

    Runs never cross a paragraph boundary; three short sentences that happen to
    end one paragraph and start the next are not a reveal.
    """
    hits: list[dict[str, Any]] = []
    run: list[int] = []

    def close(r: list[int]) -> None:
        if len(r) >= run_len:
            hits.append(
                {
                    "device": "three-beat-reveal",
                    "sentence": r[0],
                    "span": [r[0], r[-1]],
                    "beats": len(r),
                    "text": _excerpt(" ".join(sentences[j] for j in r)),
                }
            )

    for i, s in enumerate(sentences):
        same_para = bool(run) and para_ids[i] == para_ids[run[-1]]
        if 0 < word_count(s) <= max_words and (not run or same_para):
            run.append(i)
        else:
            close(run)
            run = [i] if 0 < word_count(s) <= max_words else []
    close(run)
    return hits


def merge_device_hits(
    contrast: list[dict[str, Any]], multibeat: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """One sentence is one rhetorical hit.

    'Translation, not conquest.' inside a three-beat run is one move, not two.
    The reveal is the larger structure, so it wins and absorbs the contrast.
    """
    spans = [tuple(h["span"]) for h in multibeat]
    kept = [
        h for h in contrast if not any(lo <= h["sentence"] <= hi for lo, hi in spans)
    ]
    return kept + multibeat


def detect_standalone_oneliners(paragraphs: list[str], max_words: int = 15) -> list[str]:
    """Paragraphs that are a single short sentence standing alone on the page."""
    out: list[str] = []
    for p in paragraphs:
        t = p.strip()
        if not t or "\n" in t:
            continue
        if t[0] in "#-*>|" or t.startswith("```") or re.match(r"^\d+[.)]\s", t):
            continue
        if len(split_sentences(t)) == 1 and 0 < word_count(t) <= max_words:
            out.append(_excerpt(t))
    return out


def density_violations(hits: list[dict[str, Any]], min_gap: int) -> list[dict[str, Any]]:
    """Pairs of rhetorical hits sitting closer together than min_gap sentences."""
    ordered = sorted(hits, key=lambda h: h["sentence"])
    out: list[dict[str, Any]] = []
    for a, b in zip(ordered, ordered[1:]):
        gap = b["sentence"] - a["sentence"]
        if gap < min_gap:
            out.append(
                {
                    "gap": gap,
                    "first": {"sentence": a["sentence"], "device": a["device"], "text": a["text"]},
                    "second": {"sentence": b["sentence"], "device": b["device"], "text": b["text"]},
                }
            )
    return out


def find_locations(text: str, pattern: re.Pattern[str]) -> list[tuple[int, str]]:
    """Return list of (line_number, matched_text) for every regex hit."""
    locs: list[tuple[int, str]] = []
    for ln, line in enumerate(text.splitlines(), start=1):
        for m in pattern.finditer(line):
            locs.append((ln, m.group(0)))
    return locs


# ─── Scan ───


def _strip_protected_regions(text: str) -> str:
    """Strip <script>, <style>, ``` fences, and inline `code` from text — v0.1.2 fix.

    These regions contain code/data where quote-curling and em-dash rules
    don't apply (JSON-LD requires straight quotes; code blocks shouldn't be
    auto-prettified). Frontmatter is also stripped.
    """
    out = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    out = re.sub(r"```[^\n]*\n.*?\n```", "", out, flags=re.DOTALL)
    out = re.sub(r"<script\b[^>]*>.*?</script>", "", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<style\b[^>]*>.*?</style>", "", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"`[^`\n]+`", "", out)
    return out


def scan(
    text: str,
    signature_devices: set[str] | None = None,
    longform: bool | None = None,
    density: dict[str, int] | None = None,
) -> dict[str, Any]:
    signature_devices = signature_devices or set()
    cfg = {**DENSITY_DEFAULTS, **(density or {})}
    findings: list[dict[str, Any]] = []
    advisories: list[dict[str, Any]] = []
    body = _strip_protected_regions(text)  # v0.1.2 — exclude script/style/code from scan

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
    # strip <script> and <style> blocks (e.g. JSON-LD) — v0.1.2 fix
    prose = re.sub(r"<script\b[^>]*>.*?</script>", "", prose, flags=re.DOTALL | re.IGNORECASE)
    prose = re.sub(r"<style\b[^>]*>.*?</style>", "", prose, flags=re.DOTALL | re.IGNORECASE)
    # strip inline `code` runs (cheap protection against quote-curling in inline tech)
    prose = re.sub(r"`[^`\n]+`", "", prose)
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
        elif burstiness < THRESHOLDS["burstiness_target"]:
            # v0.2.0 — the gray band. Stripping fragments to satisfy a Tier-2 count
            # pushes burstiness down toward the AI-uniform floor; catch that early.
            findings.append(
                {
                    "severity": "Minor",
                    "category": "metric",
                    "rule": "burstiness_drifting",
                    "value": burstiness,
                    "threshold": THRESHOLDS["burstiness_target"],
                    "fix": (
                        "Variance is falling toward the AI-uniform floor. If fragments were "
                        "removed to satisfy a rhetorical-device count, that trade cost more "
                        "than it bought — space them instead of deleting them."
                    ),
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

    # ─── Rhetorical-device density (v0.2.0) ───
    #
    # The two devices below are Tier-2 Majors in the catalog and signature moves in
    # some voice profiles. We count them but never score the count. What gets scored
    # is spacing, and only past the long-form threshold.

    total_words = metrics.get("total_words", word_count(prose))
    is_longform = (total_words > cfg["longform_words"]) if longform is None else longform

    body_sentences, body_para_ids = body_sentence_stream(paragraphs)
    contrast_raw = detect_contrast_framing(body_sentences)
    multibeat_hits = detect_multibeat_reveal(
        body_sentences, body_para_ids, cfg["multibeat_run"], cfg["multibeat_words"]
    )
    contrast_hits = [
        h
        for h in contrast_raw
        if not any(s["span"][0] <= h["sentence"] <= s["span"][1] for s in multibeat_hits)
    ]
    rhetorical_hits = merge_device_hits(contrast_raw, multibeat_hits)
    oneliners = detect_standalone_oneliners(paragraphs)

    metrics["body_sentence_count"] = len(body_sentences)
    short_idx = {
        i
        for i, s in enumerate(body_sentences)
        if 0 < word_count(s) <= cfg["short_sentence_words"]
    }
    punchline_idx = {h["sentence"] for h in rhetorical_hits} & short_idx
    ordinary_short = len(short_idx - punchline_idx)

    metrics["longform"] = is_longform
    metrics["contrast_framing_count"] = len(contrast_hits)
    metrics["multibeat_reveal_count"] = len(multibeat_hits)
    metrics["standalone_oneliner_count"] = len(oneliners)
    metrics["short_sentences_ordinary"] = ordinary_short
    metrics["short_sentences_punchline"] = len(punchline_idx)

    for device, hits in (("contrast-framing", contrast_hits), ("three-beat-reveal", multibeat_hits)):
        if not hits:
            continue
        advisories.append(
            {
                "device": device,
                "count": len(hits),
                "declared_signature": device in signature_devices,
                "locations": hits,
                "note": (
                    "Declared signature device. Layer 2 must treat the raw count as advisory "
                    "and judge spacing, not frequency."
                    if device in signature_devices
                    else "Not declared as a signature device for this writer. Layer 2 scores "
                    "this against the Tier-2 Major rule as written."
                ),
            }
        )

    violations = density_violations(rhetorical_hits, cfg["density_gap"])
    metrics["density_violations"] = len(violations)

    if is_longform:
        if len(violations) > cfg["density_budget"]:
            worst = ", ".join(
                f"sentences {v['first']['sentence']}→{v['second']['sentence']} (gap {v['gap']})"
                for v in violations[:5]
            )
            findings.append(
                {
                    "severity": (
                        "Major" if len(violations) >= cfg["density_major_at"] else "Medium"
                    ),
                    "category": "density",
                    "rule": "rhetorical_density",
                    "value": len(violations),
                    "threshold": (
                        f"{cfg['density_budget']} pairs closer than {cfg['density_gap']} "
                        f"sentences (Major at {cfg['density_major_at']})"
                    ),
                    "locations": violations,
                    "fix": (
                        f"Rhetorical hits are stacking: {worst}. Move one of each pair or make it "
                        "a plain declarative. Do not solve this by converting 'Not X. Not Y. Z.' "
                        "into 'X, Y, and Z' — that changes the marks, not the cadence."
                    ),
                }
            )
        if len(oneliners) > cfg["max_oneliners"]:
            findings.append(
                {
                    "severity": "Medium",
                    "category": "density",
                    "rule": "standalone_oneliners_high",
                    "value": len(oneliners),
                    "threshold": cfg["max_oneliners"],
                    "locations": oneliners,
                    "fix": "Fold the extras back into the paragraphs they belong to.",
                }
            )
        if len(punchline_idx) > ordinary_short:
            findings.append(
                {
                    "severity": "Medium",
                    "category": "density",
                    "rule": "short_sentences_all_punchline",
                    "value": f"{len(punchline_idx)} punchline / {ordinary_short} ordinary",
                    "threshold": "ordinary >= punchline",
                    "fix": (
                        "Every short sentence is landing a line. Real speech uses short sentences "
                        "for ordinary work too. Add brief declaratives that just carry information."
                    ),
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
        "advisories": advisories,
        "metrics": metrics,
        "longform": is_longform,
        "signature_devices": sorted(signature_devices),
        "score": score,
        "majors": majors,
        "total_findings": len(findings),
        "grade": grade,
    }


def auto_fix(text: str) -> tuple[str, dict[str, int]]:
    """Auto-replace em-dashes and straight quotes; return (new_text, counts).

    v0.1.2 — protects <script>, <style>, ``` fences, and inline `code` runs
    from quote-curling and em-dash replacement (JSON-LD requires straight
    quotes; code shouldn't be auto-prettified).
    """
    counts: dict[str, int] = {"em_dash": 0, "straight_double": 0, "straight_single": 0}

    # Carve out protected regions (script/style/code-fence/inline-code) and
    # apply transforms only to the prose between them.
    PROTECT = re.compile(
        r"(```[^\n]*\n.*?\n```"          # fenced code
        r"|<script\b[^>]*>.*?</script>"  # script blocks (JSON-LD)
        r"|<style\b[^>]*>.*?</style>"    # style blocks
        r"|`[^`\n]+`)",                  # inline code
        flags=re.DOTALL | re.IGNORECASE,
    )

    parts = PROTECT.split(text)
    # Even indices = prose, odd indices = protected
    for i, p in enumerate(parts):
        if i % 2 == 1:
            continue  # protected — leave verbatim
        counts["em_dash"] += p.count("—")
        # Collapse surrounding whitespace so "X — Y" becomes "X – Y" (single-spaced),
        # not "X  –  Y" (doubled). v0.1.2 fix.
        parts[i] = re.sub(r"\s*—\s*", " – ", p)
    new = "".join(parts)
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

    # Apply quote-curling only to prose regions (re-split to preserve protections)
    parts = PROTECT.split(new)
    for i, p in enumerate(parts):
        if i % 2 == 1:
            continue
        p = replace_doubles(p)
        p = replace_singles(p)
        parts[i] = p
    new = "".join(parts)
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
    lines.append(
        f"**Length class:** {'long-form' if scan_result.get('longform') else 'short-form'} · "
        f"**Declared signature devices:** "
        f"{', '.join(scan_result.get('signature_devices') or []) or 'none'}"
    )
    lines.append("")
    lines.append("## Metrics")
    for k, v in scan_result["metrics"].items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")

    advisories = scan_result.get("advisories") or []
    if advisories:
        lines.append("## Advisories — counted, never scored")
        lines.append("")
        lines.append(
            "These are the rhetorical devices the catalog lists as Tier-2 Majors. Layer 1 reports "
            "the count so Layer 2 can judge spacing rather than frequency. The count alone does "
            "not fail anything."
        )
        lines.append("")
        for a in advisories:
            flag = "signature" if a["declared_signature"] else "not declared"
            lines.append(f"### {a['device']} — {a['count']} instance(s) ({flag})")
            lines.append("")
            lines.append(a["note"])
            lines.append("")
            for loc in a["locations"]:
                lines.append(f"- sentence {loc['sentence']}: {loc['text']}")
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
    parser.add_argument(
        "--signature-devices",
        default="",
        help=(
            "Comma-separated devices the writer's voice profile declares as signature moves "
            f"({', '.join(sorted(KNOWN_SIGNATURE_DEVICES))}). Their counts are reported as "
            "advisory; spacing is still enforced."
        ),
    )
    parser.add_argument(
        "--longform",
        dest="longform",
        action="store_true",
        default=None,
        help="Force long-form density scoring regardless of word count.",
    )
    parser.add_argument(
        "--no-longform",
        dest="longform",
        action="store_false",
        help="Force short-form: report density, don't score it.",
    )
    parser.add_argument(
        "--longform-words",
        type=int,
        default=DENSITY_DEFAULTS["longform_words"],
        help="Word count above which density rules are scored.",
    )
    parser.add_argument(
        "--density-gap",
        type=int,
        default=DENSITY_DEFAULTS["density_gap"],
        help="Minimum sentences between two rhetorical hits.",
    )
    parser.add_argument(
        "--max-oneliners",
        type=int,
        default=DENSITY_DEFAULTS["max_oneliners"],
        help="Standalone one-line paragraphs allowed per piece.",
    )
    args = parser.parse_args()

    devices = {d.strip().lower() for d in args.signature_devices.split(",") if d.strip()}
    unknown = devices - KNOWN_SIGNATURE_DEVICES
    if unknown:
        print(
            f"ERROR: unknown signature device(s): {', '.join(sorted(unknown))}. "
            f"Known: {', '.join(sorted(KNOWN_SIGNATURE_DEVICES))}",
            file=sys.stderr,
        )
        return 2

    density_cfg = {
        "longform_words": args.longform_words,
        "density_gap": args.density_gap,
        "max_oneliners": args.max_oneliners,
    }

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

    result = scan(
        text,
        signature_devices=devices,
        longform=args.longform,
        density=density_cfg,
    )
    out = args.out or args.file.with_name(args.file.stem + ".slop.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_findings_md(result, args.file), encoding="utf-8")
    json_out = out.with_suffix(".json")
    json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    m = result["metrics"]
    print(
        f"STATUS=scanned GRADE={result['grade']} "
        f"SCORE={result['score']} FINDINGS={result['total_findings']} "
        f"MAJORS={result['majors']} "
        f"LONGFORM={'yes' if result['longform'] else 'no'} "
        f"CONTRAST={m.get('contrast_framing_count', 0)} "
        f"MULTIBEAT={m.get('multibeat_reveal_count', 0)} "
        f"DENSITY_VIOLATIONS={m.get('density_violations', 0)} "
        f"OUT={out}"
    )
    if result["grade"] in ("D", "F"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
