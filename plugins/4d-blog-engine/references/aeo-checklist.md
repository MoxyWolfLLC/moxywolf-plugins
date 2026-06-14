---
read_when: "Phase 2 (Description) loads this when laying out the outline. Phase 3 (Discernment) verifies the draft against it. Phase 4 (Diligence) scores the post against the AEO portion of the 100-point rubric."
status: canonical
canonical_for: "The single source of truth for SEO/AEO structure across every MoxyWolf blog pipeline — 4d-blog-engine, frontier-founder (commands/blog-post.md), and (phase 2) the stigviewer / blog-content ecosystems. Other formatters REFERENCE this file; they must not restate or fork its thresholds. When AEO behavior shifts (revisit quarterly), update the numbers here and only here."
based_on: "Princeton GEO research (Aggarwal et al., 2024); SERP-passage extraction patterns from liminalarc/claude-marketplace, agricidaniel/claude-blog, freema/seo-blog, amplitude/builder-skills."
---

# AEO checklist — structure for AI-answer-engine citation

> **Read this when:** designing the post outline (Phase 2) or auditing the draft against AI-citation readiness (Phase 3, Phase 4).

> **Canonical across pipelines:** this is the one AEO spec all MoxyWolf blog formatters point to. If you are running the Frontier Founder `/blog-post` command or any other pipeline, the thresholds live here — read them, apply them, and do not maintain a second copy.

AI search engines (ChatGPT, Perplexity, Gemini AIO, Claude with web access) cite **passages, not articles**. AEO (Answer Engine Optimization) is the discipline of writing those passages to be self-contained, extractable, and citation-worthy. It is distinct from classical SEO — classical SEO gets you ranked; AEO gets you cited.

## The three load-bearing principles

1. **Answer-First Extractability.** The reader's implied question gets answered in the first 40-60 words. AI scrapers pull from the top.
2. **Semantic Chunking.** Every H2 section is a self-contained ~150-word passage that makes sense if extracted alone. Define entities inline on first mention; never assume earlier-section context.
3. **Concrete Grounding.** Named examples, real numbers, real names, real dates. AI models cite passages with verifiable specifics over passages with abstractions.

## Required structural elements (in order, top of post)

### 1. Title (H1)

- 50-60 chars (Google rich-result cap is ~60; longer truncates in SERP).
- Primary keyword phrase appears verbatim within the first 30 chars.
- No clickbait, no "Ultimate Guide to..." (downgraded by 2024 helpful-content updates).
- No em-dash (`—`); use spaced en-dash (` – `) sparingly.
- Examples that work: "The 4D Framework: How Maya's Board Question Became a Trap" / "Building a Release Owner Gate That Survives Polish Bias" / "Why AI-Adopting Companies Hit the 1% Operational-Maturity Ceiling"

### 2. Direct-Answer Opener (first 40-60 words)

The first two sentences must literally answer the implied query.

- Sentence 1: a direct definition or claim containing the exact target keyword phrase (20-30 words).
- Sentence 2: the mechanism — *how* or *why* — that turns the claim into something actionable (20-30 words).
- Combined: 40-60 words.

❌ Bad: "Most companies have adopted AI. Almost none have been changed by it. This article explores why."
✅ Good: "78% of organizations have adopted AI but only 1% have reached operational maturity, because they trained the comfortable competence (prompt engineering) and stopped. Operational maturity requires the other three competencies — Delegation, Discernment, Diligence — engineered into the workflow as gates, not left as good intentions."

### 3. "At a Glance" block (60-90 words, immediately after the opener)

Per liminalarc/claude-marketplace: the AI citation excerpt. LLMs will lift this verbatim. Render as a blockquote or callout.

- 60-90 words total — research-backed sweet spot for Google AI-Overview passage selection.
- Self-contained: makes sense to a reader who hasn't read the article.
- Takes a point of view — not a teaser.
- Carries the load-bearing claim + the single number that makes the claim provable.

Template:
```markdown
> **At a Glance**
> [claim sentence] [mechanism sentence] [evidence sentence with a real number] [implication for the named reader].
```

### 4. TL;DR / Key Takeaways block (120-160 words, after At-a-Glance)

The expanded passage-extraction target. From freema/seo-blog and OpenClaudia/write-blog.

Render as 3-5 bullets, each a complete claim with a concrete number/name/outcome — not a teaser. The 120-160-word range is the 94th-percentile sweet spot for Google AI-Overview passage selection.

### 5. Section headers (H2)

- 4-7 H2s per post (3-4 for short pieces, 6-8 for pillar pieces).
- **60-70% of H2s should be phrased as natural questions** ("How does the Release Owner Gate work?" not "The Release Owner Gate Mechanism"). Question-H2s mirror how readers query AI engines.
- One idea per H2. AI parses content per section.
- Avoid 70%+ question H2s — that crosses into AI-tell territory (see `ai-anti-patterns.md` Tier-2-Major).

