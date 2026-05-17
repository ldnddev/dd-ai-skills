# dd-blogs — ldnddev Blog Generator Skill

Guided blog generator for ldnddev.com. Walks you through a 7-phase workflow — intake, research, plan, draft, review, assemble, summary — and produces a drop-in blog directory.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-blogs@dd-skills
```

## Install — Codex skill

`bash install.sh` from this directory. See [root README](../../README.md#codex-install-legacy) for context.

## Trigger phrases

- "write a blog post about <topic>"
- "draft an ldnddev blog on <topic>"
- "revise this blog draft" (paste draft)
- Weekly cron blog generation

## Workflow

1. **Intake** — Skill asks: topic, audience, takeaway + CTA, output path, existing blog root, publish date, keywords
2. **Discovery** — Lists existing blogs, runs WebSearch + WebFetch for grounding
3. **Plan** — Locks SEO meta, slug, H2 outline, cross-link targets
4. **Draft** — Writes blog body, validates word count (1800–2200)
5. **Review gate** — You approve or edit; loop until approved
6. **Assemble** — Writes index.html, hero images (or prompts), social.md, sitemap entry
7. **Summary** — Prints all written paths + merge status

## Per-blog output

```
<output_root>/<slug>/
├── index.html         # full HTML doc (head + body + ld+json)
├── hero-lg.webp       # or hero-prompts.md fallback
├── hero-sm.webp
├── social.md          # 3 X + 3 LinkedIn posts
└── sitemap-entry.xml  # also merged into site sitemap if path given
```

## Layout

```
dd-blogs/
├── .claude-plugin/plugin.json
├── install.sh
└── skills/dd-blogs/
    ├── SKILL.md
    ├── scripts/
    │   ├── blog_helper.py
    │   └── test_blog_helper.py
    └── references/
        ├── blog-header.md
        ├── blog-markup.md
        ├── ldjson-template.md
        ├── sitemap-blog.md
        └── social-template.md
```

## Tone formula

60% professional / 20% conversational / 20% personality. Sign-off: "Until next time, Jared Lyvers". Word count: 1800–2200.

## Helper CLI

`scripts/blog_helper.py` provides deterministic ops the skill calls during the workflow:

| Subcommand | Purpose |
|---|---|
| `slug "<title>"` | kebab-case slug |
| `dates YYYY-mm-dd` | JSON: 4 date formats (mmddYYYY, mm-dd-YYYY, YYYY-mm-dd, long) |
| `wordcount <file>` | JSON: count, in_range, min, max |
| `list-blogs <root>` | JSON: existing blogs (slug, title, date, path) |
| `merge-sitemap <sitemap.xml> <slug> <YYYY-mm-dd>` | inserts `<url>` sorted, idempotent, creates .bak |

Run tests: `cd skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v`
