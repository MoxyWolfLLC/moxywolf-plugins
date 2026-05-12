---
description: Convert pasted VTT captions to a clean text file
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

The user wants to convert VTT closed caption content into a clean text file.

Read the vtt-to-text skill at `${CLAUDE_PLUGIN_ROOT}/skills/vtt-to-text/SKILL.md` and follow its instructions to process the VTT content the user has provided.

If the user included VTT content in their message, use it directly. If not, ask them to paste the VTT content.