### 6. Citation capsules (40-60 words, after each H2)

Per agricidaniel/claude-blog. Every H2 opens with a 40-60-word paragraph that:

- Directly answers the H2's implied question.
- Contains one sourced statistic.
- Is self-contained — makes sense if extracted alone (no "as discussed above").

This is the AI-citable passage per section.

### 7. FAQ section (mandatory, 4-6 questions)

Per freema/seo-blog, OpenClaudia/write-blog, amplitude/builder-skills. FAQ H3s are citation magnets because they mirror how users prompt AI engines.

- 4-6 H3 questions phrased in natural-prompt language ("How do I...?", "Can X work for...?", "Is X free?", "Why does X...?", "When should I use X over Y?").
- Each answer self-contained, < 100 words.
- Answer in the first sentence — front-load the response.
- No "as mentioned above" / "see section X" — answers must work in isolation.

## JSON-LD schema (mandatory output)

Phase 4 writes JSON-LD into the blog markdown. Per the sign-off decision, the plugin always emits `BlogPosting`; adds `FAQPage` when an FAQ section is present.

### BlogPosting (always)

```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "{{ title }}",
  "description": "{{ excerpt }}",
  "image": "{{ heroImage }}",
  "author": {
    "@type": "Person",
    "name": "{{ author.name }}",
    "url": "{{ author.url }}"
  },
  "publisher": {
    "@type": "Organization",
    "name": "{{ publisher.name }}",
    "logo": { "@type": "ImageObject", "url": "{{ publisher.logo }}" }
  },
  "datePublished": "{{ datePublished ISO-8601 }}",
  "dateModified": "{{ dateModified ISO-8601 }}",
  "mainEntityOfPage": { "@type": "WebPage", "@id": "{{ canonicalUrl }}" }
}
```

### FAQPage (when FAQ section present)

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "{{ faq.question }}",
      "acceptedAnswer": { "@type": "Answer", "text": "{{ faq.answer }}" }
    }
  ]
}
```

Both blocks embedded in the markdown as a single `<script type="application/ld+json">` block at the end of the document (rendered platform inserts it into `<head>` at build time).

## Numeric content rules

| Rule | Value | Source |
|---|---|---|
| Title length | 50-60 chars | Google SERP cap |
| Meta description | 150-160 chars | Google SERP cap |
| H1 length | < 60 chars | Schema best practice |
| Primary keyword density | 0.5-1.5% | OpenClaudia/write-blog; > 3% triggers stuffing penalty |
| Citation capsule length | 40-60 words | agricidaniel/claude-blog |
| "At a Glance" length | 60-90 words | liminalarc passage-selection sweet spot |
| TL;DR length | 120-160 words | Google AI-Overview 94th-percentile passage length |
| Section length | 120-180 words / 150-word avg | agricidaniel: 70% more ChatGPT citations |
| Internal links | 2-5 per post | aRustyDev/blog-workflow |
| External authoritative links | 1-3 per post | aRustyDev/blog-workflow |
| Post freshness target | Updated within 30 days | agricidaniel: 76.4% of top AI citations are <30 days old |
| Article with no publication date | LOSES 76% of citation chance | DariuszCiesielski/polish-agent-skills |

## Princeton GEO method ranking (priority order)

From newmindsgroup/ai-agent-skills-library citing Princeton GEO research. Methods that lift AI-citation rate (apply in this priority):

| Method | Lift |
|---|---|
| Cite sources inline | +40% |
| Include statistics | +37% |
| Include quotations | +30% |
| Authoritative tone | +25% |
| Clarity (short sentences, plain words) | +20% |
| Technical terms (precise vocabulary) | +18% |
| Unique vocabulary (rare-but-correct words) | +15% |
| **Keyword stuffing** | **−10%** (actively hurts) |

**Best combination: Fluency + Statistics + Inline Citations.** Bake these three in by default.

## AI crawler accessibility

The publishing site's `robots.txt` should `Allow` the following user-agents (per agricidaniel/claude-blog and schwepps/seo-technical-audit):

```
User-agent: GPTBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Google-Extended
Allow: /
```

(Plugin notes this in `04-diligence/release-owner.signed.md` as an environment check, but does not modify the host site's robots.txt.)

## What this checklist is NOT

- It is not classical SEO. Classical SEO targets Google ranking (page speed, backlinks, keyword optimization for blue-link results). This file targets passage citation by AI engines.
- It is not a substitute for writing well. AEO structure on a thin post is still a thin post.
- It is not static. AI engines change citation behavior quarterly. Revisit this file every 3 months and update thresholds against current studies.
