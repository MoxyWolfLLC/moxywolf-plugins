---
name: content-writer
description: >
  Write research-backed articles using Sorkin's Desire-Obstacle-Battle narrative framework,
  MoxyWolf brand voice, and voice injection interview. The final stage of the research
  pipeline — transforms a verified, synthesized research library into publication-ready
  content. Use this skill whenever the user says "write the article," "write a blog post,"
  "turn this into content," "draft the post," "write from my research," "create the blog,"
  or any request to produce written content from an existing research library with a defined
  perspective. Also trigger after the research-synthesizer skill completes and a perspective
  has been stored. This skill should always be used for STIGViewer blog content and any
  MoxyWolf publication.
version: 0.1.0
---

# Content Writer

The final stage of the research pipeline. Takes a verified research library, a thematic
map, and a writing perspective — and produces a publication-ready article using Sorkin's
Desire-Obstacle-Battle narrative structure, MoxyWolf voice, and the voice injection
interview process.

## Prerequisites

- A research library in Supabase with verified citations
- A thematic map (from research-synthesizer)
- A writing perspective (topic, audience, angle, sub-themes)
- Supabase MCP for reading citations
- Google Drive MCP for uploading final article

## The Three Layers

Every article produced by this skill combines three layers:

1. **Sorkin DOB Structure** — the narrative architecture
2. **MoxyWolf Voice** — the style mechanics
3. **Voice Injection** — the human story underneath

None of these layers is optional. An article without DOB structure reads like an essay.
Without MoxyWolf voice it sounds like AI. Without voice injection it sounds like anyone.
All three together produce content that's structurally compelling, stylistically authentic,
and personally grounded.

## Phase 1: Gather Inputs

### From Supabase

Pull the research library, thematic map, and perspective:

```sql
-- Get the perspective
SELECT * FROM research_perspectives WHERE library_id = {id} ORDER BY created_at DESC LIMIT 1;

-- Get the thematic map
SELECT * FROM thematic_maps WHERE library_id = {id} ORDER BY created_at DESC LIMIT 1;

-- Get all citations sorted by relevance
SELECT * FROM citations WHERE library_id = {id} ORDER BY llm_relevance DESC NULLS LAST;
```

### From the User: Voice Injection Interview

Before writing a single word, conduct the 8-question voice injection interview.
Ask one question at a time. Wait for the answer before moving to the next.

1. **The Trigger**: "What triggered this? What conversation, client situation, or
   frustration made you want to write about this right now?"

2. **The Evidence**: "Give me a real example. A specific conversation, project, or
   moment where this played out. Names can be changed, but the story has to be real."

3. **The Contrarian Take**: "What do most people get wrong about this? Where's the
   conventional wisdom broken?"

4. **The Authority**: "Why should anyone listen to you on this? What experience shapes
   how you see this differently?"

5. **The Specific Reader**: "Who specifically is reading this, and what are they staring
   at right now that makes them need it?"

6. **The Business Connection**: "How does this connect to what MoxyWolf / STIGViewer
   is building?"

7. **The Call to Action**: "What should someone DO after reading this?"

8. **The Emotional Core**: "What pisses you off, excites you, or worries you about
   this topic?"

If voice injection answers were already provided earlier in the session, skip the
interview and use those answers directly.

## Phase 2: Map the DOB Arc

Using the thematic map, perspective, and interview answers, identify:

### Desire

What the reader wants. Not abstractly — viscerally.

- Win contracts. Keep their job. Prove their security posture.
- Pass the audit. Meet the deadline. Stop the bleeding.
- Connect it to the emotional core from Question 8.

The Desire comes from the interview answers — the practitioner who cried, the CISO
staring at 320 controls, the contractor worried about exclusion.

### Obstacle

What stands in the way. This is where the research data lives.

- Map the obstacle to specific themes from the thematic map
- Use the cost data, the deficiency studies, the tool fragmentation
- Make it concrete with numbers from the citations
- The contrarian take from Question 3 sharpens the obstacle

### Battle

The conflict when desire meets obstacle. This is where the ecosystem is right now.

- New solutions emerging but the fight isn't won
- Automation exists but adoption is uneven
- The regulatory framework is in place but the infrastructure layer is missing
- The business connection from Question 6 lives here — subtly

### The Ending: Unresolved

Sorkin doesn't resolve cleanly. Neither do we.

- Leave the reader mid-battle with a choice to make
- Frame it as competitive: "before your competitor does"
- Use a timeline deadline to create urgency (October 2026, November 2026)
- DO NOT pitch a product. DO create the space where the reader connects the dots.

## Phase 3: Write the Draft

### Structure

