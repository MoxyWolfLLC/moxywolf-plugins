---
description: "Extract a UCF Authority Document into a citations JSON + HTML hierarchy viewer. Usage: /mapping-ucmapper <AD_ID | mapper URL> [output folder]"
argument-hint: <AD_ID | mapper URL> [output folder]
allowed-tools: Read, Write, Edit, Bash, WebSearch, WebFetch, AskUserQuestion
---

The user wants to extract a Unified Compliance Framework Authority Document from the public UCF mapper.

## Resolve the inputs first

The user's argument, verbatim, is:

$ARGUMENTS

Parse **AD_ID** out of it. Accept any of these forms and normalise to the bare numeric id:

- a bare id — `4528`
- a full mapper URL — `https://mapper.unifiedcompliance.com/public-comment/index/4528` (the id is the last path segment)
- an id with surrounding prose — `extract 4528 please`
- an id followed by a path — `4528 ~/Documents/ucf/4528` (see the folder rule below)

If the argument is empty, or you cannot find a number in it, **ask for the AD id**. Do not guess one, and never carry over an id from earlier in the conversation or from the skill's worked example — the example document is 4524, and silently extracting 4524 when the user meant something else produces a confidently wrong result. Every invocation gets a freshly parsed id.

Echo the resolved id back before doing any work, so a misparse is caught in one line rather than after a 5 MB fetch.

**OUTPUT_FOLDER**: if the argument includes a path alongside the id, use it and confirm the resolved absolute path. Otherwise **ask** — there is no default. Either way, create the folder if it doesn't exist and confirm where the files will land before writing anything.

## Then run the procedure

Read the ucmapper skill at `${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/SKILL.md` and follow it exactly, in order. Do not skip the schema reconnaissance in step 0 — each Authority Document is a fresh document whose shape has to be confirmed rather than assumed — and do not skip the parity check in step 5.
