# sitemap-blog Markup Template

Include this structured data block on every blog post page.

```xml
<url>
  <loc>https://ldnddev.com/blog/[blog_slug]/</loc>
  <lastmod>[blog_date]T12:13:00+00:00</lastmod>
  <priority>0.80</priority>
</url>
```

## Placeholder Reference

| Placeholder | Format | Notes |
|---|---|---|
| `[SEO_Title]` | Plain text | Full SEO page title |
| `[blog_slug]` | kebab-case | Derived from SEO title |
| `[blog_date]` | YYYY-mm-dd | e.g. 2026-03-15 |
