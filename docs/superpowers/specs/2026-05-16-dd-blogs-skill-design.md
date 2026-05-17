# dd-blogs Skill Conversion — Design Spec

**Date:** 2026-05-16
**Author:** Jared Lyvers
**Status:** Approved for implementation planning

## Goal

Convert `custom/dd-blogs/` from a guidelines-only skill into an executable workflow that produces a complete, drop-in blog post for ldnddev.com from a guided Q&A intake in a single Claude Code session.

## Current State

The existing skill at `custom/dd-blogs/skills/dd-blogs/` contains:

- `SKILL.md` — brand tone formula, deliverables checklist, references to templates
- `references/blog-header.md` — HTML `<head>` template with placeholders
- `references/blog-markup.md` — HTML body template with placeholders
- `references/ldjson-template.md` — schema.org `BlogPosting` template
- `references/sitemap-blog.md` — sitemap `<url>` snippet template

It instructs the model on tone and required deliverables but has no execution flow, no scaffolder, no deterministic helpers, and produces output only in chat. Date formats differ across templates (`mmddYYYY`, `mm-dd-YYYY`, `YYYY-mm-dd`, long form).

## Non-Goals

- Publishing blog posts to a live site or CMS
- Image generation infrastructure (skill detects available tools; otherwise emits prompts)
- Modifying the existing site templates downstream (preserve current date format contracts)
- Backwards compatibility with the 1.0 skill API (single user, full replace OK)

## Architecture

### Layout

```
custom/dd-blogs/
├── .claude-plugin/plugin.json        (bump to 2.0.0)
├── install.sh                        (copy SKILL.md + references + scripts to ~/.codex)
├── README.md                         (rewrite for new flow)
└── skills/dd-blogs/
    ├── SKILL.md                      (rewritten — drives full workflow)
    ├── scripts/
    │   └── blog_helper.py            (NEW — stdlib only)
    └── references/
        ├── blog-header.md            (kept)
        ├── blog-markup.md            (kept)
        ├── ldjson-template.md        (kept)
        ├── sitemap-blog.md           (kept)
        └── social-template.md        (NEW)
```

### Per-blog output

Target directory is configurable per-run (default `./blog/`). Skill writes to `<output_root>/<slug>/`:

```
<output_root>/<slug>/
├── index.html          (full HTML document — head + body + ld+json inline)
├── hero-lg.webp        (or omitted; prompts written instead)
├── hero-sm.webp        (or omitted; prompts written instead)
├── hero-prompts.md     (only when image gen unavailable)
├── social.md           (3 X posts + 3 LinkedIn posts)
└── sitemap-entry.xml   (snippet; merged into site sitemap if path given)
```

## Components

### blog_helper.py

CLI tool. Python 3, stdlib only. Each subcommand exits non-zero on error; outputs JSON on success (except `slug` which returns plain text for ergonomic shell use).

| Subcommand | Args | Output |
|---|---|---|
| `slug` | `<title>` | kebab-case slug (stdout, plain text) |
| `dates` | `<YYYY-mm-dd>` | JSON: `{mmddYYYY, mm-dd-YYYY, YYYY-mm-dd, long}` |
| `wordcount` | `<file>` | JSON: `{count, in_range, min:1800, max:2200}` |
| `list-blogs` | `<blog_root>` | JSON array: `[{slug,title,date,path}, ...]` |
| `merge-sitemap` | `<sitemap.xml> <slug> <YYYY-mm-dd>` | Writes file in place, exits 0. Backs up to `<sitemap.xml>.bak`. Skips if `<loc>` already present (idempotent). |

**Slug rules:** lowercase ASCII, alphanumeric + hyphens, leading numbers preserved, multiple hyphens collapsed, leading/trailing hyphens stripped. Strip non-ASCII via NFKD normalization.

**list-blogs parsing:** regex against known templates. Extracts:
- `title` from `<title>ldnddev, LLC. Insights | (.+?)</title>`
- `slug` from canonical href tail
- `date` from ld+json `datePublished` (template emits `mm-dd-YYYY`; helper normalizes output to `YYYY-mm-dd` for sortable comparison)

Skips dirs lacking `index.html` silently.

**merge-sitemap:** parses with `xml.etree.ElementTree`, inserts `<url>` sorted by `<loc>`, writes back preserving declaration. Idempotent.

### SKILL.md

Drives the seven-phase workflow inline. Calls `blog_helper.py` via Bash. Uses WebSearch / WebFetch for the research pass. Uses Write/Edit for file output.

## Workflow

### Phase 1 — Intake (guided Q&A, one question per turn)

1. Topic (one-liner)
2. Target audience
3. Key takeaway + CTA goal
4. Output root path (default `./blog`)
5. Existing blog root path (optional)
6. Publish date (default today)
7. Keyword hints (optional)

### Phase 2 — Discovery

