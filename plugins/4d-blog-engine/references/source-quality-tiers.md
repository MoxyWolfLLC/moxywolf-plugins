---
read_when: "Phase 3 (Discernment) reads this when classifying each finding from the 30-day discourse sweep; the citation-verifier scores each source by tier; the bibliography records the tier as a quality_tier field per entry."
status: canonical
based_on: "agricidaniel/claude-blog 5-tier source-quality system; jamesgray007/hoai-course FLOW evidence triple; cross-source clustering from agricidaniel and lifegenieai/research-coordinator."
---

# Source quality tiers — for the 30-day discourse sweep

> **Read this when:** scoring sources after the 30-day sweep (Phase 3), building the bibliography (Phase 3), or checking citation integrity at the Diligence gate (Phase 4).

Every source surfaced by the 30-day discourse sweep gets a tier (1-5). The bibliography records the tier per entry. Tier 1-3 sources are citable in body prose; Tier 4-5 are rejected — they're noise, not evidence.

## The tier ladder

### Tier 1 — Primary authoritative sources

- Government domains (`.gov`, `.gov.uk`, `.europa.eu`, etc.)
- Educational/research institutions (`.edu`, named universities, research consortia)
- Standards bodies (W3C, IETF RFCs, ISO, NIST)
- Anthropic / OpenAI / Microsoft Research / DeepMind official research publications (when they ARE the primary source for an AI claim — peer-reviewed or technical report, not a blog post)
- NBER working papers
- Direct primary sources: company SEC filings, official changelogs, official documentation

**Treatment:** Cite directly. No paraphrase chain. Always cite the primary, not a Tier-3 summary of it.

### Tier 2 — Named research firms and academic outlets

