# Blog Draft Markup Template

Use these fragments when assembling the page. Skill loops over body chunks (one per `<h2>`, from `blog_helper.py split-sections`) and emits a `dd-section__item` + `dd-spacer` pair for each. The LAST chunk gets NO trailing spacer.

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

```html
<!-- rich text | content -->
<section class="dd-section -full-lg">
  <div class="dd-section__content">
    <div class="dd-section__items dd-g">

      [chunk_loop]

    </div>
  </div>
</section>
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
