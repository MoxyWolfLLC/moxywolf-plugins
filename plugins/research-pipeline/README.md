# Research Pipeline Plugin

End-to-end research-to-publication pipeline for Cowork. Start with a topic — not
a file. Everything runs in conversation, from literature discovery through published
article with bibliography.

## What It Does

Takes you from a research question to a published, voice-injected article:

1. **Discover** — Search academic + industry + government sources via API engine AND multi-model swarm (Perplexity, Gemini, DeepSeek via OpenRouter)
2. **Verify** — 4-layer citation verification (DOI, arXiv, semantic, LLM relevance)
3. **Synthesize** — Build Mermaid thematic maps + define your writing perspective
4. **Write** — Sorkin DOB narrative arc + MoxyWolf voice + voice injection interview + Chicago bibliography
5. **Import** (optional) — Add your own collected BibTeX references on top

## Quick Start

Just say: **"I want to research STIG automation"**

The pipeline discovers sources, verifies them, builds a thematic map, defines your
writing perspective, interviews you for voice, and produces a publication-ready article
with Sorkin's Desire-Obstacle-Battle narrative structure and a full bibliography.

## Components

### Skills

| Skill | Purpose |
|-------|---------|
| `research-pipeline` | Orchestrator — coordinates the full workflow |
| `literature-discovery` | Multi-source search + multi-model swarm — the entry point |
| `citation-verifier` | 4-layer reference validation |
| `research-synthesizer` | Thematic analysis + perspective building |
| `content-writer` | Sorkin DOB narrative + MoxyWolf voice + voice injection + bibliography |
| `import-bibtex` | BibTeX parsing + abstract enrichment (alternative entry point) |

### Commands

| Command | Description |
|---------|-------------|
| `/discover-literature` | Search for sources on a topic (new or existing library) |
| `/verify-citations` | Run citation verification on a library |
| `/synthesize-research` | Build thematic maps and perspectives |
| `/write-article` | Write a research-backed article with DOB narrative + voice injection |
| `/import-bibtex` | Import a BibTeX file (alternative to discovery) |
| `/research-status` | Show library stats and health |

## Setup

Already done. The Supabase project `research-pipeline` is live at
`https://xoiazflgpfeuxmwhmsbv.supabase.co` with all tables and functions deployed.

### Required Connections

- **Supabase MCP** — already connected
- **Google Drive MCP** — for file uploads
- **Mermaid MCP** — for diagram validation/rendering
- **Rube MCP** — for web search, API calls, and OpenRouter swarm

## Architecture

```
"I want to research [topic]"
  |
  v
/discover-literature
  |-- API Engine: OpenAlex + Semantic Scholar + arXiv + Web Search
  |-- Multi-Model Swarm: Perplexity + Gemini + DeepSeek (via OpenRouter)
  |-- Merge, deduplicate, score by cross-model agreement
      |-- Creates library -> Ingests approved sources
          |
          |-->  /verify-citations
          |      |-- CrossRef + arXiv + Semantic matching + LLM relevance
          |
          |-->  /synthesize-research
          |      |-- Theme inventory -> Mermaid diagram -> Perspective architect
          |
          |-->  /write-article
          |      |-- Voice injection interview (8 questions)
          |      |-- Sorkin DOB arc: Desire -> Obstacle -> Battle -> Unresolved
          |      |-- MoxyWolf voice + anti-detection checklist
          |      |-- Chicago bibliography with URLs
          |
          |-->  /discover-literature (again, to expand)
                 |-- Citation chaining, gap-driven search, temporal expansion

All data -> Supabase (citations, thematic_maps, research_perspectives)
All files -> Google Drive
```
