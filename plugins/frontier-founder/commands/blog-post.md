---
description: Convert any draft markdown file into a publication-ready Frontier Founder blog post — formatted, with a brand-aligned hero image, saved into the FrontierFounder repo.
argument-hint: [path to a draft .md file, or paste the draft markdown]
---

# Convert a draft into a Frontier Founder blog post

Take a rough markdown draft and turn it into a publication-ready post for The
Frontier Founder blog: format it to the blog's frontmatter spec, apply the
MoxyWolf typographic rules, generate a brand-aligned hero image, and save both
files into the FrontierFounder repo with a shared, slug-based naming convention.

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
- **Excerpt** — frontmatter `excerpt`, else write one: a single plain sentence,
  roughly 20 to 40 words, drawn from the opening. It is used on cards and as
  the search-result snippet.
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

## Step 3 — Format the body

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

## Step 4 — Inline media

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

## Step 5 — Generate the hero image

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

## Step 6 — Assemble and save

1. Build the final post: the YAML frontmatter block (see the spec below)
   followed by the formatted body.
2. Save it to `content/blog/<slug>.md` in the FrontierFounder repo.
3. If a file with that slug already exists, stop and ask the user whether to
   overwrite it or choose a different slug.

## Step 7 — Report back

Tell the user, plainly:

- The post path (`content/blog/<slug>.md`) and the hero path
  (`public/blog-hero/<slug>.png`).
- The slug — confirm the post file, the hero file, and the `heroImage` value
  all share it.
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
excerpt: "One plain sentence, roughly 20 to 40 words, used on cards and in search."
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
