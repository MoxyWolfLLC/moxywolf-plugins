# Authorship Record Schema

The authorship record is the legal and creative backbone of every Editorial Forge project. It documents every editorial decision the human author made — demonstrating copyrightable selection, coordination, and arrangement of AI outputs.

## File Location

`authorship-record.json` at the project root.

## Schema

```json
{
  "project": "Project Name",
  "project_type": "book|strategy|single-piece",
  "authors": [
    {
      "name": "Author Name",
      "role": "primary_author|contributing_author|editor"
    }
  ],
  "created": "ISO-8601 timestamp",
  "last_updated": "ISO-8601 timestamp",
  "environment": {
    "ai_model": "claude-opus-4-6",
    "ai_model_version": "2026-04-08",
    "plugin": "editorial-forge",
    "plugin_version": "0.1.0",
    "tools_used": ["google_drive_search", "google_drive_fetch"],
    "additional_plugins": ["voice-architect"]
  },
  "decisions": []
}
```

## Decision Entry Schema

Every editorial decision gets an entry in the `decisions` array:

```json
{
  "id": "d-NNN",
  "timestamp": "ISO-8601",
  "phase": "intent|structure|voice|writing|verification",
  "type": "decision_type",
  "author": "Author Name",
  "ai_model": "model-identifier",
  "ai_model_version": "version-string",
  "plugins_active": ["editorial-forge"],
  "tools_used": ["tool1", "tool2"],
  "description": "What was decided — human-readable summary",
  "context": "Why — the author's reasoning for this decision"
}
```

### Required Fields
- `id`: Auto-incrementing, format `d-NNN`
- `timestamp`: ISO-8601, always UTC
- `phase`: Which phase this decision occurred in
- `type`: Decision type (see types below)
- `author`: Name of the human who made the decision
- `description`: What was decided

### Required Provenance Fields
- `ai_model`: The AI model active when this decision was made
- `ai_model_version`: Version string of the model
- `plugins_active`: List of all active plugins during this decision
- `tools_used`: List of tools invoked in this decision's context

### Optional Fields
- `context`: The author's stated reasoning (strongly recommended)
- `chapter`: Which chapter this decision relates to
- `question`: For voice injection answers, the question that was asked
- `answer`: For voice injection answers, the author's response
- `original`: For passage rejections, the original text that was rejected
- `replacement_direction`: For passage rejections, what the author directed instead

## Decision Types

### Intent Phase
- `thesis_defined` — Author defined the work's core argument
- `reader_defined` — Author specified the target reader
- `refusal_defined` — Author stated what the work is NOT
- `stakes_defined` — Author articulated consequences of ignoring the work
- `authority_defined` — Author stated their credibility basis

### Structure Phase
- `source_material_ingested` — Original AI content loaded for review
- `section_selected` — Author chose to keep a proposed section
- `section_rejected` — Author chose to remove a proposed section (include reason)
- `section_rearranged` — Author changed the order or grouping
- `section_merged` — Author combined multiple sections
- `section_split` — Author divided a section into multiple parts
- `section_created` — Author added a section not in the original
- `structure_approved` — Author approved the final structure
- `throughline_approved` — Author approved the book-level DOB arc

### Voice Phase
- `voice_interview_answer` — Author answered a voice extraction question
- `voice_profile_generated` — Voice profile created from interview
- `voice_profile_validated` — Author confirmed the profile sounds like them
- `voice_profile_imported` — Existing profile imported from another project
- `voice_profile_updated` — Profile revised based on author feedback

### Writing Phase
- `dob_mapped` — DOB arc mapped for a chapter
- `dob_approved` — Author approved chapter DOB mapping
- `dob_modified` — Author changed the DOB mapping
- `voice_qa_answer` — Author answered a chapter-specific voice question
- `draft_generated` — AI generated a chapter draft
- `passage_approved` — Author approved a passage as-is
- `passage_rejected` — Author flagged a passage for revision
- `passage_refined` — Passage revised based on author direction
- `chapter_approved` — Author approved a complete chapter

### Verification Phase
- `voice_audit_complete` — Voice consistency check finished
- `dob_audit_complete` — DOB integrity check finished
- `antidetection_audit_complete` — Anti-detection checklist passed
- `provenance_summary_generated` — Human-readable authorship summary created

## Writing an Entry

When logging a decision:

1. Generate the next `id` by reading the current highest ID and incrementing
2. Set `timestamp` to current UTC time
3. Set `ai_model` and `ai_model_version` to the currently active model
4. Set `plugins_active` to all currently loaded plugins
5. Set `tools_used` to tools invoked in this specific interaction
6. Write a clear `description` — someone reading this in a year should understand what happened
7. Include `context` whenever the author states WHY they made a decision

## Provenance Summary

Phase 5 generates a human-readable summary from the authorship record. Format:

```markdown
# Creative Provenance: [Project Name]

## Authors
- [Name] ([Role]) — [N] editorial decisions logged

## Timeline
- Project started: [date]
- Intent defined: [date range]
- Structure finalized: [date]
- Voice profile created: [date]
- Writing completed: [date range]
- Verification: [date]

## Editorial Decisions Summary
- **Intent phase**: [N] decisions defining thesis, reader, stakes, authority
- **Structure phase**: [N] decisions — [X] sections selected, [Y] rejected, [Z] rearranged
- **Voice phase**: [N] interview answers, profile validated [date]
- **Writing phase**: [N] decisions across [M] chapters — [X] passages approved, [Y] revised
- **Verification**: All audits passed [date]

## AI Environment
- Primary model: [model] [version]
- Plugin: editorial-forge [version]
- Tools: [list]

## Key Editorial Judgments
[Top 10 most significant decisions, each with description and author reasoning]
```
