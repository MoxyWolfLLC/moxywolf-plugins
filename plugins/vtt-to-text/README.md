# VTT to Text

Converts pasted WebVTT (.vtt) closed caption content into clean, readable text files. Built for converting course lecture captions into study-friendly transcripts.

## Components

- **Skill: vtt-to-text** — Triggers automatically when VTT content is pasted into a conversation. Strips timestamps, sequence numbers, and formatting, then merges caption fragments into flowing paragraphs.
- **Command: /convert-vtt** — Manually invoke the converter if the skill doesn't auto-trigger.

## Usage

1. Paste VTT caption content into the chat
2. When prompted, provide the tier name (e.g., "Tier 3") and class name (e.g., "Introduction")
3. The plugin saves a clean text file named like `Tier 3 - Introduction.txt` to your workspace folder

## Requirements

- Python 3 (available in the Cowork sandbox by default)
