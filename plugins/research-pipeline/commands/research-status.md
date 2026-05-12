---
description: Show the current state of a research library
argument-hint: [library-name]
---

Load the research-pipeline skill and display the status of the library named "$ARGUMENTS".

If no name given, list all available libraries and their summary stats.

Run `get_library_stats()` via Supabase and present:
- Citation counts and verification breakdown
- Source diversity
- Thematic maps and perspectives count
- Open research gaps
- Recommended next actions based on current state
