# Blog Draft Markup Template

Use these fragments when assembling the page. Skill loops over body chunks (one per `<h2>`, from `blog_helper.py split-sections`) and emits a `dd-section__item` + `dd-spacer` pair for each. The LAST chunk gets NO trailing spacer. A mid-article `dd-cta` fragment is inserted after chunk index `floor(N/2)` (see "Mid-article CTA fragment" below).

## Document scaffolding (rendered once)

Opening `<body>` tag uses the `page` class for site-wide layout hooks.

```html
<body class="page">
```

Immediately after `<body class="page">`, emit this fixed scaffolding block (legacy browser notice, skip-link, page-top anchor, htmx header include):

```html
<!--[if lt IE 8]>
  <p class="browserupgrade">You are using an <strong>outdated</strong> browser. Please <a href="http://browsehappy.com/">upgrade your browser</a> to improve your experience.</p>
<![endif]-->
<a href="#main-content" class="visually-hidden focusable skip-link">Skip to main content</a>
<div name="page_top" id="page_top"></div>
<header id="header" hx-trigger="load" hx-get="/includes/header.html" hx-swap="outerHTML"></header>
```

**Skip-link target:** `#main-content` is set on the body `<article>` wrapper (see "Body section wrapper" below). Required for WCAG 2.4.1 Bypass Blocks.

## Hero section (rendered once)

```html
<!-- hero -->
<section class="dd-hero -contained" id="dd-0001" aria-label="Introduction">
  <div class="dd-hero__image">
    <picture>
      <source srcset="./hero-sm.webp 720w, ./hero-lg.webp 1440w" sizes="(max-width: 1440px) 100vw, 1440px">
      <img src="./hero-sm.webp" class="dd-img" alt="[hero_title] [hero_copy]" />
    </picture>
  </div>
  <style>
    .dd-hero__image {
      background-image: url('./hero-sm.webp');
    }
    @media only screen and (min-width: 64em) {
      .dd-hero__image {
        background-image: url('./hero-lg.webp');
      }
    }
  </style>
  <div class="dd-hero__content dd-g" data-aos="fade-in" data-aos-duration="1000" data-aos-delay="0">
    <div class="dd-hero__copy dd-u-1-1 dd-u-lg-12-24">
      <div class="dd-hero__title">
        <h1 id="[blog_slug]">[hero_title]</h1>
      </div>
      <div class="dd-hero__body">
        <p>[hero_copy]</p>
        <div class="dd-hero__links dd-g">
          <div class="dd-hero__link">
            <a href="/contact-us/" class="dd-button -primary">Let's Talk!</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
```

## Body section wrapper (rendered once, contains the chunk loop)

Use `<article>` (not `<section>`) — the blog post body is self-contained syndicatable content. `<article>` becomes a navigable landmark in AT without needing an explicit accessible name, which avoids `aria-label`/`aria-labelledby` boilerplate and silences the `dd-framework validate` "unnamed landmark" warning.

```html
<!-- rich text | content -->
<article id="main-content" class="dd-section -full-lg">
  <div class="dd-section__content">
    <div class="dd-section__items dd-g">

      [chunk_loop]

    </div>
  </div>
</article>
```

## Chunk fragment (rendered per body chunk)

For chunk index `i` in the chunks array returned by `split-sections`:

```html
<div class="dd-section__item dd-u-1-1 l-box">
  <div class="dd-rich_text" data-aos="fade-up" data-aos-duration="1000" data-aos-delay="0">
    [chunk_content]
  </div>
</div>
[spacer_or_empty]
```

Where `[chunk_content]` rules:
- **First chunk (i = 0):** prepend the byline `<p><em>By Jared Lyvers, ldnddev — [blog_draft_date]</em></p>` before the chunk HTML.
- **Last chunk (i = len-1):** append the sign-off `<p><em>Until next time, Jared Lyvers</em></p>` after the chunk HTML.
- **Middle chunks:** chunk HTML as returned.

Where `[spacer_or_empty]` rules:
- **All chunks EXCEPT the last:** render the spacer below.
- **Last chunk:** render nothing (no spacer).

## Mid-article CTA fragment (rendered once between body chunks)

Insert after body chunk index `M = floor(N/2)` where `N` is total chunk count. Sits as a sibling `dd-section__item` inside the body article — same grid track as chunks, preserves single `<article>` landmark, AT-friendly. Emit a spacer BEFORE and AFTER this item (a spacer already exists after chunk M from the loop; only the trailing spacer is added here).

Default values:
- `image_src`: `/assets/imgs/blog-cta-default.webp`
- `image_alt`: `""` (decorative — copy carries the meaning)
- `variant`: `-center`
- `heading_level`: `2`
- `primary_cta`: `{ "text": "Let's Talk!", "href": "/contact-us/" }`
- `title`, `body`: AI-drafted at Phase 4 to tie to blog topic; user edits at Phase 5

```html
<div class="dd-section__item dd-u-1-1 l-box">
  <div class="dd-cta -center">
    <div class="dd-cta__image">
      <img src="/assets/imgs/blog-cta-default.webp" class="dd-img" alt="" />
    </div>
    <style>
      .dd-cta .dd-cta__image { background-image: url('/assets/imgs/blog-cta-default.webp'); }
      @media (min-width: 64em) { .dd-cta .dd-cta__image { background-image: url('/assets/imgs/blog-cta-default.webp'); } }
    </style>
    <div class="dd-cta__content dd-g" data-aos="fade-up" data-aos-duration="1000" data-aos-delay="0">
      <div class="dd-cta__copy dd-u-1-1 dd-u-md-12-24">
        <div class="dd-cta__title"><h2>[cta_title]</h2></div>
        [cta_body]
        <div class="dd-cta__links dd-g -x-center">
          <div class="dd-cta__link"><a href="/contact-us/" class="dd-button -primary">Let's Talk!</a></div>
        </div>
      </div>
    </div>
  </div>
</div>
```

Where `[cta_body]` is `<p>...</p>` HTML drafted to bridge the blog topic to the contact-us CTA (one short paragraph, 1-2 sentences).

## Spacer fragment

```html
<div class="dd-section__item dd-u-1-1" aria-hidden="true">
  <div class="dd-spacer -xl -divider"></div>
</div>
```

## Placeholder Reference

| Placeholder | Format | Notes |
|---|---|---|
| `[blog_slug]` | kebab-case | Derived from SEO title |
| `[hero_title]` | Plain text | First 3 words of SEO title |
| `[hero_copy]` | Plain text | SEO title minus first 3 words |
| `[blog_draft_date]` | MMMM dd, YYYY | e.g. May 16, 2026 |
| `[chunk_content]` | HTML | One `<h2>` section + paragraphs; byline prepended on first chunk, sign-off appended on last |
