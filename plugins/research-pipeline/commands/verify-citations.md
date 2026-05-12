---
description: Run 4-layer citation verification on a research library
argument-hint: [library-name]
---

Load the citation-verifier skill and run the full verification pipeline on the library
named "$ARGUMENTS" (or the most recently used library if no name given).

Steps:
1. Look up the library in `research_libraries` by name
2. Count unverified citations
3. Run all four verification layers: DOI (CrossRef/DataCite), arXiv, semantic matching, LLM relevance
4. Update citations in Supabase with verification results
5. Present the verification report to the user
