# dd-blogs — ldnddev Blog Writing Skill

Brand-tone copywriting skill for ldnddev.com blog posts. Enforces voice, structure, and a deliverables checklist (HTML markup, ld+json, SEO meta, social posts, hero image prompts).

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-blogs@dd-skills
```

No deps. Loads instantly.

## Install — Codex skill

`bash install.sh` from this directory. See [root README](../../README.md#codex-install-legacy) for context.

## Trigger phrases

- "write a blog post about <topic>"
- "draft an ldnddev blog on <topic>"
- "revise this blog draft" (paste draft)
- Weekly cron blog generation

## Deliverables (per post)

- `SEO_Title`, `SEO_Description`, `SEO_Keywords`
- `blog_date` (mmddYYYY), `blog_slug`, `URL`
- Blog header HTML (template: `references/blog-header.md`)
- Blog body HTML (template: `references/blog-markup.md`)
- ld+json structured data (template: `references/ldjson-template.md`)
- Hero image prompts (1920×1080 + 1024×576)
- Social posts: 3 each for X.com and LinkedIn

## Layout

```
dd-blogs/
├── .claude-plugin/plugin.json
├── install.sh
└── skills/dd-blogs/
    ├── SKILL.md
    └── references/
        ├── blog-header.md
        ├── blog-markup.md
        ├── ldjson-template.md
        └── sitemap-blog.md
```

## Tone formula

60% professional / 20% conversational / 20% personality. Sign-off: "Until next time, Jared Lyvers". Word count: 1800–2200.
