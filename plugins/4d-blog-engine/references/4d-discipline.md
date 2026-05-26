---
read_when: "Every phase of the 4D Blog Engine loads this as a prerequisite. Read at the start of any /4d-blog-engine command."
source: "Cougias, D. J. (2026). Beyond the Prompt: How the 4D AI Fluency Framework Operationalizes the Frontier Founder. MoxyWolf LLC."
status: canonical
---

# The 4D Discipline — applied to content production

> **Read this when:** invoking any `/4d-blog-engine:*` command. This is the spine of the plugin. Every phase asks the question this reference says it asks; every gate enforces what this reference says it enforces. If a phase ever skips the gate this file describes, the whole framework is wearing a costume.

The 4D AI Fluency Framework (Dakan and Feller, 2025) defines AI fluency as the capacity to work with AI effectively, efficiently, ethically, and safely. Four competencies, two loops.

- **Inner loop** (all-day cycle): **Description** + **Discernment** — describe what you need, evaluate what comes back, refine, repeat.
- **Outer loop** (governing context): **Delegation** + **Diligence** — decide what to hand to the machine in the first place, and own the result.

This plugin maps each D to a phase, and each phase to a command. The mapping is exact, not metaphorical.

## Delegation — `/4d-blog-engine:delegate`

**The question this phase answers:** *Is this the right work to hand to AI in the first place, and what part of it?*

**Inputs:** A base document (path or URL) and optionally an angle question.

**What it does:**
1. **Capability triage** (cheap LLM, ~$0.001) — yes/no on "does this topic warrant a post against the jagged frontier?" References Dell'Acqua et al. (2026): tasks inside the model's capability frontier get a +40% quality lift; tasks outside cost 19 percentage points. The triage answers *which side of the line*.
2. **Doc classification** — detect base doc type (blog / whitepaper / meeting notes / transcript / report / email / braindump / code commit log / other).
3. **Angle elicitation** — if the user didn't supply one, propose 3-5 candidate angles, each a one-sentence thesis + audience + earned-secret slot. Angles must be *genuinely different*, not three rephrasings of the same idea (naveedharri/benai-skills).
4. **Earned-secret stall** (animalzinc/structured-article-writer) — the human must name something they know from direct experience that the audience does not. It cannot be something they read. If they can't supply one, the phase blocks and asks again. **This is the single best device for forcing genuine voice into a derived piece. Do not soften it.**
5. **Modality decision** — automation / augmentation / agency (Raisch & Krakowski, 2021). Default: automation. The selected modality affects which review prompts fire downstream.

**Gate:** Writes `_phase: 01, _status: passed, _timestamp: <ISO>, earned_secret: <one-line>, modality: <automation|augmentation|agency>` to `01-delegation.md` frontmatter. Phase 2 refuses to start if `passed != true` or the timestamp is >24h old.

## Description — `/4d-blog-engine:describe`

**The question this phase answers:** *Have we told the AI the goal and constraints precisely enough that it can behave usefully?*

**What it does:**
1. **Voice load (mandatory STEP 0).** Read `MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md` in full. Report back to the user what was loaded (voice tone, sentence-length range, contraction rate target, fragment frequency, conjunction-starter frequency, forbidden phrases). Per jamon8888/cc-suite — never proceed silently.
2. **8-question voice interview** — reuse `research-pipeline/content-writer`'s interview (Trigger / Evidence / Contrarian Take / Authority / Specific Reader / Business Connection / Call to Action / Emotional Core). One question per message. Push back on vague answers ("Marketing professionals" is not a reader; "Sarah, VP Marketing at a Series B SaaS company who just got told to use AI more by her CEO" is a reader).
3. **Structure pick** — Sorkin DOB (default) / Hero's Journey / Story Circle / Inverted Pyramid. Selection persisted.
4. **Outline** — H2-by-H2, 60-70% question-phrased H2s (`aeo-checklist.md`), per-section word budget, evidence mapping per section ("what does the 30-day sweep need to find for this section?"), and the **"At a Glance" 60-90 word AI-citation block** specified up front.
5. **Anti-slop pre-load** — read `ai-anti-patterns.md` in full. Internalize before any prose. The patterns are constraints on composition, not just things to scan for after.

**Gate:** Writes `02-description.md`. Human reviews the outline + At-a-Glance block and types `proceed` or `revise <specific>`. No prose generated yet. Cap: 2 revision rounds before escalating.

## Discernment — `/4d-blog-engine:discern`

**The question this phase answers:** *Did the draft survive a real check — including a 30-day reality check from the world outside our heads?*