- Named research firms publishing methodology with their data: Ahrefs Research, BrightEdge Data Cube, SparkToro, Pew Research, McKinsey Global Institute, Forrester, Gartner (when they publish methodology)
- Academic journals with peer review (verified via `research-pipeline/citation-verifier`)
- Government statistical agencies operating at arm's length
- Major think tanks with disclosed methodology and funding (Brookings, AEI, Pew)
- Author-publisher first-party publications (the company's own engineering blog when reporting their own data — "we measured X in our production system")

**Treatment:** Cite directly. Note methodology where it strengthens the claim ("Anthropic's Education Report analyzed 9,830 anonymized conversations…").

### Tier 3 — Reputable trade press and named-author analysis

- Major trade press: Search Engine Journal, The Verge, Wired, MIT Technology Review, Stratechery, HBR
- Named-author Substack / Medium with discoverable expertise (the author's track record is checkable)
- Industry trade publications with editorial oversight
- Long-running analysis blogs from named experts in the field

**Treatment:** Citable. When a Tier 3 source reports on a Tier 1-2 finding, **cite the Tier 1-2 source upstream**, not the Tier 3 reporter (cross-source clustering rule below).

### Tier 4 — REJECT (don't cite)

- Generic SEO blogs (the "X marketing tips for 2026" content-farm tier)
- Aggregator/listicle sites with no original reporting
- AI-written content farms (any site whose About page lists AI-content disclaimers)
- Unsourced "X% of marketers believe…" roundups that don't link to a survey
- Random Medium / dev.to posts where the author has no discoverable expertise
- LinkedIn posts from accounts not in the field they're posting about

**Treatment:** Discard. If a discourse-sweep result is Tier 4, do not include in the bibliography. Do not let Tier 4 "support" a body claim.

### Tier 5 — REJECT (with active flag)

- Plagiarized content (rephrased Tier 1-3 source without citation, often algorithmically detectable)
- Demonstrably false or contradicted-by-Tier-1 content
- AI-generated content farm posts (heavy Tier-1/Tier-2 anti-pattern signals from `ai-anti-patterns.md`)
- Content from organizations with conflicts of interest unstated relative to the claim

**Treatment:** Discard AND log to `sources-verification.md` as a flagged exclusion with reason. If the same false claim shows up in multiple Tier-5 sources, flag the upstream.

## FLOW evidence triple — required on every statistic in body prose

Every numeric claim in the published post must carry the FLOW evidence triple. If any element is missing, the claim is downgraded to `[CITATION NEEDED]` and the Diligence gate (Phase 4) flags it.

1. **Year anchor in prose.** State the year inline before the number. ("In 2026, …" / "Microsoft's 2025 Work Trend Index found…")
2. **Inline citation with publisher name.** Use the form `[Publisher Name](url)`. Not bracketed numbers, not bare URLs.
3. **URL with retrieval date in the source block.** Each citation also appears in `bibliography.bib` with a `note = {Accessed YYYY-MM-DD}` field.

### Example of correct FLOW citation in body

```markdown
Microsoft's 2025 Work Trend Index ([Microsoft](https://www.microsoft.com/worklab/work-trend-index)) surveyed 31,000 workers and found that 78% of organizations have adopted AI while 1% have reached operational maturity.
```

### Example of broken FLOW citation (Phase 3 flags)

```markdown
A recent study found that 78% of companies use AI [^1].
```

Missing year anchor, vague subject ("a recent study"), bracketed-number style, no inline publisher name. Phase 3 marks this as a Discernment failure and forces a rewrite.

## Cross-source clustering — collapse paraphrases to upstream

A common AI failure mode: an LLM finds five articles all paraphrasing one BrightEdge report and treats them as five independent sources. They are one source.

**Rule:** When two or more sources share a load-bearing claim (the same statistic, the same finding, the same example), trace the upstream. Cite the upstream (the original BrightEdge report) as the **primary citation** and note in `sources-verification.md` how many downstream copies were found. The downstream copies do not earn their own bibliography entries unless they add a distinct interpretation or methodology critique.

**Recall vs precision:** the 30-day sweep is recall-heavy (it casts a wide net across reddit, X, HN, Substack, Facebook, Quora, podcasts, academic). The Council synthesis pass and this clustering rule are how the noise becomes signal.

## Verification states per finding

Each finding from the sweep, after passing through `research-pipeline/citation-verifier`, gets one of three tags. The writer's behavior is determined by the tag.

| Tag | Meaning | Writer behavior |
|---|---|---|
| `[V]` Verified | URL resolves; claim appears on the cited page; year/figure/wording matches the prose claim within rounding | Citable in body prose with FLOW triple |
| `[S]` Search-summary only | URL resolves but the verifier couldn't read the full page (e.g., paywalled, JS-rendered, PDF-only); summary matches the claim | Citable, but flag in `sources-verification.md` — human verifies at the Diligence gate |
| `[F]` Fetch-failed | URL doesn't resolve, the cited page doesn't contain the claim, or the figure/year/wording is contradicted by the page | **Forbidden in body.** Replace the prose claim with `[CITATION NEEDED]`. Phase 4 will not pass with any `[F]` data in body. |

This is the rainday/smart-blog-skills triple-layer verification, adapted for our pipeline.

## Anti-fabrication rules

These are not negotiable. They apply to every phase.

1. **Never generate a BibTeX entry from memory.** AI-generated citations have a documented ~40% error rate (luqmannurhakimbazman/ml-paper-writing). All BibTeX entries flow through `bibtex-builder/bibtex-from-urls` or `research-pipeline/literature-discovery`, which fetch the source.
2. **Never invent an author, title, year, or DOI.** If a verified source for a claim cannot be found, the claim does not get made. Insert `[CITATION NEEDED]` and surface it to the human.
3. **Never substitute an unrelated source.** If the original source for a claim is dead-link, the writer cannot replace it with a different source that says something similar. The claim either gets a real upstream or it gets cut.
4. **Direct quotes ≤ 15 words.** Anything longer paraphrases with citation. Copyright safety.
5. **Attribute social-platform sources by handle + platform + date.** ("@username on X, 2026-04-12") not as a generic "according to a recent post."

## Discourse-sweep platform-specific notes

The 30-day sweep hits 10 platforms. Each has its own quality character:

| Platform | Tier ceiling | Notes |
|---|---|---|
| Academic (OpenAlex, Semantic Scholar, arXiv) | Tier 1-2 | The default backbone for any data-driven claim |
| `.gov` / `.edu` / W3C / RFC | Tier 1 | Always cite as primary |
| Hacker News | Tier 3 (for comments) or Tier 1-2 (for links to primary) | Comments are signal-rich but anonymous |
| Reddit | Tier 3 (for comments) or Tier 1-2 (for links to primary) | Look at the subreddit's reputation; r/MachineLearning ≠ r/AI |
| LinkedIn Pulse | Tier 3 max | Named-author analyses; treat as opinion unless the author IS the primary source |
| Substack | Tier 3 max | Same as LinkedIn Pulse; named authors with track records |
| X (Twitter) | Tier 3 max | Useful for quoting practitioner reactions; never for the load-bearing claim |
| dev.to / Medium | Tier 3 max | Skews thin; only cite when the author has discoverable expertise |
| Facebook | Tier 4 (default) | Almost never citable; included in sweep for completeness, almost always discarded |
| Quora | Tier 3 (for named-expert answers) or Tier 4 (default) | Useful for surfacing practitioner questions, less so for answers |
| Podcasts (Apify) | Tier 3 max | Cite the podcast + episode + timestamp; if the guest is the primary source, find their written work and cite that instead |
| GitHub (issues, READMEs, code) | Tier 1-2 (for the code itself) or Tier 3 (for discussion) | The repo IS the source for any technical-implementation claim |

The Council synthesis pass uses these tier ceilings to weight findings during the "consensus vs minority" analysis.
