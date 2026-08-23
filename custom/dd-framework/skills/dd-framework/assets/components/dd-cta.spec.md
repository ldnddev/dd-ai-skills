# dd-cta

## Purpose
Call-to-action section with background image, headline, subtitle, body, and up to two CTAs. Positioned content variants control headline placement over image.

## Context
- **Standalone.** Renders edge-to-edge.
- Use `dd-section` only if you need consistent vertical spacing wrapper — `dd-cta` already provides its own.

## Required parameters
| name | type | description |
|---|---|---|
| `title` | string | Headline (default `<h2>`). |
| `image_src` | string (URL) | Background image (default + fallback). |
| `image_alt` | string | Alt text. `""` if image is purely decorative. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `subtitle` | string | — | Rendered inside `<strong>`. |
| `body` | string (HTML) | — | Body paragraph(s). |
| `srcset` | string | — | Responsive `srcset` values. |
| `sizes` | string | `(max-width: 1440px) 100vw, 1440px` | `<source>` sizes attr. |
| `bg_mobile_url` | string | `image_src` | CSS `background-image` for narrow viewports. |
| `bg_desktop_url` | string | `image_src` | CSS `background-image` ≥ 64em. |
| `primary_cta` | object | — | `{ text, href, target }`. |
| `secondary_cta` | object | — | Same shape; rendered with `-ghost`. |
| `variant` | enum | — | See Variants. |
| `heading_level` | int | `2` | 2–6. |
| `sal` | string | `slide-up` | SAL animation. |
| `sal_duration` | int | — | ms, 200–2000 in 50 ms steps. Omit for library default (400 ms). |
| `sal_delay` | int | — | ms, 50–1000 in 50 ms steps. Omit for 0. |

## Variants
| modifier | placement of copy |
|---|---|
| `-top-left` | Top-left |
| `-top-right` | Top-right |
| `-bottom-left` | Bottom-left |
| `-bottom-right` | Bottom-right |
| `-center` | Centered |

## Canonical structure
```html
<div class="dd-cta {variant}">
  <div class="dd-cta__image">
    <img src="{image_src}" srcset="{srcset}" sizes="{sizes}" class="dd-img" alt="{image_alt}" />
  </div>
  <style>
    .dd-cta .dd-cta__image { background-image: url('{bg_mobile_url}'); }
    @media (min-width: 64em) { .dd-cta .dd-cta__image { background-image: url('{bg_desktop_url}'); } }
  </style>
  <div class="dd-cta__content dd-g" data-sal="{sal}"{% if sal_duration %} data-sal-duration="{sal_duration}"{% endif %}{% if sal_delay %} data-sal-delay="{sal_delay}"{% endif %}>
    <div class="dd-cta__copy dd-u-1-1 dd-u-md-12-24">
      <div class="dd-cta__title"><h{heading_level|default 2}>{title}</h{heading_level|default 2}></div>
      {% if subtitle %}<div class="dd-cta__subtitle"><strong>{subtitle}</strong></div>{% endif %}
      {body}
      {% if primary_cta or secondary_cta %}
      <div class="dd-cta__links dd-g -x-center">
        {% if primary_cta and primary_cta.href %}
        <div class="dd-cta__link"><a href="{primary_cta.href}" class="dd-button -primary">{primary_cta.text}</a></div>
        {% endif %}
        {% if secondary_cta and secondary_cta.href %}
        <div class="dd-cta__link"><a href="{secondary_cta.href}" class="dd-button -ghost">{secondary_cta.text}</a></div>
        {% endif %}
      </div>
      {% endif %}
    </div>
  </div>
</div>
```
See `dd-cta.html`.

**Gating:** Omit subtitle `<strong>` and CTA `<a>` when values absent. The static reference uses a `<picture><source>` pattern; `<source>` without `media` or `type` is non-functional, so canonical uses `<img srcset>` directly.

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 1.4.3, 1.4.11, 2.4.4, 2.4.7, 3.2.2.

- Headline level chosen based on parent context. Default `h2` assumes CTA sits between `h1` page hero and `h3` subsections.
- Background image: if image carries semantic info AND text overlays it, the overlay text MUST maintain ≥ 4.5:1 contrast against the image region BEHIND the text (verify worst-case pixel region, not average). Apply a CSS scrim/gradient overlay if image is busy.
- Variant placement: ensure copy region's text remains contrast-compliant given the section of image behind it (top-left over a sky vs bottom-right over a logo can differ wildly).
- Buttons: `-primary` and `-ghost` MUST both meet 4.5:1 text contrast and 3:1 non-text contrast (border/surface).
- CTAs with `target="_blank"`: add `rel="noopener noreferrer"` and an SR-only "opens in new tab" indicator so the change of context is announced before activation (technique G201, supports 3.2.2 On Input).
- Focus visible: 2px outline.
- Decorative `image_alt=""` if the background only provides ambience.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` (or `$c_text_inverse` over dark images) | title, subtitle, body |
| `$c_primary_action_*` | primary CTA states |
| `$c_secondary_action_*` or ghost vars | ghost CTA states |
| `$c_support_focus` / `--dark` | focus outline |
| `dd-u-md-12-24` (50% on tablet+) | copy width |
| `l-box` | inner padding (optional override) |

## JS hooks
- `data-sal`, optional `data-sal-duration`, optional `data-sal-delay` — SAL scroll animation. Respect `prefers-reduced-motion`.

## Example params
```json
{
  "variant": "-top-left",
  "title": "Ready to ship?",
  "subtitle": "Free during beta",
  "body": "<p>Pull a starter, render a page, deploy.</p>",
  "image_src": "/assets/imgs/cta-1920.webp",
  "image_alt": "",
  "primary_cta": { "text": "Start free", "href": "/start", "target": "_self" },
  "secondary_cta": { "text": "Docs", "href": "/docs", "target": "_self" }
}
```

## Platform translation
**Static HTML:** Direct substitution.

**Drupal Twig:**
```twig
<div class="dd-cta {{ variant }}">
  <div class="dd-cta__image">
    <picture>
      {% if srcset %}<source srcset="{{ srcset }}" sizes="{{ sizes }}">{% endif %}
      <img src="{{ image_src }}" class="dd-img" alt="{{ image_alt }}" />
    </picture>
  </div>
  <div class="dd-cta__content dd-g" data-sal="{{ sal|default('slide-up') }}"{% if sal_duration %} data-sal-duration="{{ sal_duration }}"{% endif %}{% if sal_delay %} data-sal-delay="{{ sal_delay }}"{% endif %}>
    <div class="dd-cta__copy dd-u-1-1 dd-u-md-12-24">
      <div class="dd-cta__title"><h{{ heading_level|default(2) }}>{{ title }}</h{{ heading_level|default(2) }}></div>
      {% if subtitle %}<div class="dd-cta__subtitle"><strong>{{ subtitle }}</strong></div>{% endif %}
      {{ body|raw }}
      {% if primary_cta or secondary_cta %}
      <div class="dd-cta__links dd-g -x-center">
        {% if primary_cta %}<div class="dd-cta__link"><a href="{{ primary_cta.href }}" class="dd-button -primary">{{ primary_cta.text }}</a></div>{% endif %}
        {% if secondary_cta %}<div class="dd-cta__link"><a href="{{ secondary_cta.href }}" class="dd-button -ghost">{{ secondary_cta.text }}</a></div>{% endif %}
      </div>
      {% endif %}
    </div>
  </div>
</div>
```

**WordPress:** Mirror in `render.php` with proper escape functions per field type.