**What it does:**
1. **30-day discourse sweep** (`scripts/discourse_sweep.py`). Platform-targeted `site:` operators across reddit / X / news.ycombinator.com / Substack / dev.to / github / linkedin.com/pulse / Facebook / Quora, plus podcasts (Apify) and academic (research-pipeline/literature-discovery). `after:<today-30d>` recency filter. Combined score = relevance×0.6 + recency×0.4. Dedup 70% title-overlap. Cross-source clustering. See `source-quality-tiers.md`.
2. **Council synthesis pass** — `/council:deliberate` is fed the raw harvest + the outline + the angle. Returns a ranked, themed brief: which findings move the post from generic to specific, which contradict each other, which represent consensus vs minority across platforms.
3. **Bibliography build** — pass the curated source set to `bibtex-builder/bibtex-from-urls`. Each entry gets a 50-150 word AI-generated abstract and a `quality_tier: 1-5` field.
4. **Citation verification** — `research-pipeline/citation-verifier` runs the 4-layer check (CrossRef, DataCite, arXiv, Semantic Scholar). Each datum tagged `[V]` verified / `[S]` search-summary-only / `[F]` fetch-failed. `[F]` data is **forbidden in the body** — substitutes `[CITATION NEEDED]` placeholders.
5. **Draft** — `research-pipeline/content-writer` runs with the voice profile, the DOB arc, the outline, and the verified bibliography. Every cited statistic carries the **FLOW evidence triple** (year anchor + inline citation + URL with retrieval date).
6. **Two-tier slop pass** (`scripts/prose_lint.py` + LLM sub-agent). Layer 1 deterministic: vocab blocklist, regex banned phrases, em-dash detection, burstiness, TTR. Layer 2 structural (LLM): question-H2 ratio, three-clause-sentence frequency, hedge stacking, paragraph-shape flatness. See `ai-anti-patterns.md`.
7. **Second-pass audit** — re-scan the rewrite to catch survivors (rainday/smart-blog-skills). Single-pass de-slop misses survivors.

**Gate:** Writes letter grade (heymitch/ai-pattern-hunter): F = 3+ majors or 6+ total flags; D = 2+ majors. C or worse blocks Phase 4.

## Diligence — `/4d-blog-engine:diligence`

**The question this phase answers:** *Will a named human put their signature on this before it ships?*

This is the literal Release Owner Gate from the *Beyond the Prompt* whitepaper, section 7. Quote: *"Any AI-generated output about to reach a customer, a support reply, a proposal, a report, a config change, product copy, doesn't go out until one named person has signed for it. Not 'the team.' A person."*

**What it does (5-stage nonce-bound contract — `scripts/preflight.py`):**

1. **Capability** — every claim sources to a Tier 1-3 source; every URL resolves (link checker); zero `[F]` data in body.
2. **Format** — frontmatter validates (UUIDv4 id, ISO-8601 date, no em-dash, spaced en-dash, typographer's quotes, blank lines before lists/headings).
3. **Visual** — hero image generated via `frontier-founder/blog-post`'s fixed brand style spec (geometric/abstract, palette hex, no text/logos/people), 16:9 ~1600x900. Shown for human approval **before** generation. Saved alongside an `og-hero-prompt.md` artifact (AI transparency).
4. **Content Review** — BLOCKING reviewer agent (no Bash tool, no Edit tool; tool-restricted by trust boundary). Scores 100-point rubric (`release-owner-rubric.md`). **Must** echo the CSPRNG nonce written to `.review-nonce` verbatim in its scorecard, and end with a machine-readable `BLOCKING: true|false (reason)` line. Iterates up to 3 times; nothing below 90/100 reaches the user; on iteration 3 still failing, escalates.
5. **Asset Integrity** — every referenced media file exists on disk; slug ties post + hero + bibliography names.

**Sign-off line.** The Release Owner enters `Verified — <initials>, <YYYY-MM-DD>` into `changelog.md` by hand. The plugin **never** auto-signs.

**Only on a clean Diligence gate does the plugin generate the LinkedIn pair** (article + teaser, each with 3-axis scorecard). The Diligence phase is the staging condition for derivative output, not an afterthought.

## Three load-bearing rules (these are not optional)

1. **The gates are mechanisms, not aspirations.** Layer 1 is a deterministic script. Layer 2 has a nonce the reviewer must echo. If a future contributor proposes "let's just have Claude self-review" instead, push back — automation bias (Romeo and Conti, 2026) means a polished output disarms the check by 5.2 points. The whole point of engineering the gate is to beat that current.
2. **The earned secret is required, not encouraged.** If Delegation lets a post through without one, the plugin produces generic content — the polish bias amplified. The stall is the feature.
3. **Voice loads at STEP 0 and reports back.** Silent voice loading = drift. Loud voice loading + a test-passage calibration (lifegenieai/copy-editor) is the only known mechanism that survives a long session without drift.

## References (verbatim, for the file the skills will read)

- Dakan, R., and Feller, J. (2025). The AI Fluency Framework. Anthropic.
- Cougias, D. J. (2026). Beyond the Prompt. MoxyWolf LLC.
- Cougias, D. J. (2025). The Frontier Founder. MoxyWolf LLC.
- Dell'Acqua, F., McFowland, E., Mollick, E., et al. (2026). Navigating the Jagged Technological Frontier. *Organization Science*, 37(2), 403-423.
- Raisch, S., and Krakowski, S. (2021). Artificial Intelligence and Management: The Automation-Augmentation Paradox. *Academy of Management Review*, 46(1), 192-210.
- Anthropic. (2026). AI Fluency Index.
- Romeo, G., and Conti, D. (2026). Exploring automation bias in human-AI collaboration. *AI & Society*, 41(1), 259-278.
- Wingerter, T. L., Straub, T., and Schweitzer, S. (2025). Mitigating Automation Bias in Generative AI Through Nudges. *Procedia Computer Science*, 270, 2106-2114.
