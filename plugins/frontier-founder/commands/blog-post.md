---
description: Convert any draft markdown file into a publication-ready Frontier Founder blog post — formatted, with a brand-aligned hero image, saved into the FrontierFounder repo.
argument-hint: [path to a draft .md file, or paste the draft markdown]
---

# Convert a draft into a Frontier Founder blog post

Take a rough markdown draft and turn it into a publication-ready post for The
Frontier Founder blog: format it to the blog's frontmatter spec, structure it
for AI answer engines and search (AEO), apply the MoxyWolf typographic rules,
embed JSON-LD structured data, generate a brand-aligned hero image, and save
both files into the FrontierFounder repo with a shared, slug-based naming
convention.

The draft can come from anyone — a guest writer, a teammate, you — written in
any editor, with no frontmatter and no knowledge of this blog's conventions.
This command supplies all of that. The author does not need to be working in
the Frontier Founder project.

## The draft

The draft is provided in `$ARGUMENTS` — either a path to a `.md` file, or the
markdown pasted directly after the command. It may also have been uploaded as
an attachment in this conversation. Accept any of these. If you cannot find a
draft, ask the user for one before doing anything else.

The draft may have full frontmatter, partial frontmatter, or none at all.
Handle every case: use what is there, derive what you can, ask for the rest.

## Step 1 — Locate the FrontierFounder repo

The post and its hero image must be saved into the FrontierFounder repo. It is
the `FrontierFounder/` folder under the mounted **GitHub** root.

- Confirm the repo is reachable and that `content/blog/` and
  `public/blog-hero/` exist inside it.
- If the GitHub root or the FrontierFounder repo is not mounted in this Cowork
  session, stop and ask the user to add it via Cowork → Folders. Do not write
  anything until the repo is reachable.

## Step 2 — Derive the post's identity

Work these out from the draft's frontmatter first, then its content, then by
asking the user:

- **Title** — frontmatter `title`, else the first `# H1` in the body, else ask.
- **Slug** — the single naming key. Keep an existing frontmatter `slug`;
  otherwise kebab-case the title: lowercase, ASCII only, words joined by single
  hyphens, punctuation stripped. "Why Agents Change the Org Chart" becomes
  `why-agents-change-the-org-chart`.
- **Excerpt** — frontmatter `excerpt`, else write one. This field does triple
  duty: the site feeds it to `<meta name="description">`, to OpenGraph, and to
  the JSON-LD `description` (Step 7). Write it as the meta description:
  **150–160 characters**, declarative (not a teaser), leading with the post's
  primary keyword phrase. Carry an existing good excerpt over; only rewrite one
  that is missing, too long, or too vague to earn a click.
- **Category** — frontmatter `category`, else infer a short one- or two-word
  category from the subject, else ask.
- **Author** — frontmatter `author`, else `Dorian Cougias`. If the draft is
  clearly by someone else, ask for the author's name. Never guess a name.
- **Date** — frontmatter `date`, else today's date as `YYYY-MM-DD`.
- **status** — `draft`, unless the draft's frontmatter explicitly says
  `published`. Converting a draft never publishes it on its own; the user flips
  this when the post is ready.
- **linkedinUrl** — carry it over if present; otherwise leave it out. It is
  added later, once the LinkedIn edition exists.

## Step 3 — Apply the AEO structure

Structure the post so AI answer engines (ChatGPT, Perplexity, Gemini, Claude)
and classical search can extract and cite it. The rules and every threshold
live in the **canonical AEO checklist** — the single source of truth shared by
all MoxyWolf blog pipelines:

`plugins/4d-blog-engine/references/aeo-checklist.md` in the `moxywolf-plugins`
repo (the installed 4d-blog-engine plugin ships an identical copy). Load it and
apply its numbers. Do not restate or fork its thresholds here — when AEO
guidance changes, that one file changes.

Unlike Step 4, this step may **add** structural scaffolding the draft lacks. It
never rewrites the author's argument and never invents evidence: build every
element only from claims and numbers already in the draft. If a slot has no
provable number or named example in the source, leave it out and tell the user
— MoxyWolf never fabricates a statistic, a name, or a source.

Ensure the post carries these, in order (see the checklist for the exact word
counts and the question-H2 ratio):

1. **Direct-answer opener** — the first 40–60 words answer the post's implied
   question, primary keyword phrase in the first sentence.
