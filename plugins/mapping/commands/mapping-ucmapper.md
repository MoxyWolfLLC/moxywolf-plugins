---
description: Extract a UCF Authority Document into a citations JSON + HTML hierarchy viewer
allowed-tools: Read, Write, Edit, Bash, WebSearch, WebFetch, AskUserQuestion
---

The user wants to extract a Unified Compliance Framework Authority Document from the public UCF mapper.

Read the ucmapper skill at `${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/SKILL.md` and follow its procedure exactly, in order, without skipping the schema reconnaissance in step 0 or the parity check in step 5.

Resolve the two inputs first:

- **AD_ID** — take it from the user's message if they gave an id or a `https://mapper.unifiedcompliance.com/public-comment/index/{AD_ID}` URL. If they gave neither, ask for it.
- **OUTPUT_FOLDER** — always ask, every run. There is no default. Create it if it doesn't exist and confirm the resolved absolute path before writing anything.

$ARGUMENTS
