#!/usr/bin/env python3
"""
smart_quotes.py — apply typographer's quotes to a markdown post body, preserving
YAML frontmatter and JSON-LD script blocks exactly.

Why this is a script and not ad-hoc code:
The /publish skill writes the post into the publishing repo. If we ad-hoc Python
each publish, we hit the same YAML-breaking bug we hit before — curly-quoting
the YAML frontmatter and breaking the static-site-generator build. This script
encodes the exact split logic so the bug doesn't return.

Usage:
    python3 smart_quotes.py --in <source-md> --out <dest-md>
    python3 smart_quotes.py --in <source-md> --in-place

Behavior:
- YAML frontmatter (delimited by leading `---\n...\n---\n`): passed through unchanged.
- <script type="application/ld+json">...</script> blocks in the body: passed through unchanged.
- Markdown body text outside those blocks: typographer's quotes applied.
- Existing curly quotes in the body: left as-is.
- Em-dashes / en-dashes: not touched (this script is quotes-only).

Quote transform rules (single pass per text region):
- `"` after start/whitespace/punctuation → left double `“` ("LEFT DOUBLE QUOTATION MARK")
- `"` after a letter or digit → right double `”`
- `'` after a letter or digit (apostrophe in contractions, possessives) → right single `’`
- `'` after start/whitespace/punctuation followed by non-space → left single `‘`
- Any remaining straight `"` defaults to left double; remaining `'` defaults to right single.

Exit codes:
- 0: success, file written.
- 2: input file not found.
- 3: malformed frontmatter (unmatched `---` delimiters).
"""

import argparse
import re
import sys
from pathlib import Path

LDQUO = "“"  # "
RDQUO = "”"  # "
LSQUO = "‘"  # '
RSQUO = "’"  # '


def split_frontmatter(text):
    """
    Split text into (frontmatter, body) where frontmatter includes the
    leading `---\\n`, the YAML, and the trailing `---\\n`. If the text has no
    frontmatter, returns ('', text).
    """
    if not text.startswith("---\n"):
        return "", text
    # Find the closing `---` line
    m = re.search(r"\n---\n", text[4:])
    if m is None:
        # Malformed frontmatter
        return None, None
    end = 4 + m.start() + len("\n---\n")
    return text[:end], text[end:]


def split_around_jsonld(body):
    """
    Split body into a list of (kind, content) tuples where kind is either
    'text' or 'jsonld'. JSON-LD blocks are <script type="application/ld+json">
    ... </script>. The split preserves the script blocks verbatim.
    """
    pattern = re.compile(
        r'(<script\s+type="application/ld\+json"[^>]*>.*?</script>)',
        re.DOTALL | re.IGNORECASE,
    )
    parts = pattern.split(body)
    result = []
    for part in parts:
        if pattern.fullmatch(part):
            result.append(("jsonld", part))
        else:
            result.append(("text", part))
    return result


def apply_smart_quotes(text):
    """
    Apply typographer's quote rules to a chunk of markdown body text.
    The order matters: single quotes first (apostrophes are common and easy
    to disambiguate), then double quotes.
    """
    # --- Single quotes ---
    # Contractions and possessives: ' after a letter or digit → right single
    text = re.sub(r"(?<=[A-Za-z0-9])'", RSQUO, text)
    # Opening single quote: ' at start of string or after whitespace/opening
    # punctuation, followed by a non-space character → left single
    text = re.sub(r"(^|[\s\(\[\{<])'(?=\S)", lambda m: m.group(1) + LSQUO, text)
    # Any remaining straight ' → right single (closing quote default)
    text = text.replace("'", RSQUO)

    # --- Double quotes ---
    # Opening double quote: " at start of string or after whitespace/opening
    # punctuation, followed by a non-space character → left double
    text = re.sub(r'(^|[\s\(\[\{<])"(?=\S)', lambda m: m.group(1) + LDQUO, text)
    # Closing double quote: " after a letter, digit, or closing punctuation
    # → right double
    text = re.sub(r'(?<=[A-Za-z0-9\.\,\!\?\;\:\)\]\}])"', RDQUO, text)
    # Any remaining straight " → left double (opening default)
    text = text.replace('"', LDQUO)

    return text


def transform(text):
    """
    Top-level transform. Splits off YAML frontmatter, then splits the body
    around JSON-LD script blocks, applies smart quotes only to the text
    chunks, and reassembles.
    """
    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        raise ValueError("Malformed frontmatter: opening --- without closing ---")

    chunks = split_around_jsonld(body)
    transformed_chunks = []
    for kind, content in chunks:
        if kind == "text":
            transformed_chunks.append(apply_smart_quotes(content))
        else:
            # JSON-LD block — preserve verbatim
            transformed_chunks.append(content)

    return frontmatter + "".join(transformed_chunks)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="input", required=True, help="Source markdown file")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", dest="output", help="Destination markdown file")
    group.add_argument("--in-place", action="store_true", help="Rewrite the input file in place")
    args = parser.parse_args(argv)

    src = Path(args.input)
    if not src.exists():
        print(f"smart_quotes: input file not found: {src}", file=sys.stderr)
        return 2

    raw = src.read_text(encoding="utf-8")
    try:
        result = transform(raw)
    except ValueError as e:
        print(f"smart_quotes: {e}", file=sys.stderr)
        return 3

    dst = src if args.in_place else Path(args.output)
    dst.write_text(result, encoding="utf-8")
    print(f"smart_quotes: wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
