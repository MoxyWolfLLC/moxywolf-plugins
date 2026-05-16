---
name: citation-verifier
description: >
  Four-layer citation verification system inspired by AutoResearchClaw. Validates references
  against CrossRef, DataCite, arXiv, and Semantic Scholar APIs, then runs semantic matching
  and LLM relevance scoring. Catches hallucinated or broken references before they reach
  published content. Use this skill whenever the user says "verify my citations," "check my
  references," "validate my bibliography," "are these citations real," "citation audit,"
  "reference check," "verify DOIs," "check for hallucinated references," or any request to
  validate the authenticity and relevance of academic references. Also trigger when the user
  mentions citation quality, broken DOIs, or reference integrity.
version: 0.1.0
---

# Citation Verifier

Four-layer verification system that validates every citation in a research library against
external APIs and semantic analysis. Modeled on AutoResearchClaw's citation integrity system.

## Prerequisites

- **Supabase MCP** — reading/writing citations table
- **`WebFetch` (built-in) and `Bash` (curl)** — for CrossRef, DataCite, arXiv, and Semantic Scholar API calls. All four APIs are public, no auth required for read-only verification.

## The Four Verification Layers

### Layer 1: DOI Verification (CrossRef + DataCite)

For citations with a `doi` field:

```
CrossRef API: https://api.crossref.org/works/{doi}
DataCite API: https://api.datacite.org/dois/{doi}
```

Check:
- Does the DOI resolve? (HTTP 200)
- Does the returned title match the citation title? (fuzzy match, >80% similarity)
- Do the authors match? (at least one surname overlap)
- Does the year match? (exact or ±1)

Scoring:
- DOI resolves + title match + author match = `doi_verified: true`
- DOI resolves but metadata mismatch = flag for manual review
- DOI does not resolve = `doi_verified: false`, log the failure

### Layer 2: arXiv Verification

For citations with an `arxiv_id` field:

```
arXiv API: https://export.arxiv.org/api/query?id_list={arxiv_id}
```

Check:
- Does the arXiv ID return a valid entry?
- Does the title match?
- Do the authors match?

Scoring:
- Valid entry + matches = `arxiv_verified: true`
- Valid entry but mismatch = flag as potentially wrong ID
- Invalid entry = `arxiv_verified: false`

### Layer 3: Semantic Matching

For citations that passed Layer 1 or 2, compare the stored abstract against the
abstract returned by the API:

- Compute a semantic similarity score (use embeddings if available, or fall back to
  keyword overlap using Jaccard similarity on significant terms)
- Threshold: score > 0.7 = confirmed match
- Score 0.4-0.7 = partial match, flag for review
- Score < 0.4 = likely mismatch despite DOI/arXiv match

Store as `semantic_score` on the citation.

### Layer 4: LLM Relevance Assessment

For each citation in the library, assess whether it's actually relevant to the
library's stated topic:

Take the library description/name + the citation's title and abstract. Ask:
"On a scale of 0 to 1, how relevant is this citation to the research topic
[library name]? Consider whether it directly addresses the topic, provides
supporting methodology, offers contrasting evidence, or is tangentially related."

Score thresholds:
- 0.8-1.0: Highly relevant, core citation
- 0.5-0.8: Supporting reference
- 0.2-0.5: Tangentially related
- 0.0-0.2: Likely irrelevant or wrong library

Store as `llm_relevance` on the citation.

## Execution Process

### Step 1: Scope the verification

Query the citations table for the target library:

```sql
SELECT id, citation_key, title, doi, arxiv_id, verification_status
FROM citations
WHERE library_id = {id} AND verification_status = 'unverified'
ORDER BY id
```

Report to the user: "Found [X] unverified citations in [library name]. Running
4-layer verification — this may take a few minutes for large libraries."

### Step 2: Run Layers 1-2 (API verification)

Process citations in batches of 10 to respect API rate limits.

For each citation:
1. If DOI exists → run Layer 1
2. If arXiv ID exists → run Layer 2
3. If neither exists → mark as `needs_discovery` and suggest the user run
   literature discovery to find proper identifiers

Rate limiting:
- CrossRef: max 50 requests/second (polite pool with `mailto` header)
- arXiv: max 1 request/3 seconds
- DataCite: max 10 requests/second

Add a `User-Agent` or `mailto` parameter for CrossRef polite pool access.

### Step 3: Run Layer 3 (Semantic matching)

For citations that passed Layer 1 or 2, compare abstracts. Use the Supabase
embeddings if available, or generate on-the-fly using the OpenAI embeddings endpoint.

### Step 4: Run Layer 4 (LLM relevance)

Batch citations into groups of 5-10 for efficient LLM assessment. Use a single
prompt that evaluates the batch together for consistency.

### Step 5: Update and Report

Update each citation in Supabase:

```sql
UPDATE citations SET
  verification_status = CASE
    WHEN doi_verified OR arxiv_verified THEN 'verified'
    WHEN (doi IS NOT NULL AND NOT doi_verified) OR (arxiv_id IS NOT NULL AND NOT arxiv_verified) THEN 'failed'
    ELSE 'unverified'
  END,
  doi_verified = ...,
  arxiv_verified = ...,
  semantic_score = ...,
  llm_relevance = ...,
  verification_log = ...,
  verified_at = now()
WHERE id = ...
```

### Verification Report

Present results as:

```
Citation Verification Report for: [Library Name]
═══════════════════════════════════════════════

Total citations checked: [X]

Verified:     [Y] ([%])  — DOI/arXiv confirmed, metadata matches
Failed:       [Z] ([%])  — DOI/arXiv exists but metadata mismatch
Unverifiable: [W] ([%])  — no DOI or arXiv ID available
Hallucinated: [V] ([%])  — DOI/arXiv does not exist at all

Relevance Distribution:
  Core (>0.8):        [count]
  Supporting (0.5-0.8): [count]
  Tangential (0.2-0.5): [count]
  Irrelevant (<0.2):    [count]

Action Items:
  - [list citations that need manual review]
  - [list citations with no identifiers that need discovery]
  - [list potentially hallucinated citations to remove or replace]
```

## Handling Failures Gracefully

- If CrossRef is down, skip Layer 1 and note it in the verification_log
- If arXiv rate limits hit, pause and retry with exponential backoff
- If a citation has no DOI and no arXiv ID, don't mark it as failed —
  mark it as `unverified` with a note suggesting literature discovery
- Never auto-delete citations; always present findings and let the user decide

## Reference

For the full Supabase schema, read `references/supabase-migration.sql` in the
research-pipeline skill directory.
