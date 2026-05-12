#!/usr/bin/env python3
"""
BibTeX Parser for Research Pipeline
Parses BibTeX files into structured citation objects ready for Supabase insertion.
Run via: python3 bibtex-parser.py <input.bib> <output.json>
"""

import re
import json
import sys


def parse_bibtex_entry(entry_text: str) -> dict | None:
    """Parse a single BibTeX entry into a structured dict."""
    entry_text = entry_text.strip()
    if not entry_text or not entry_text.startswith("@"):
        return None

    # Extract entry type and citation key
    header_match = re.match(r"@(\w+)\s*\{\s*([^,]+),", entry_text)
    if not header_match:
        return None

    entry_type = header_match.group(1).lower()
    citation_key = header_match.group(2).strip()

    # Extract fields using brace-matching
    fields = {}
    # Match field = {value} or field = "value" or field = number
    field_pattern = re.compile(
        r"(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|\"([^\"]*)\"|(\d+))",
        re.DOTALL,
    )

    for match in field_pattern.finditer(entry_text):
        field_name = match.group(1).lower()
        value = match.group(2) or match.group(3) or match.group(4) or ""
        # Clean up whitespace
        value = re.sub(r"\s+", " ", value).strip()
        fields[field_name] = value

    # Parse year as integer
    year = None
    if "year" in fields:
        try:
            year = int(fields["year"])
        except ValueError:
            year = None

    # Extract arXiv ID from eprint or arxivid fields
    arxiv_id = fields.get("eprint") or fields.get("arxivid") or fields.get("arxiv_id")

    return {
        "citation_key": citation_key,
        "entry_type": entry_type,
        "title": fields.get("title", "Untitled"),
        "authors": fields.get("author"),
        "year": year,
        "journal": fields.get("journal") or fields.get("booktitle"),
        "abstract": fields.get("abstract"),
        "doi": fields.get("doi"),
        "arxiv_id": arxiv_id,
        "url": fields.get("url"),
        "bibtex_raw": entry_text,
        "verification_status": "unverified",
        "source": "bibtex_import",
    }


def parse_bibtex_file(content: str) -> list[dict]:
    """Split a BibTeX file into entries and parse each one."""
    # Split on @ that starts an entry
    raw_entries = re.split(r"(?=@\w+\s*\{)", content)
    citations = []
    seen_keys = set()

    for entry_text in raw_entries:
        parsed = parse_bibtex_entry(entry_text)
        if parsed is None:
            continue

        # Deduplicate by citation_key + abstract
        sig = f"{parsed['citation_key']}|||{parsed.get('abstract', '')}"
        if sig in seen_keys:
            continue
        seen_keys.add(sig)
        citations.append(parsed)

    return citations


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 bibtex-parser.py <input.bib> [output.json]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    citations = parse_bibtex_file(content)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(citations, f, indent=2)
        print(f"Parsed {len(citations)} citations → {output_path}")
    else:
        print(json.dumps(citations, indent=2))
