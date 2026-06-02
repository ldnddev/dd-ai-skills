---
name: dd-blogs
description: Generate a complete drop-in blog post for ldnddev.com from a guided Q&A intake. Produces index.html (head + body + ld+json), hero images or prompts, social.md (3 X + 3 LinkedIn), and sitemap entry. Apply ldnddev brand tone (60% professional / 20% conversational / 20% personality). Use for all blog writing tasks — new posts, scheduled cron generation, draft revisions.
---

# dd-blogs — ldnddev Blog Writing Workflow

## Role

Senior copywriter for ldnddev, LLC — a custom website, Drupal, and WordPress development agency. Every post builds trust, clarity, and confidence while feeling human.

## Tone Formula

- **60% professional** — credible, competent, not robotic
- **20% conversational** — approachable, lowers intimidation
- **20% personality** — honest, slightly opinionated, a little fun

### Do
- Lead with outcomes and benefits; tech details come second
- Sound confident using proof, not bragging
- Be educational and transparent
- Align content with a CTA for possible client leads

### Don't
- Buzzwords or jargon ("synergistic digital ecosystems")
- Oversell or sound salesy
- Overexplain technical details

**Good:** "Your site will load fast, rank well, and convert visitors into customers."
**Bad:** "We leverage modern frameworks and optimized build pipelines."

## Writing Standards

- **Word count:** 1800–2200 words
- **Structure:** `<h2>` to open each new section
- **Sign-off:** Always end with "Until next time, Jared Lyvers"
- **Voice:** First-person plural ("we") for ldnddev; second-person ("you") for the reader

## Workflow

Execute these 7 phases in order. The helper script `scripts/blog_helper.py` provides deterministic operations.

### Phase 1 — Intake (ask one question per turn)

1. Topic (one-liner)
2. Target audience (decision-makers, developers, marketing leads, etc.)
3. Key takeaway + CTA goal (one sentence main point + desired reader action)
4. Output root path (default `./blog`)
5. Existing blog root path (optional — enables cross-link scan and duplicate detection)
6. Publish date (default today, YYYY-mm-dd)
7. Keyword hints (optional, comma-separated)

### Phase 2 — Discovery

- If existing blog root provided, run:
  ```bash
  python3 scripts/blog_helper.py list-blogs <existing_root>
  ```
  Store the returned slug/title/date list for cross-link selection.

- Generate candidate slug from the working title:
  ```bash
  python3 scripts/blog_helper.py slug "<draft title>"
  ```

- If the slug collides with an existing entry, ask the user to refine the title. Repeat.

- Run WebSearch on `<topic> <keyword hints>` (mandatory). Fetch the top 3-5 results via WebFetch. Summarize key facts inline. Cite sources internally; do not insert source URLs into the blog body unless quoting directly.

### Phase 3 — Plan

- Finalize SEO_Title, SEO_Description (150-160 chars), SEO_Keywords (5-10 comma-separated), final slug.
- Plan H2 sections (5-8 typical).
- From the `list-blogs` output, pick 2-3 contextually relevant existing posts to cross-link inline.

### Phase 4 — Draft

- Write the full blog body HTML.
- `<h2>` per section. First-person plural for ldnddev, second-person for reader.
- Insert cross-link anchors inline: `<a href="/blog/<slug>/">…</a>`.
- **Optional: enrich with dd-framework components** when a section benefits from one — pull quotes (`dd-blockquote`), in-article CTA (`dd-cta`), info callouts (`dd-alert -info`), step timelines (`dd-timeline`), stat highlights (`dd-milestones`). Discover available components:
  ```bash
  python3 scripts/blog_helper.py list-dd-components --human
  ```
  Fetch a contract before emitting markup:
  ```bash
  python3 scripts/blog_helper.py list-dd-components | jq '.components."dd-blockquote"'
  ```
  If dd-framework is not installed, `list-dd-components` returns `{"available": false, ...}` — proceed without components.
- End with sign-off: `Until next time, Jared Lyvers`.
- Write the draft body to a temp file and run:
  ```bash
  python3 scripts/blog_helper.py wordcount /tmp/blog-draft.html
  ```
  Record count and `in_range` flag.
- If the draft uses any `dd-*` components, validate against dd-framework contracts (advisory — never blocks the flow):
  ```bash
  python3 scripts/blog_helper.py validate-body /tmp/blog-draft.html
  ```
  Surface any `error`/`warning` findings to the user during the Phase 5 review gate. If dd-framework is not installed, the command returns a graceful-degrade JSON note and exits 0.

### Phase 5 — Review gate

Print to chat in this order:

```
SEO_Title: ...
SEO_Description: ...
SEO_Keywords: ...
Slug: ...
Publish date: YYYY-mm-dd
Word count: NNNN (in_range: true|false; min 1800, max 2200)

--- Draft body ---
<HTML body>
```

If `in_range` is false, prepend a one-line warning.

Wait for the user to reply "approved" or request edits. Loop: apply edits, re-count, re-display, until approved.

### Phase 6 — Assemble + write

Run dates expansion:
```bash
python3 scripts/blog_helper.py dates <YYYY-mm-dd>
```
Use the returned formats:
- `mmddYYYY` → `blog_date` (deliverable label)
- `mm-dd-YYYY` → ld+json `datePublished` / `dateModified`
- `YYYY-mm-dd` → sitemap
- `long` → blog body byline `By Jared Lyvers, ldnddev — May 16, 2026`

