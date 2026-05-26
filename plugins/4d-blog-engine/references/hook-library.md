---
read_when: "Phase 4 (Diligence) loads this when generating the LinkedIn teaser and the article's opening hook. Six named formulas with templates."
status: canonical
based_on: "Crawl synthesis from founder-os/hook-creation, naveedharri/benai-skills (80+ template library), jamon8888/cc-suite, RanNahmany/writing-linkedin-posts, hanamizuki/solopreneur, agricidaniel/claude-blog."
---

# Hook library — 6 named formulas for LinkedIn

> **Read this when:** writing a LinkedIn teaser or the first 2 lines of a LinkedIn article (Phase 4 derivative output).

The first line of a LinkedIn post is the *single* most important sentence — it must land before character 210 (the "See more" fold on mobile). LinkedIn's algorithm uses dwell time as the dominant 2026 signal; if the reader doesn't unfold, nothing else matters.

This file is 6 named formulas with templates. **Generate 3 candidate hooks before picking one. Show all 3 with the chosen one marked.** Use a template's exact sentence structure — do not paraphrase. The templates work because their specific structures are psychologically proven (naveedharri/benai-skills).

## Six formulas

### 1. Stat-Led

**Structure:** Specific number + counter-intuitive implication.
**Template:**
```
{{ number }} of {{ population }} {{ action }}. Only {{ smaller number }} {{ counter-intuitive outcome }}.
```
**Examples that work:**
- "78% of organizations have adopted AI. Only 1% have reached operational maturity."
- "11,556 verbs sit in our dictionary. 3,333 are still waiting on human judgment a system couldn't supply."
- "Sold my shares back for one dollar. I was the largest single shareholder."

**Rules:** Number must be verifiable, not invented. Counter-intuitive part must be the actual gap, not a rhetorical flourish. Best for posts where the data IS the argument.

---

### 2. Question

**Structure:** A question the reader can't answer cleanly, in a room where they'd be expected to.
**Template:**
```
{{ Authority figure }} asked {{ named reader }} a question that should have been straightforward: {{ the question, verbatim }}.
```
**Examples that work:**
- "Maya's board asked her a question that should've been straightforward: where, exactly, is AI making the company operationally better?"
- "When the CTO said 'we're AI-first,' what's the discernment gate?"
- "Your board sees the demo. What did they not see?"

**Rules:** The question must be one the reader has actually been asked or could be asked. Never rhetorical. Never a question Claude would invent for narrative effect. Best when the post's whole point is "this question doesn't have a clean answer yet."

---

### 3. Story (opener-as-scene)

**Structure:** A specific moment, specific people, specific date. Concrete enough to be falsifiable.
**Template:**
```
{{ Time anchor }}, {{ named person }} {{ specific action }}. {{ The unexpected consequence in one line }}.
```
**Examples that work:**
- "A year ago I sold my shares in a company I'd co-founded. The price was one dollar."
- "Last week, the first batch of import tests came back clean. The system looked done. Then we ran a real dataset through it."
- "October 2025: the CTO didn't stay much longer than I did."

**Rules:** The scene must be a real scene the author lived through. The unexpected-consequence line must be specific (a number, a name, a verb you can picture). Never generic ("things got hard"). Best for posts where the author has direct experience and the story IS the evidence.

---

### 4. Contrarian

**Structure:** Name the consensus, then name the specific thing it gets wrong.
**Template:**
```
Everyone thinks {{ widely held belief, stated precisely }}. The data say {{ specific contrary fact }}.
```
**Examples that work:**
- "Everyone thinks prompt engineering is the curriculum. It's a quarter of a quarter."
- "Most AI consulting teams sell 'AI fluency.' What they actually deliver is a prompt-engineering workshop."
- "The frontier-founder thesis says automation replaces humans. Raisch and Krakowski found the opposite."

**Rules:** The consensus must be one a real reader would recognize and nod to. Never invent a strawman to knock down. The contrary fact must be sourced (FLOW evidence triple required). Best for posts arguing against a widely held position.

