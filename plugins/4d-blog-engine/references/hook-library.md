---
read_when: "blog-social (the post-Diligence derivative skill) loads this when generating hooks for LinkedIn / Twitter / Facebook. Six named formulas with templates, plus a per-platform formula-fit table."
status: canonical
based_on: "Crawl synthesis from founder-os/hook-creation, naveedharri/benai-skills (80+ template library), jamon8888/cc-suite, RanNahmany/writing-linkedin-posts, hanamizuki/solopreneur, agricidaniel/claude-blog."
---

# Hook library — 6 named formulas for social derivatives

> **Read this when:** the blog-social skill is generating a hook for a LinkedIn teaser, a LinkedIn article opener, the first post of a Twitter thread, or a Facebook post.

The first line of any social post is the *single* most important sentence. On LinkedIn it must land before character 210 (the "See more" mobile fold). On Twitter it must fit ≤260 chars (leaving room for "🧵" or "1/"). On Facebook it must land before "See more" truncation (~roughly the first 300 chars).

This file holds 6 named formulas with templates, plus a per-platform formula-fit table so blog-social can pick formulas that land best on each platform. **Generate 3 candidate hooks per platform before picking one. Show all 3 with the chosen one marked.** Use a template's exact sentence structure — do not paraphrase. The templates work because their specific structures are psychologically proven (naveedharri/benai-skills).

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

## Which formulas land best where

The same six formulas work across platforms, but each platform has a sweet spot. Pick formulas from this table for each platform's hook candidates:

| Platform | First-choice formulas | Avoid (lands flat here) | Notes |
|---|---|---|---|
| **LinkedIn teaser** (short feed post, ≤210-char hook) | Stat-Led, Story (single-line), Contrarian | Bold Claim (too declarative for feed scroll) | Use a *different* formula than the article. The teaser is the hook into the article, not a mini-article. |
| **LinkedIn article** (long-form, 800-1200 words) | Story (opener-as-scene), Pattern Interrupt, Bold Claim | Stat-Led (numbers belong inside the article, not as the opening sentence) | Articles get the full first paragraph (3-5 sentences) — let Story run longer and pair with Bold Claim as the second beat. |
| **Twitter Post 1** (thread opener, ≤260 chars to leave room for "🧵" / "1/") | Stat-Led, Pattern Interrupt, Question | Story (a scene needs more room than 280 chars), Contrarian (the consensus + counter usually busts the 280 cap) | Twitter Post 1 is *all* hook. It should make the reader want to see Post 2; don't burn chars on setup. |
| **Facebook post** (~300-500 chars, warmer register) | Story (one-line, conversational), Question, Stat-Led | Pattern Interrupt (FB's audience wants warmth, not literary jolt), Contrarian (reads as combative on FB) | Open with a temporal anchor: "Last week…", "I keep thinking about…". The hook can be softer than LinkedIn because FB's algorithm tolerates conversational opens. |

The "Avoid" column isn't an absolute ban — it's the formula that statistically lands worst in that channel based on the crawl synthesis. If you have a strong instinct that an "avoided" formula is the right move for a specific piece, override it and note the reason in the alternates-considered block.

## Output contract — LinkedIn teaser

When blog-social generates the LinkedIn teaser, `<piece>/04-diligence/social/linkedin-teaser.md` carries this structure:

```markdown
# LinkedIn Teaser — [post slug]

## Selected hook (Formula: {{ formula_name }})
> {{ hook text — 1 or 2 sentences, under 210 chars combined }}

## Alternates considered (rejected)
- Formula: {{ formula_name }} — {{ rejected hook }} — **Why rejected:** {{ one-line reason }}
- Formula: {{ formula_name }} — {{ rejected hook }} — **Why rejected:** {{ one-line reason }}

## Body
{{ teaser body, 800-1500 chars total including hook, 1 earned-secret-anchored line in the middle, ends with a SPECIFIC question — never "What do you think?" or "Agree?" }}

## Posting metadata
- Hashtags: 0-3 max, at the very end after a line break.
- Link placement: blog URL goes in the **first comment**, not in the body.
- Best posting window: Tue/Wed/Thu, 7:30-8:30 AM PT.
```

## Output contract — LinkedIn article

A long-form LinkedIn **article** opens with the full first paragraph (3-5 sentences) — the formula table still applies but each formula gets more room. Pair Formula 3 (Story) with Formula 5 (Bold Claim) as a two-beat opener: scene + thesis. The article body is 800-1200 words, leaning more personal and opinion-led than the source blog.

## Output contract — Twitter thread

Twitter threads use `## Post N` block headings. The hook lives entirely in Post 1; subsequent posts develop the argument. Reference structure:

```markdown
## Post 1
{{ hook — ≤260 chars, complete sentence, curiosity trigger }}

## Post 2
{{ stake or context — ≤280 chars, picks up where Post 1 ends }}

## Post 3
{{ specific evidence or the earned secret — ≤280 chars }}

… (continue 5-10 posts total)

## Post N
{{ closing thought + blog URL + 0-2 hashtags — ≤280 chars total }}
```

Each post must read as a stand-alone thought. No "👇" pointers. No emoji-as-bullet. The thread structure points itself.

## Output contract — Facebook post

A single post, 300-500 chars sweet spot (allowed range 200-800). Warmer register than LinkedIn. Blog URL goes inline in the body — Facebook renders a preview card, which is why this is the only platform where the link belongs in the post itself. 0-2 hashtags max, at the end after a line break.

## Fold and char-limit rules per platform

- **LinkedIn mobile "See more" fold** ≈ char 210 (sometimes 200 with emoji/punctuation density). The first 210 chars MUST land the hook completely (no cliffhanger), carry a curiosity trigger, and contain zero "see more" filler ("Read below 👇" — banned). The format checker enforces a hard char count.
- **Twitter per-post limit** = 280 chars hard cap. The script enforces this per `## Post N` block; there is no soft fallback. Post 1 should fit ≤260 chars to leave room for the "🧵" or "1/" suffix.
- **Facebook "See more" truncation** ≈ char 300 (varies by device). The hook should land in the first ~250 chars even when the rest of the body runs to 500.

For every platform: if the hook + curiosity-trigger doesn't land by the platform's fold, regenerate.
