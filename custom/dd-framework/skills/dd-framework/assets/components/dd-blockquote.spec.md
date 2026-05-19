# dd-blockquote

## Purpose
Testimonial quotation with attribution (person photo, name, title) and structured-data markup via schema.org `Quotation`.

## Context
- Wraps in `dd-section`.
- Uses semantic `<blockquote>` element at root.
- JSON-LD `<script type="application/ld+json">` co-located with markup for SEO. Drupal/WP installs may render JSON-LD in document `<head>` instead — see Platform translation.

## Required parameters
| name | type | description |
|---|---|---|
| `quote` | string (HTML) | Quotation body. |
| `name` | string | Quoted person's name. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `title` | string | — | Job title / role. Rendered with leading comma. |
| `image_src` | string (URL) | — | Person photo. |
| `image_alt` | string | `name` | Alt text. Defaults to person name if photo. |
| `icon_class` | string | `fa-regular fa-message-quote` | Font Awesome icon class for decorative quote glyph. |
| `aos` | string | `fade-in` | AOS animation. |
| `emit_jsonld` | boolean | `true` | Whether to render the JSON-LD script. Disable when site centralizes structured data. |
| `cite_url` | string (URL) | — | Source URL for the quotation. Renders as `cite` attribute on `<blockquote>`. |

## Variants
None.

## Canonical structure
```html
<blockquote class="dd-blockquote" {% if cite_url %}cite="{cite_url}"{% endif %}>
  <div class="dd-blockquote__content dd-g" data-aos="{aos}">
    <div class="dd-blockquote__icon" aria-hidden="true"><i class="{icon_class}"></i></div>
    <div class="dd-blockquote__person dd-g l-box">
      {% if image_src %}
      <div class="dd-blockquote__image">
        <img src="{image_src}" alt="{image_alt|default name}" />
      </div>
      {% endif %}
      <div class="dd-blockquote__name-title">
        <cite>
          <span class="dd-blockquote__name">{name}</span>
          {% if title %}<span class="dd-blockquote__title">, {title}</span>{% endif %}
        </cite>
      </div>
      <div class="dd-blockquote__comment">{quote}</div>
    </div>
  </div>
</blockquote>
{% if emit_jsonld %}
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Quotation",
  "creator": { "@type": "Person", "name": "{name}" },
  "text": "{quote_plaintext}"
}
</script>
{% endif %}
```
See `dd-blockquote.html`. **Note:** the static reference has a broken `data-aos` attribute (missing closing quote) — the canonical structure above corrects it.

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 1.4.3, 2.4.4.

- `<blockquote>` is the semantic root — SR announces "quote".
- Decorative icon `<i>` should carry `aria-hidden="true"` AND no interactive children. Font Awesome glyphs without text equivalent are invisible to AT — that's correct for decoration.
- Person photo `alt` defaults to the name. If photo is purely decorative beside an already-named person, `alt=""` is acceptable.
- Quote text contrast ≥ 4.5:1 against surface.
- If the quoted person has a citation URL, add `<cite><a href="...">{name}</a></cite>` and a `cite="..."` attribute on `<blockquote>`.
- JSON-LD adds no UI; safe but ensure `quote_plaintext` is escaped (no raw HTML).

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | quote body, name |
| `$c_text_secondary` / `--dark` | title |
| `$c_primary_subtle` / `--dark` | optional surface tint |
| `$c_support_border` / `--dark` | left rule (if rendered) |

## JS hooks
- `data-aos="fade-in"` — AOS scroll-in.
- Font Awesome library required for icon (loaded once globally).

## Example params
```json
{
  "quote": "<p>The dd-framework cut our page build time in half.</p>",
  "name": "Jane Doe",
  "title": "Senior Frontend Engineer",
  "image_src": "/assets/imgs/jane.webp",
  "image_alt": "Jane Doe smiling"
}
```

## Platform translation
**Static HTML:** Substitute directly. Keep JSON-LD inline.

**Drupal Twig (`dd-blockquote.html.twig`):**
```twig
<blockquote class="dd-blockquote">
  <div class="dd-blockquote__content dd-g" data-aos="{{ aos|default('fade-in') }}">
    <div class="dd-blockquote__icon" aria-hidden="true"><i class="{{ icon_class|default('fa-regular fa-message-quote') }}"></i></div>
    <div class="dd-blockquote__person dd-g l-box">
      {% if image_src %}<div class="dd-blockquote__image"><img src="{{ image_src }}" alt="{{ image_alt|default(name) }}" /></div>{% endif %}
      <div class="dd-blockquote__name-title">
        <span class="dd-blockquote__name">{{ name }}</span>
        {% if title %}<span class="dd-blockquote__title">, {{ title }}</span>{% endif %}
      </div>
      <div class="dd-blockquote__comment">{{ quote|raw }}</div>
    </div>
  </div>
</blockquote>
{% if emit_jsonld is not defined or emit_jsonld %}
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Quotation",
  "creator": { "@type": "Person", "name": {{ name|json_encode|raw }} },
  "text": {{ quote|striptags|json_encode|raw }}
}
</script>
{% endif %}
```

**WordPress:** Use `wp_kses_post` for `quote`, output JSON-LD via `wp_print_inline_script_tag` or register in `wp_head`. Centralized SEO plugins (Yoast, RankMath) may already handle structured data — disable `emit_jsonld` to avoid duplication.