---

### 5. Bold Claim

**Structure:** A single declarative sentence stated without hedging.
**Template:**
```
{{ Subject }} {{ does/is }} {{ specific outcome }}.
```
**Examples that work:**
- "The bottleneck has moved from making the work to validating it."
- "Foundation models are valuable and entirely non-rare."
- "The company that wins the AI era won't be the one with the best models or the best prompts."

**Rules:** No hedging. No "I think" / "It seems" / "Perhaps." The claim must be defensible in the post body. Best for posts where the whole argument compresses into one sentence and you can defend it across the next 800 words.

---

### 6. Pattern Interrupt

**Structure:** A line that breaks the expected register of a LinkedIn post — abruptly short, unexpectedly personal, or formally precise where the platform expects warmth.
**Template:**
```
{{ A single concrete sentence that doesn't sound like a LinkedIn opener }}.
```
**Examples that work:**
- "The H is being taken out of the loop."
- "I watched the H come out of the loop."
- "A staircase doesn't make anyone able to climb."

**Rules:** Must NOT use any of the standard LinkedIn opener templates above. Must feel like the start of an essay, not a post. Best when the post needs literary weight — usually a piece making a longer thematic argument.

---

## Hooks to retire (do not generate)

From multiple crawl sources (jamesgray007/hoai-course, RanNahmany, hanamizuki, founder-os). These are killed on sight:

- "This one thing made me $X" / "This one trick…"
- "The CEO pulled me aside…"
- "I'm excited to announce…" / "I'm thrilled to share…"
- "Most people don't realize…" / "Nobody tells you…" / "Here's what they're missing…"
- "I've been wrong about…" (manufactured-humility pattern)
- "Welcome to this week's edition…" / "Happy [day]!" / "Before we get started…"
- "Sound familiar?" / "Here's the thing:" / "The catch?"
- Generic CTAs as the opener: "Comment YES if…" / "DM me if you…"

If a generated hook matches any of these, reject and regenerate.

## Output contract (Phase 4)

When the plugin generates the LinkedIn teaser, the artifact `04-diligence/linkedin-teaser.md` carries this structure:

```markdown
# LinkedIn Teaser — [post slug]

## Selected hook (Formula: {{ formula_name }})
> {{ hook text — 1 or 2 sentences, under 210 chars combined }}

## Alternates considered (rejected)
- Formula: {{ formula_name }} — {{ rejected hook }} — **Why rejected:** {{ one-line reason }}
- Formula: {{ formula_name }} — {{ rejected hook }} — **Why rejected:** {{ one-line reason }}

## Body
{{ teaser body, 800-1200 chars total including hook, 1 earned-secret-anchored line in the middle, ends with a SPECIFIC question — never "What do you think?" or "Agree?" }}

## Posting metadata
- Hashtags: 0-3 max, at the very end after a line break.
- Link placement: blog URL goes in the **first comment**, not in the body.
- Best posting window: Tue/Wed/Thu, 7:30-8:30 AM PT.
```

## Article opening (versus teaser hook)

A long-form LinkedIn **article** (the full mirror) opens differently from a teaser **post**. The article gets the full first paragraph (3-5 sentences) to set up the angle; the post gets one or two sentences before the fold. Use the same formula table for both, but for the article allow Formula 3 (Story) to run longer and pair it with Formula 5 (Bold Claim) as the second beat.

## The character-210 rule (mobile fold)

LinkedIn's mobile "See more" fold cuts at approximately character 210 (sometimes 200 depending on emoji/punctuation density). The first 210 chars MUST:

- Land the hook completely (no cliffhanger mid-sentence).
- Carry a curiosity trigger — the reader cannot guess what comes next from these 210 chars alone.
- Be free of "see more" filler ("Read the full story below 👇" — banned).

Phase 4 enforces a hard char count: if the hook + curiosity-trigger does not land by char 210, regenerate.
