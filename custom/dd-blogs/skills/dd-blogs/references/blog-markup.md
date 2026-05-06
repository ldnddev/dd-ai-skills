# Blog Draft Markup Template

Use this HTML template for every blog post. Replace all `[placeholder]` values before outputting.

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

<!-- rich text | content -->
<section class="dd-section -full-lg">
  <div class="dd-section__content">
    <div class="dd-section__items dd-g">

      <!-- intro -->
      <div class="dd-section__item dd-u-1-1 l-box">
        <div class="dd-rich_text" data-aos="fade-up" data-aos-duration="1000" data-aos-delay="0">
          <p><em>By Jared Lyvers, ldnddev — [blog_draft_date]</em></p>
          [blog_draft]
          [blog_draft_end]
        </div>
      </div>
      <div class="dd-section__item dd-u-1-1">
        <div class="dd-spacer -xl -divider"></div>
      </div>
    </div>
  </div>
</section>
```

## Placeholder Reference

| Placeholder | Format | Notes |
|---|---|---|
| `[blog_slug]` | kebab-case | Derived from SEO title |
| `[hero_title]` | Plain text | First 3 words of SEO title |
| `[hero_copy]` | Plain text | SEO title minus first 3 words |
| `[blog_draft_date]` | MMMM dd, YYYY | e.g. March 15, 2026 |
| `[blog_draft]` | HTML | 1800–2200 words, use `<h2>` to start each new section |
| `[blog_draft_end]` | Plain text | Always: "Until next time, Jared Lyvers" |
