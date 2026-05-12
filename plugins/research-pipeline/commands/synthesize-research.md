---
description: Build thematic maps and writing perspectives from your library
argument-hint: [library-name]
---

Load the research-synthesizer skill and run the full synthesis pipeline on the library
named "$ARGUMENTS" (or the most recently used library if no name given).

Steps:
1. Page through all citations in the library from Supabase
2. Build a theme inventory and identify patterns
3. Generate a Mermaid thematic tree diagram
4. Validate the diagram and present for user review
5. Walk through the 4-step perspective architect (writing angle, audience, sub-themes, final JSON)
6. Persist everything to Google Drive and Supabase