```
# [Stakes-Driven Headline]

[Opening hook — 2-3 paragraphs establishing desire through a real story
from the voice injection interview. The trigger, the evidence, the person.]

## [Thematic section — not "Act I"]

[Rising action — the obstacle becomes clear. Research data, cost numbers,
specific failures. The contrarian take lands here.]

## [Thematic section]

[Battle intensifies — ecosystem shifts, automation emerges, but the gap
persists. The "what's missing" argument builds.]

[Ending — unresolved tension. Competitive pressure. Timeline deadline.
The reader is left with a decision, not a conclusion.]

---

*[Author bio with authority from Question 4. Link to STIGViewer.com.]*

---

## References

[Full Chicago-style bibliography with URLs for every cited source]
```

### Headline Formula

Capture DOB tension in the headline:

- [Vivid situation] + [Stakes/tension]
- [Old world] vs [New reality]
- [Specific number] + [Dramatic consequence]

Examples from existing blog:
- "The Audit That Outgrew the Checklist: When Paperwork Stopped Being Enough"
- "847 Findings, Zero Context"
- "Your Spreadsheet Died 18 Days Before Your Audit"

### Citation Integration

Weave citations naturally into prose using (Author/Organization, Year) format.
Never use bracketed numbers [1][2] in the published article.

- "Sundararajan, Ghodousi, and Dietz (2022) analyzed 127 contractors and found..."
- "Atlantic Digital (2025) projects $487,970 over three years..."
- Direct quotes must be under 15 words for copyright compliance

### Bibliography

Every article ends with a full References section in University of Chicago style:

```
Author/Organization. "Title." *Publication*, Year. [URL](URL).
```

Pull bibliography entries from the citations table. Include every source cited in
the article. Alphabetize by author/organization surname.

## Phase 4: Apply MoxyWolf Voice

### Mandatory Style Rules

**Contractions**: Use in 80%+ of opportunities. "doesn't," "can't," "it's," "they're."
Reserve the remaining 20% for deliberate emphasis: "This is not optional."

**Sentence architecture**: Vary length aggressively. Some sentences: four words. Others
unspool across forty, building through clauses before arriving at their point.

**Fragments**: Use deliberately. For emphasis. The way actual writers do.

**Conjunctions as starters**: Start sentences with And, But, Or at least once per section.

**Paragraph length**: Vary dramatically. Include single-sentence paragraphs alongside
longer blocks.

**Specificity over abstraction**: Replace "significant cost reduction" with actual
numbers. Replace "organizations across industries" with named examples.

### Forbidden Phrases (AI tells — never use)

- "It's worth noting that..."
- "It's important to understand..."
- "In today's rapidly changing..."
- "At its core..."
- "This is particularly true when..."
- "Moving forward..."
- "In order to..." (just use "to")
- "That being said..."

### Forbidden Transitions

- Furthermore → And, Plus, or delete
- Additionally → And, or delete
- Moreover → What's more, or delete
- In conclusion → Just conclude
- Nevertheless → But, Still, Yet

### Punctuation

- ALWAYS use typographer's quotes: "curly" not "straight"
- NEVER use em dashes (—). Use spaced en-dashes " – " sparingly.

## Phase 5: Anti-Detection Checklist

Before delivering, verify every item:

- [ ] Contractions in 80%+ of opportunities
- [ ] No forbidden phrases
- [ ] No formulaic transitions
- [ ] Sentence length varies dramatically (4-word and 40-word present)
- [ ] At least one fragment per section
- [ ] Parallelism broken (not everything in threes)
- [ ] Specific examples replace abstract claims
- [ ] Paragraphs vary in length (single-sentence paragraphs present)
- [ ] Sentences start with And, But, Or in each section
- [ ] No em dashes — only spaced en-dashes
- [ ] Typographer's quotes throughout
- [ ] DOB arc is clear (desire → obstacle → battle → unresolved)
- [ ] Ending leaves reader mid-battle with a decision
- [ ] Every factual claim has (Author, Year) citation
- [ ] Bibliography at end with URLs

## Phase 6: Refinement

After presenting the draft, invite passage-level feedback. For each passage the user
flags, ask:

- **"Too generic"** → "What specific example or detail from your experience should
  replace this?"
- **"Too soft"** → "What's the stronger version? What would you say to someone's face?"
- **"Not how I'd say it"** → "Read it aloud. What words feel wrong?"
- **"Needs a story here"** → "Tell me the story. Who was involved? What happened?"
- **"Unpack this"** → Create a P.S. section with technical deep-dive

Iterate until the user approves.

## Phase 7: Deliver and Persist

1. Save final article as markdown to Google Drive
2. Offer to generate a .docx version
3. Offer to generate a blog header image (MoxyWolf brand colors)
4. Store the article metadata in Supabase for the content ecosystem pipeline

## Reference

- **`references/dob-examples.md`** — Before/after transformation examples for
  opening hooks, citation embedding, visceral stakes, and unresolved endings
