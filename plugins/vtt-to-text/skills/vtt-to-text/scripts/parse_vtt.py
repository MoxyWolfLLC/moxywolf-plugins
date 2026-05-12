#!/usr/bin/env python3
"""
VTT to clean text converter.

Reads WebVTT content from stdin, strips all formatting (headers, timestamps,
sequence numbers), and outputs flowing paragraph text to stdout.

Usage:
    python parse_vtt.py < input.vtt > output.txt
    cat input.vtt | python parse_vtt.py
"""

import re
import sys


def parse_vtt(vtt_content: str) -> str:
    """Parse VTT content and return clean flowing paragraph text."""
    lines = vtt_content.strip().split("\n")

    # Patterns to skip
    timestamp_pattern = re.compile(
        r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}"
    )
    sequence_pattern = re.compile(r"^\d+$")

    # Extract only the spoken text lines
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.startswith("NOTE"):
            continue
        if timestamp_pattern.match(line):
            continue
        if sequence_pattern.match(line):
            continue
        if line.startswith("STYLE") or line.startswith("::cue"):
            continue
        # Strip inline VTT tags like <v>, <c>, <b>, <i>, etc.
        line = re.sub(r"<[^>]+>", "", line)
        text_lines.append(line)

    # Join all text lines into a continuous stream
    raw_text = " ".join(text_lines)
    raw_text = re.sub(r"\s+", " ", raw_text).strip()

    # Split into paragraphs at sentence boundaries (~5 sentences each)
    sentences = re.split(r"(?<=[.!?])\s+", raw_text)

    paragraphs = []
    current = []
    for sentence in sentences:
        current.append(sentence)
        if len(current) >= 5:
            paragraphs.append(" ".join(current))
            current = []

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def main():
    vtt_content = sys.stdin.read()
    if not vtt_content.strip():
        print("Error: No input received. Pipe VTT content via stdin.", file=sys.stderr)
        sys.exit(1)

    result = parse_vtt(vtt_content)
    print(result)


if __name__ == "__main__":
    main()
