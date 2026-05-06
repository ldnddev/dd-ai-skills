# ld+json Markup Template

Include this structured data block on every blog post page.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "[SEO_Title]",
  "image": "https://www.ldnddev.com/blog/[blog_slug]/hero-lg.webp",
  "datePublished": "[blog_date]",
  "dateModified": "[blog_date]",
  "author": {
    "@type": "Organization",
    "name": "Jared Lyvers",
    "url": "https://x.com/jaredlyvers01"
  },
  "publisher": {
    "@type": "Organization",
    "name": "ldnddev, LLC",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.ldnddev.com/assets/imgs/logo-box-solid.webp"
    }
  },
  "description": "[SEO_Description]",
  "keywords": "[SEO_Keywords]",
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://www.ldnddev.com/blog/[blog_slug]/"
  }
}
</script>
```

## Placeholder Reference

| Placeholder | Format | Notes |
|---|---|---|
| `[SEO_Title]` | Plain text | Full SEO page title |
| `[blog_slug]` | kebab-case | Derived from SEO title |
| `[blog_date]` | mm-dd-YYYY | e.g. 03-15-2026 |
| `[SEO_Description]` | Plain text | 150–160 character meta description |
| `[SEO_Keywords]` | Comma-separated | 5–10 relevant keywords |