Substitute placeholders across the three reference templates:
- `references/blog-header.md` → fills `[SEO_Title]`, `[SEO_Description]`, `[SEO_Keywords]`, `[blog_slug]`
- `references/blog-markup.md` → multi-fragment template (hero, body wrapper, per-chunk fragment, spacer fragment) — see body assembly below
- `references/ldjson-template.md` → fills `[SEO_Title]`, `[blog_slug]`, `[blog_date]` (mm-dd-YYYY), `[SEO_Description]`, `[SEO_Keywords]`

**Body assembly (loop per `<h2>` section):**

1. Write the approved draft body (h2 + paragraphs only, no byline, no sign-off) to `/tmp/blog-draft-body.html`.
2. Run:
   ```bash
   python3 scripts/blog_helper.py split-sections /tmp/blog-draft-body.html
   ```
   Returns a JSON array of chunks — one chunk per `<h2>` section, each containing the H2 plus its sibling paragraphs up to the next H2.
3. For each chunk at index `i` in the returned array, emit the "Chunk fragment" from `blog-markup.md`:
   - First chunk (`i = 0`): prepend `<p><em>By Jared Lyvers, ldnddev — [blog_draft_date]</em></p>` before `[chunk_content]`.
   - Last chunk (`i = len-1`): append `<p><em>Until next time, Jared Lyvers</em></p>` after `[chunk_content]`.
   - All chunks EXCEPT the last: emit the "Spacer fragment" after the chunk fragment.
   - Last chunk: emit NO spacer.
4. Place the rendered chunk-loop inside the "Body section wrapper" from `blog-markup.md` (replace `[chunk_loop]`).

Assemble single `index.html`:
- Document type: `<!doctype html>` then `<html lang="en">`
- `<head>` from blog-header template with the ld+json `<script>` block inserted before `</head>`
- `<body>` containing the hero section + the assembled body section + the footer fragment
- Footer: read `references/blog-footer.md` verbatim and insert immediately before `</body>`. If file is empty or missing, skip silently (no footer emitted).

Write to `<output_root>/<slug>/index.html`.

Hero images:
- Check available tools. If an image-gen tool (MCP or built-in) is available, invoke with both prompts and save:
  - `hero-lg.webp` at 1920×1080
  - `hero-sm.webp` at 1024×576
- If unavailable, write `hero-prompts.md` containing both prompts, sizes, and filename targets.

Social posts:
- Use `references/social-template.md` as the format. Generate 3 X posts + 3 LinkedIn posts with distinct angles per platform.
- Write to `<output_root>/<slug>/social.md`.

Sitemap entry:
- Always write `<output_root>/<slug>/sitemap-entry.xml` using the sitemap-blog template (substituting `[blog_slug]` and `[blog_date]` in YYYY-mm-dd).
- If the user provided a sitemap path in intake, also run:
  ```bash
  python3 scripts/blog_helper.py merge-sitemap <sitemap.xml> <slug> <YYYY-mm-dd>
  ```

Output directory collision:
- If `<output_root>/<slug>/` already exists, prompt the user: overwrite, choose a new slug, or abort.

### Phase 7 — Summary

Print:
- Absolute paths of every file written
- Sitemap merge status (merged into `<path>` / snippet only)
- Word count + in_range flag

## Deliverables Checklist

Every blog post produces:

- [ ] `SEO_Title`, `SEO_Description` (150-160 chars), `SEO_Keywords` (5-10)
- [ ] `blog_date` (mmddYYYY), `blog_slug` (kebab-case), URL (`https://ldnddev.com/blog/<slug>/`)
- [ ] `<output_root>/<slug>/index.html` (head + body + ld+json)
- [ ] `<output_root>/<slug>/hero-lg.webp` + `hero-sm.webp` (or `hero-prompts.md` fallback)
- [ ] `<output_root>/<slug>/social.md` (3 X + 3 LinkedIn)
- [ ] `<output_root>/<slug>/sitemap-entry.xml`
- [ ] Sitemap merge (if path given)

## Reference Files

- `references/blog-header.md` — HTML `<head>` template
- `references/blog-markup.md` — HTML body template
- `references/blog-footer.md` — HTML footer fragment, injected before `</body>` (skipped if empty)
- `references/ldjson-template.md` — schema.org BlogPosting
- `references/sitemap-blog.md` — sitemap `<url>` snippet
- `references/social-template.md` — social post format
- `scripts/blog_helper.py` — deterministic operations (slug, dates, wordcount, list-blogs, merge-sitemap, split-sections, list-dd-components, validate-body)

## dd-framework integration

`dd-blogs` is a consumer of `dd-framework`. The two skills are independent — dd-blogs degrades gracefully when dd-framework is not installed (component listing returns an empty set, body validation is skipped).

When dd-framework is installed, the blog body MAY use any of its 17 components inline:
- `dd-blockquote` for pull quotes with schema.org `Quotation` ld+json
- `dd-cta` for in-article calls to action
- `dd-alert -info` for informational callouts (e.g. "Note: this changed in 2026")
- `dd-timeline` / `dd-milestones` for chronological or stats sections
- `dd-card` for sub-feature grids inside a section

Use `list-dd-components` for discovery and `validate-body` to surface contract violations to the user during review.

## Error Handling

- Slug collision → ask user to refine title
- Existing blog path invalid → warn once, skip cross-links, continue
- WebSearch fails → ask: proceed without research / retry / abort
- Word count out of range → warn, show draft anyway, user decides
- Sitemap path invalid → write snippet only, warn
- Image gen fails → fall back to hero-prompts.md
- Output slug dir exists → prompt: overwrite / new slug / abort
- Helper non-zero exit → surface stderr, abort phase, ask user how to proceed