2. **At a Glance** — a blockquote led by `> **At a Glance**` carrying the
   load-bearing claim plus the one number that proves it. This is the passage
   AI engines lift verbatim.
3. **Key Takeaways** — a `> **Key Takeaways**` blockquote of 3–5 bullets, each a
   complete claim with a concrete number, name, or outcome (not a teaser).
4. **Question-style H2s** — phrase most section headings as the natural
   questions a reader would ask an AI engine, one idea per H2.
5. **FAQ** — an `## FAQ` section near the end, 4–6 `###` questions in
   natural-prompt language, each answered self-contained and answer-first.

The live posts already model this house style — match
`content/blog/polish-bias-smb-founders.md`. If the draft is too thin to add
these honestly without inventing evidence, stop and tell the user it needs more
source material first.

## Step 4 — Format the body

This is a formatting pass, not a rewrite. Do not change the author's words,
their argument, or the structure of their ideas. Fix only mechanics:

- Remove a leading `# H1` if it just repeats the title — the page renders the
  title from the frontmatter.
- Section headings start at `##`.
- Apply the MoxyWolf typographic rules: convert straight quotes to
  typographer's (curly) quotes; replace every em-dash with a spaced en-dash
  ` – `, used sparingly; normalize list markers and blank-line spacing so the
  markdown is clean.
- Leave a blank line before every list and before every heading.

A full voice pass — rewriting flat or generic passages into the author's
voice — is a separate step, the voice-injection skill, and is not part of this
command. Mention it to the user only if the draft reads as visibly AI-generic.

## Step 5 — Inline media

Scan the body for image, video, and audio references.

- Normalize every inline media path to `/blog-media/<filename>`.
- A reference whose file ends in `.mp4`, `.webm`, `.mov` (video) or `.mp3`,
  `.wav`, `.m4a` (audio) is fine as a standard `![caption](path)` image link —
  the site renders those as players automatically.
- Build the `media` array in the frontmatter from every referenced asset, each
  entry as `file` plus an optional `caption`.
- For every file named in `media` and in `heroImage`, check whether it already
  exists under the repo's `public/blog-media/` or `public/blog-hero/`. List any
  that are missing and tell the user they must upload them — the blog's build
  validator fails the deploy if a published post references a file that is not
  there. Never invent or fabricate a media file.

## Step 6 — Generate the hero image

Every post gets one hero image, generated in the **brand-aligned abstract**
style so the blog stays visually cohesive.

**Style spec — use this every time:**

> A geometric, abstract composition. Layered angular shapes, soft depth, clean
> negative space, a calm and modern editorial feel. Matte finish. No text, no
> logos, no people, and no literal depiction of objects. Palette only: deep
> navy `#26547C`, teal `#0E8C80`, warm orange `#F77028`, cream `#F6F5F1`, with
> a small accent of gold `#C8870E`. The mood echoes the Frontier Founder
> compass mark — angular, eight-pointed, exact — without drawing a compass.

Workflow:

1. Read the finished post and derive a one-line concept for the composition —
   a mood and a shape language drawn from the post's theme, not a literal
   illustration of it.
2. Show the user that concept and the full generation prompt, and let them
   approve or adjust it before you generate.
3. Generate the image at **16:9 landscape, about 1600 by 900** — it is cropped
   to 16:9 on the blog index card and as the post hero.
4. Save it to `public/blog-hero/<slug>.png` in the FrontierFounder repo — the
   same slug as the post file.
5. Set the frontmatter `heroImage: /blog-hero/<slug>.png`.

Use whatever image-generation tool or skill is available in the session. If
none is available, do not fail the whole command — save the formatted post,
set `heroImage` to the intended `/blog-hero/<slug>.png` path, and tell the user
the hero image still needs to be generated and dropped at that path.

## Step 7 — Generate the JSON-LD block

The FrontierFounder site renders structured data from a single JSON-LD block in
the post body. `src/lib/posts.ts` extracts the **first**
`<script type="application/ld+json">…</script>` block, validates it as JSON,
strips it from the visible body, and emits it as a real `<script>` tag for
crawlers. Honor that contract exactly:

- Emit **exactly one** `ld+json` block, and make it valid JSON. A malformed
  block is left visible in the body; a second block renders as escaped text.
- Put it as the **last thing in the body**, after the FAQ.
- Hold every node in one `@graph`. Follow the house convention already shipping
  in `content/blog/polish-bias-smb-founders.md`: a `BlogPosting`, the author
  `Person`, the publisher `Organization` (MoxyWolf LLC), and — when the post has
  an FAQ — a `FAQPage`. Reuse the shared `@id`s verbatim so entities consolidate
  across MoxyWolf properties; only the per-post fields change.

