# Routing Heuristics Reference

Detailed keyword and pattern matching rules for query classification and routing decisions.

## Query Category Classification

### Architecture Decision
**Keywords:** compare, tradeoffs, pros cons, monolith, microservices, architecture, design pattern, scalability, infrastructure, migration, refactor
**Signals:** Multiple options being weighed, mentions of technical constraints, "should we" or "should I"
**Default route:** Deliberate (voting protocol)

### Compliance / Security
**Keywords:** STIG, CMMC, compliance, FedRAMP, NIST, authorization, access control, audit, vulnerability, security, risk
**Signals:** References to specific frameworks or standards, questions about requirements interpretation
**Default route:** Deliberate (consensus protocol — knowledge-heavy)

### Code / Implementation
**Keywords:** implement, code, function, bug, error, fix, refactor, test, deploy, API
**Signals:** Code snippets in query, specific file or function references, error messages
**Default route:** Single model (usually factual/deterministic — unless "best approach to implement" which is a decision)

### Strategy / Business
**Keywords:** strategy, market, pricing, positioning, competitor, growth, roadmap, prioritize, launch
**Signals:** Business context, stakeholder mentions, timeline references
**Default route:** Deliberate (voting protocol)

### Creative / Writing
**Keywords:** write, draft, blog, post, article, copy, headline, tagline, narrative, story
**Signals:** Tone/voice specifications, audience definitions, content type requests
**Default route:** Deliberate (voting protocol — creative benefits from diverse perspectives)

### Factual / Lookup
**Keywords:** what is, define, how does, explain, meaning of, syntax for, list of
**Signals:** Short queries, single-concept questions, no decision involved
**Default route:** Single model

## Compound Query Detection

Queries with multiple sub-questions should usually deliberate:
- "What is X **and** should we use it?" → Deliberate (the "should" makes it a decision)
- "How does X work?" → Single model
- "How does X work and what are the tradeoffs vs Y?" → Deliberate

Look for conjunctions (and, but, or, vs, versus, compared to) as compound signals.
