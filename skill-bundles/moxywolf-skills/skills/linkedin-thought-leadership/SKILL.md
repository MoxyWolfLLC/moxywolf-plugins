---
name: linkedin-thought-leadership
description: Scrape a LinkedIn top-content page via Claude in Chrome (running in Dorian's logged-in browser), scan all posts on the page, intelligently select 2-3 with highest engagement potential, then draft practitioner-level comments in MoxyWolf voice. This is the preferred LinkedIn engagement skill — it includes an already-commented check that skips posts Dorian has already commented on. Use this skill whenever a linkedin.com URL is shared and engagement is implied, when asked to respond to or comment on LinkedIn posts, for LinkedIn thought leadership sessions around cybersecurity, compliance, IR, GRC, or operational security topics. Trigger on phrases like "draft a comment for this post," "engage with this LinkedIn content," "what should I say to this," "run the LinkedIn responder," or any pasted linkedin.com URL. Always use this skill even without explicit LinkedIn mention if a linkedin.com URL appears.
---

# LinkedIn Engagement Responder

Reads a single LinkedIn content page using Claude in Chrome (which runs in Dorian's real, logged-in browser — bypassing LinkedIn's anti-bot gates that block standard fetches), scans all posts on the page, selects the best 2-3, and drafts practitioner-level comments in Dorian's voice following MoxyWolf brand guidelines.

## URL Input

### Default Target URL

If Dorian says "run the LinkedIn engagement responder" (or similar) without providing a specific URL, use this default:

https://www.linkedin.com/top-content/technology/cybersecurity-incident-response-plans/

If Dorian provides a specific URL, use that instead.

## Workflow

### Step 1: Fetch the LinkedIn Content

LinkedIn blocks standard `WebFetch`. Use Claude in Chrome — it runs in the user's actual browser with their authenticated LinkedIn session, so the anti-bot gate doesn't trigger.

**Tool chain:**
1. `mcp__Claude_in_Chrome__tabs_create_mcp` (or reuse a tab via `tabs_context_mcp` with `createIfEmpty: true`)
2. `mcp__Claude_in_Chrome__navigate` — url: the target LinkedIn URL
3. Wait ~3 seconds for the page to render
4. `mcp__Claude_in_Chrome__get_page_text` — returns the rendered text

**Fallbacks (in order):**
1. If `get_page_text` returns suspicious content (login banner, empty body), use `javascript_tool` to confirm session state. If the LinkedIn session has expired, ask the user to re-authenticate in the browser, then retry.
2. If the URL fails after retry, log it in the artifact as "FETCH FAILED" and stop.

**Note:** LinkedIn "top-content" aggregation pages render multiple posts inline without individual permalink URLs. The skill reads and responds to content but can't reliably extract direct comment links from these pages.

### Step 2: Scan All Posts and Select 2-3

Parse the scraped text and identify every individual post by author name patterns (names followed by follower counts and time indicators like "7mo", "1y").

For each post, extract: author name, title/role, follower count, post age, full text, comment count, hashtags.

**Already-commented check (required before selection):** After expanding each post to read its full text, scroll through the visible comments section. If Dorian Cougias's name appears as a comment author, mark the post as `ALREADY COMMENTED — INELIGIBLE` and exclude it from selection entirely. Do not include it in the numbered post catalog presented to Dorian.

In browser automation mode: look for "Dorian" or "Dorian Cougias" in comment author labels visible beneath the post. If comments aren't expanded, click "View comments" or the comment count to load them before deciding. If comment loading fails or times out, mark the post as `COMMENT CHECK FAILED — EXCLUDED (could not verify)` and skip it to be safe. If all relevant posts have already been commented on, inform Dorian and stop — no catalog needed.

**Evaluate every post** against these selection criteria and pick **two or three**:

**Selection criteria (priority order):**

1. **Engagement potential** — High comment counts signal active discussions where a sharp comment gets visibility. But don't ignore lower-count posts from high-follower authors — those are early-mover opportunities.
2. **Bridge to Dorian's expertise** — The post must create a natural opening to compliance, risk management, operational security, hardening, audit, or IR process design. If Dorian can't add practitioner depth, skip it.
3. **Contrarian or reframing opportunity** — Prefer posts where Dorian can offer a genuinely different angle. Not disagreement for its own sake, but a perspective the comment section probably doesn't have. Posts that present a single "right answer" are ideal targets for reframing.
4. **Author credibility** — Prioritize authors with meaningful titles, significant follower counts, or recognizable organizations. Commenting on a CISO's post carries more signal than an anonymous account.
5. **Recency** — More recent posts get more ongoing traffic. All else equal, favor newer content.

**Off-topic filtering:** Many aggregation pages include posts that are tangentially tagged but not actually relevant (sales demos, data center physical layouts, VC funding, etc.). Aggressively skip these. If a page yields only 0-1 relevant posts, that's fine — draft for what's there. Don't force selections from weak pages.

Present the numbered post list, your selections, and why — then **wait for Dorian's confirmation** before drafting. If Dorian overrides selections, honor that.

### Step 3: Draft Responses

**Read `/mnt/skills/user/moxywolf/SKILL.md` first** for brand voice guidelines before drafting any response. (Only needed once per session.)

Draft one comment per selected post. Present the first draft and **wait for Dorian's approval** before drafting the next. If Dorian requests revisions, iterate until approved.

Each comment must follow these rules:

#### Required:
- Practitioner tone throughout
- Open with a specific observation tied to the author's actual point — no generic praise
- Bridge to compliance, hardening, risk management, or operational security
- Include at least one concrete element (chosen safely):
  - A specific operational detail ("where this breaks in practice is…")
  - An experience-based insight ("what I've seen in audits…")
  - A statistic only if stated in the post or widely established — never invent numbers
- Dorian's voice: direct, confident, slightly contrarian, operationally grounded
- End with a genuine question back to the author that furthers conversation
- MoxyWolf mechanics: contractions (80%+), varied sentence length, fragments for emphasis, spaced en-dashes ( -- ) not em dashes, no forbidden phrases per MoxyWolf guidelines

#### Prohibited:
- No self-promotion, CTAs, or links
- No brand mentions ("MoxyWolf," "STIGViewer," etc.)
- No "Great post" or "Thanks for sharing" openers
- No hashtags (LinkedIn comments don't use them)
- No reference to anything not in or reasonably implied by the post
- No hedging ("perhaps," "maybe," "might")
- No AI-tell transitions ("Furthermore," "Additionally," "Moreover")

#### Comment Structure:
1. **Opening hook** (1-2 sentences) — Specific, slightly contrarian observation about the author's point
2. **Bridge** (2-3 sentences) — Connect to deeper operational reality
3. **Concrete element** (2-4 sentences) — Operational detail, audit insight, or experience-based observation
4. **Reframe** (2-3 sentences) — Different lens on the problem, not disagreement but expansion
5. **Closing question** (1-2 sentences) — Reframe the discussion, invite the author to go deeper

**Target: 150-250 words. Hard limit: 1200 characters.** LinkedIn truncates longer comments. Count characters before finalizing and trim if over.

### Step 4: Create the Artifact

Create the artifact after the first approved comment. Append each subsequent approved comment incrementally — don't wait until the end.

**File naming:** `linkedin-engagement-{date}.md`

Save to `/mnt/user-data/outputs/` and present via `present_files` after each update.

#### Artifact Header (once, at top of file):

```
# LinkedIn Engagement Responses — {Topic}

**Source Page:** LinkedIn Top Content: {topic name}

**Generated:** {date}

**Voice:** MoxyWolf (Dorian)
```

#### Per-Response Block:

For each approved comment, add a section with this exact format:

```
---

## Response N of M

**Post Author:** {Author Name} — {Title/Role} ({follower count} followers)

**Post URL:** {Direct permalink URL if available; if from an aggregation page, write "No permalink — found on [source page URL]"}

**Post Summary:** {1-2 sentence summary of the post's core argument}

**Full Original Post:**

> {The complete post text, reproduced verbatim as a blockquote. Include all original
> formatting — bullet points, line breaks, emoji. Do not truncate or summarize.
> This is the full post as scraped from LinkedIn.}

**Why This Post:** {One sentence on selection rationale — what reframe opportunity exists, why it bridges to Dorian's expertise}

**Dorian's Response** ({character count} chars)

> {The approved comment text. Separate paragraphs with blank lines within the
> blockquote. Use `> ` prefix on each line including blank separator lines
> marked as `> `.}
```

**Important formatting notes:**
- The Full Original Post must be the **complete verbatim text** of the post, not a summary or excerpt. If the post included bullet points, numbered lists, or other formatting, reproduce them inside the blockquote.
- Dorian's Response should also be a blockquote with paragraph spacing preserved.
- Separate each response block with a horizontal rule (`---`).
- When a new URL/topic begins, add a new top-level header and source page reference before the first response from that URL.

## Single Post Override

If Dorian specifies a single post (individual URL or pointing to a specific one on the page), skip selection and draft one response only. Still use the same artifact format.

## Finding Direct Post URLs

Aggregation pages lack permalinks. If Dorian needs the direct URL:

1. Search via the built-in `WebSearch` with distinctive phrases from the post in quotes + `site:linkedin.com`
2. If that fails, provide a manual path: author's profile URL, a distinctive phrase for LinkedIn search, and approximate post age

Be upfront about this limitation. Don't waste cycles on repeated failed attempts.

## Edge Cases

- **Auth wall**: Ask Dorian to paste content directly. Log "FETCH FAILED" in artifact and move to next URL.
- **Image/infographic posts**: Note visible text. Ask Dorian to describe the visual if needed.
- **Reshares**: Respond to original content unless Dorian specifies otherwise.
- **Non-English content**: Flag and ask for direction.
- **Empty or blocked pages**: Log in artifact and continue to next URL.
- **Rate limiting**: If LinkedIn surfaces a rate-limit page or unusual challenge, pause and inform Dorian — don't retry indefinitely. Chrome MCP runs in his real browser, so abusive scraping would affect his account.
- **All candidates already commented**: If every relevant post has already been commented on by Dorian, inform him and stop — no selection catalog needed.