Template — fill the `<…>` per-post fields, keep the shared `@id`s exactly:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BlogPosting",
      "@id": "https://thefrontierfounder.com/blog/<slug>#post",
      "headline": "<title>",
      "description": "<excerpt>",
      "image": "https://thefrontierfounder.com<heroImage>",
      "author": {"@id": "https://moxywolf.com/people/dorian-cougias#author"},
      "publisher": {"@id": "https://moxywolf.com#publisher"},
      "datePublished": "<date>",
      "dateModified": "<date — or a later update date if the post was revised>",
      "mainEntityOfPage": {"@type": "WebPage", "@id": "https://thefrontierfounder.com/blog/<slug>"}
    },
    {
      "@type": "Person",
      "@id": "https://moxywolf.com/people/dorian-cougias#author",
      "name": "Dorian Cougias",
      "url": "https://moxywolf.com",
      "sameAs": ["https://www.linkedin.com/in/doriancougias/"]
    },
    {
      "@type": "Organization",
      "@id": "https://moxywolf.com#publisher",
      "name": "MoxyWolf LLC",
      "url": "https://moxywolf.com",
      "logo": {"@type": "ImageObject", "url": "https://moxywolf.com/logo.png"}
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {"@type": "Question", "name": "<question>", "acceptedAnswer": {"@type": "Answer", "text": "<answer>"}}
      ]
    }
  ]
}
</script>
```

- Drop the `FAQPage` node when the post has no FAQ. Its questions and answers
  must match the on-page `## FAQ` word-for-word.
- If the author is not Dorian, replace the `Person` node with the real author
  (name, url, sameAs) under a new `@id` — never reuse Dorian's `@id` for someone
  else, and never invent a name or profile URL.
- The page URL — `BlogPosting` `@id`, `mainEntityOfPage`, and the absolute
  `image` — uses `thefrontierfounder.com/blog/<slug>`, the blog's canonical
  home and the URL the site sets as `alternates.canonical`. The author `Person`
  and publisher `Organization` `@id`s deliberately stay on `moxywolf.com`: those
  are stable entity identifiers, shared across MoxyWolf properties for entity
  consolidation, not page URLs.

## Step 8 — Assemble and save

1. Build the final post: the YAML frontmatter block (see the spec below)
   followed by the formatted body, which ends with the Step 7 JSON-LD block.
2. Save it to `content/blog/<slug>.md` in the FrontierFounder repo.
3. If a file with that slug already exists, stop and ask the user whether to
   overwrite it or choose a different slug.

## Step 9 — Report back

Tell the user, plainly:

- The post path (`content/blog/<slug>.md`) and the hero path
  (`public/blog-hero/<slug>.png`).
- The slug — confirm the post file, the hero file, and the `heroImage` value
  all share it.
- The AEO scaffolding you added (At a Glance, Key Takeaways, FAQ) — and call out
  any slot you left empty because the draft had no provable number for it.
- That a single JSON-LD `@graph` block (BlogPosting + author + publisher, plus
  FAQPage when there's an FAQ) sits at the end of the body and renders as
  structured data — the site strips it from the visible post.
- `status: draft` — and that they flip it to `published` when the post is ready.
- Any media files still to be uploaded to `public/blog-media/`.
- That once they review it they commit and push from GitHub Desktop; the post
  goes live on the next Vercel deploy, and the build validator blocks the
  deploy if any referenced hero or media file is missing.

## Frontmatter spec (reference)

```yaml
---
title: "The post title"
slug: the-post-title
excerpt: "150–160 chars. Meta description + OpenGraph + JSON-LD description: declarative, keyword-first."
date: 2026-05-25
author: Dorian Cougias
category: Operating
heroImage: /blog-hero/the-post-title.png
linkedinUrl:                       # optional — added once the LinkedIn issue is up
status: draft                      # draft | published
media:
  - file: /blog-media/some-diagram.png
    caption: "What the diagram shows"
---
```

`title` and `date` are required on a published post. The slug ties the post
file, the hero image file, and the `heroImage` path together — one stem for all
three.

The body itself ends with the single `<script type="application/ld+json">`
`@graph` block from Step 7. Leave it in the body, last — the site extracts and
renders it as structured data and strips it from the visible post. It is not a
frontmatter field.