- If existing root provided: `blog_helper.py list-blogs <root>`
- Generate candidate slug: `blog_helper.py slug "<draft title>"`
- If slug collides with existing: ask user to refine title, repeat
- WebSearch on `<topic> <keyword hints>` (mandatory)
- WebFetch top 3-5 results, summarize key facts inline

### Phase 3 — Plan

- Finalize SEO_Title, SEO_Description (150-160 chars), SEO_Keywords (5-10), slug
- Plan H2 sections
- From `list-blogs` output, select 2-3 contextually relevant existing posts for inline cross-links

### Phase 4 — Draft

- Write blog body HTML (`<h2>` per section, first-person plural for ldnddev, second-person for reader)
- Insert cross-link anchors inline
- Sign-off: "Until next time, Jared Lyvers"
- Run `blog_helper.py wordcount` on draft → record count + in_range

### Phase 5 — Review gate

- Print to chat: SEO_Title, SEO_Description, SEO_Keywords, word count, in_range flag, draft body
- Wait for user approval or edits
- Loop: apply edits, re-count, re-display, until approved

### Phase 6 — Assemble + write

- `blog_helper.py dates <publish_date>` → 4 formats
- Substitute placeholders across blog-header, blog-markup, ldjson-template
- Concatenate into single `index.html` (header `<head>` includes ld+json `<script>`; body uses markup template)
- Hero images:
  - Detect available image gen tool (MCP scan)
  - If found: invoke with both prompts, save `hero-lg.webp` + `hero-sm.webp`
  - Else: write `hero-prompts.md` containing both prompts, sizes, filenames
- Write `social.md` from social-template.md with 3 X posts (≤280 chars, three distinct angles: hook, stat/insight, question) + 3 LinkedIn posts (1200-2000 chars, three angles: problem-first, lessons-learned, direct CTA). Each post includes blog URL.
- Write `sitemap-entry.xml` (snippet always)
- If sitemap path given: `blog_helper.py merge-sitemap`

### Phase 7 — Summary

- Print absolute paths of every file written
- Print sitemap merge status (merged / snippet only)
- Print word count + range status

## Data Flow

```
user topic
  → intake Q&A
  → list-blogs (existing) ─┐
  → WebSearch + WebFetch ──┤
                           ↓
                       plan (slug, SEO, outline, cross-links)
                           ↓
                       draft (body HTML + wordcount)
                           ↓
                       review gate (user)
                           ↓
                       dates expansion (helper)
                           ↓
                       template substitution (Claude)
                           ↓
                       file writes (index.html, social.md, sitemap-entry.xml)
                           ↓
                       optional: image gen, sitemap merge
                           ↓
                       summary
```

## Error Handling

| Failure mode | Behavior |
|---|---|
| Slug collision in existing blogs | Ask user to refine title; repeat slug gen |
| Existing blog path invalid/missing | Warn once; skip discovery + cross-links; continue |
| WebSearch fails | Warn; ask user: proceed without research / retry / abort |
| Word count out of range | Print warning with count; show draft anyway; user decides |
| Sitemap path invalid | Write snippet only; warn |
| Image gen tool call fails | Fall back to `hero-prompts.md` |
| Output slug dir already exists | Prompt: overwrite / new slug / abort |
| `blog_helper.py` returns non-zero | Surface stderr to user; abort phase, ask how to proceed |

## Testing

### Unit tests for `blog_helper.py`

Pytest suite at `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`. Covers:

- `slug`: unicode (curly apostrophes, em-dash), punctuation, leading numbers, multi-space, leading/trailing whitespace
- `dates`: leap year, single-digit month/day padding, January 1
- `wordcount`: HTML-tag stripping, in_range boundaries (1799, 1800, 2200, 2201)
- `list-blogs`: empty dir, malformed index.html, missing fields, valid sample
- `merge-sitemap`: empty sitemap, existing entries, sorted insertion, idempotent re-run, backup created

### Manual smoke test

End-to-end run against a fake blog root with 2-3 sample blogs. Verify:

- All output files land at expected paths
- index.html parses as valid HTML5
- ld+json validates against schema.org BlogPosting
- Sitemap merge inserts in correct sorted position
- Cross-links resolve to real existing slugs
- Word count lands in 1800-2200

### Out of scope

- Automated WebSearch tests (network-dependent)
- Image gen integration tests (tool availability varies)

## Migration

The skill is single-user. Replace `custom/dd-blogs/` contents in place:

- Bump plugin.json to 2.0.0
- Rewrite SKILL.md
- Add `scripts/blog_helper.py` + tests
- Add `references/social-template.md`
- Rewrite README.md to document new flow
- `install.sh` updated to copy scripts/ subdir

No backwards-compat shims. Old trigger phrases (`write a blog post about <topic>`) still work — they enter the new intake flow.

## Open Questions

None at design time. All resolved during brainstorm.
