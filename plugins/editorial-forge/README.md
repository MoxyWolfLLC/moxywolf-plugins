# Editorial Forge

Transform AI-generated content into authentically author-owned work through structured editorial judgment, voice extraction, and Sorkin DOB narrative framing.

## What It Does

Editorial Forge inverts the typical AI writing workflow. Instead of generating first and editing after, it captures the author's intent, editorial judgment, and voice FIRST — then uses AI as scaffolding. Every editorial decision is logged in an authorship record that documents the human's copyrightable contribution.

Built on the legal reality that under US copyright law, the author's **selection, coordination, and arrangement** of AI outputs — not the outputs themselves — is the copyrightable act.

## Components

### Skills

- **editorial-forge** — Main orchestrator. Manages the five-phase workflow: Intent Mapping, Structure Scaffolding, Voice Extraction, Chapter Writing with DOB, and Verification. Handles asymmetric Q&A (questions that may take days to answer) with full state persistence in Google Drive.

- **voice-architect** — Builds author voice profiles through an 8-question structured interview. Captures how the author argues, their sentence rhythm, vocabulary, emotional patterns, and forbidden phrases. Profiles are per-project but can be imported across projects.

### Commands

- `/forge-start` — Initialize a new authoring project. Creates the Google Drive folder structure, initializes the authorship record, and begins Phase 1.
- `/forge-resume` — Resume an existing project. Reads the manifest, re-presents any pending questions with context, and picks up where you left off.
- `/forge-status` — Show current project status including phase, progress, pending questions, and editorial decision count.

## The Five Phases

1. **Intent Mapping** — Author defines thesis, reader, stakes, and authority through 5 structured questions
2. **Structure Scaffolding** — AI proposes organization; author selects, rejects, and rearranges with every decision logged
3. **Voice Extraction** — 8-question interview builds the author's voice profile (per-project, importable)
4. **Chapter Writing** — Sorkin DOB mapping + chapter-specific Q&A + prose generation + passage-level refinement
5. **Verification** — Voice consistency audit, DOB integrity check, anti-detection audit, authorship record compilation

## Key Features

- **Authorship Record** — JSON log of every editorial decision with AI model, version, plugins, and tools captured per-decision
- **Sorkin DOB** — Desire-Obstacle-Battle narrative framework at chapter level with book-level throughline
- **Counter-Playbook DOB** — Specialized pattern for adversarial structures (e.g., opposing framework's rules as Obstacles)
- **Asymmetric Q&A** — State persists in Google Drive; questions can take hours or days to answer
- **Voice Profiles** — Per-project, importable via drag-and-drop, built from structured interview
- **No Preset Voice** — Voice is always extracted from the author, never applied from a template (unless explicitly requested)

## Project Types

- **Book** — Multi-chapter with `03-chapters/` directory
- **Strategy Document** — Structured sections with `03-sections/` directory
- **Single Piece** — Articles, whitepapers, guides with `03-draft/` directory

## Setup

No external services or API keys required. Uses Google Drive for state persistence via the Google Drive MCP tools.
