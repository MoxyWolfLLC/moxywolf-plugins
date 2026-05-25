# frontier-founder

Tooling for **The Frontier Founder** site. One command today — `/blog-post` — with room to grow as the project needs more.

## `/blog-post` — convert a draft into a blog post

The Frontier Founder blog is file-based: every post is a markdown file in the FrontierFounder repo's `content/blog/`, with a hero image in `public/blog-hero/` and inline media in `public/blog-media/`. Each post carries a specific YAML frontmatter block, and the build fails if a published post references a file that was never uploaded.

`/blog-post` takes all of that off the writer's plate. Hand it a rough markdown draft — pasted, uploaded, or a file path — and it:

- Derives the post's identity: title, a kebab-case **slug**, excerpt, category, date, author.
- Writes the frontmatter block to the blog's spec.
- Formats the body — headings from `##`, typographer's quotes, en-dashes not em-dashes — without rewriting the author's words.
- Builds the `media` array from inline references and flags any media files still to be uploaded.
- Generates a **brand-aligned abstract** hero image, 16:9, in the Frontier Founder palette.
- Saves the post to `content/blog/<slug>.md` and the hero to `public/blog-hero/<slug>.png` — post file, hero file, and the `heroImage` path all share one slug.

The draft author does not need to be working in the Frontier Founder Cowork project, or know anything about the blog's conventions. The command locates the FrontierFounder repo, supplies every convention, and leaves the post as `status: draft` for review.

## How to use

In a Cowork session with the **GitHub** root mounted, type `/blog-post` and hand it the draft:

```
/blog-post ~/Desktop/agents-and-the-org-chart.md
```

or paste the markdown after the command. Review the result, flip `status` to `published`, then commit and push — the post goes live on the next deploy.

## Requirements

- The **GitHub** root mounted in Cowork → Folders, with the FrontierFounder repo inside it.
- An image-generation tool or skill available in the session for the hero image. Without one, the command still saves the formatted post and tells you the hero is pending.

## Version history

- **0.1.0** — Initial release. `/blog-post` draft-to-post converter with brand-aligned hero generation and slug-tied file naming.
