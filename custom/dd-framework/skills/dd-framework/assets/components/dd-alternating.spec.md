# dd-alternating

## Purpose
Image-and-copy rows where image position alternates (left/right) row-to-row — for feature lists, product showcases, and storytelling layouts.

## Context
- Wraps in `dd-section`.
- Alternation is purely visual (CSS `:nth-child` or row-class flips column order). Do NOT reorder DOM to achieve alternation; that breaks reading order.

## Required parameters
| name | type | description |
|---|---|---|
| `items` | array of `row` | One per alternating row. |

### `row` shape
| name | type | description |
|---|---|---|
| `title` | string (required) | Row heading (default `<h2>`). |
| `body` | string (HTML) (required) | Copy block. |
| `image_src` | string (URL) (required) | Image asset. |
| `image_alt` | string (required) | Alt text. `""` if decorative. |
| `links` | array of `{text, href, variant}` | Optional CTAs. |
| `heading_level` | int | Optional override 2–6. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `aria_label` | string | — | Section landmark label if used in addition to `dd-section`. |
| `aos` | string | `fade-up` | AOS animation per row. |

## Variants
None at root. Row alternation is automatic via CSS.

## Canonical structure
```html
<!-- Emit role+aria-label ONLY when aria_label is provided. A landmark without an accessible name fails axe `region`. -->
<div class="dd-alternating" {% if aria_label %}role="region" aria-label="{aria_label}"{% endif %}>
  <div class="dd-alternating__items dd-g">
    <!-- repeat per item; default heading_level = 2 -->
    <div class="dd-alternating__item dd-u-1-1">
      <div class="dd-alternating__content dd-g">
        <div class="dd-alternating__image dd-u-1-1 dd-u-lg-12-24" data-aos="{aos}">
          <img src="{image_src}" class="dd-img" alt="{image_alt}" />
        </div>
        <div class="dd-alternating__copy l-box dd-u-1-1 dd-u-lg-12-24" data-aos="{aos}">
          <div class="dd-alternating__title"><h{heading_level|default 2}>{title}</h{heading_level|default 2}></div>
          <div class="dd-alternating__body">
            {body}
            {% if links %}
            <div class="dd-alternating__links">
              <div class="dd-alternating__link">
                <a href="{links[].href}" class="dd-button {links[].variant}">{links[].text}</a>
              </div>
            </div>
            {% endif %}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```
See `dd-alternating.html`.

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 1.3.2 Meaningful Sequence, 1.4.3, 1.4.10 Reflow, 1.4.12 Text Spacing, 2.4.6, 2.4.7.

- `role="region"` requires an accessible name. **Only emit the role + `aria-label` when `aria_label` is provided** — a landmark without a name is invalid and fails axe `region`/`landmark-unique`.
- 1.4.10 Reflow: alternating columns must stack to single column at 320 CSS px width without horizontal scroll. 1.4.12 Text Spacing: copy must remain readable when user agents apply increased line-height / letter-spacing / paragraph-spacing.
- Reading order: DOM is always `image then copy` per row. Visual flip via CSS only. **Never** use `flex-direction: row-reverse` without verifying tab order matches visual order, or apply on the parent so both image and copy reverse together (no half-flip).
- Heading hierarchy: pick `heading_level` based on parent section's heading. If section has `h2`, rows are `h3`.
- Alt text per image, scoped to the row's narrative function. If image purely illustrates body copy, `alt=""` may be appropriate.
- Inline links inside body inherit standard underline + focus styling.
- AOS fade-up respects reduced motion.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | title + body |
| `$c_primary_action_*`, `$c_secondary_action_*` | CTA button states |
| `$c_support_focus` / `--dark` | focus outline |
| Grid: `dd-u-lg-12-24` 50/50 split at large viewport |
| `l-box` | inner padding on copy column |

## JS hooks
- `data-aos="fade-up"` — AOS scroll animation.

## Example params
```json
{
  "items": [
    {
      "title": "Component-driven",
      "body": "<p>Composable, named, documented.</p>",
      "image_src": "/assets/imgs/components.webp",
      "image_alt": "",
      "links": [{ "text": "Browse components", "href": "/components", "variant": "-primary" }]
    },
    {
      "title": "Cross-platform",
      "body": "<p>Static, Drupal, WordPress.</p>",
      "image_src": "/assets/imgs/platforms.webp",
      "image_alt": ""
    }
  ]
}
```

## Platform translation
**Static HTML:** Loop in build pipeline.

**Drupal Twig:**
```twig
<div class="dd-alternating" role="region"{% if aria_label %} aria-label="{{ aria_label }}"{% endif %}>
  <div class="dd-alternating__items dd-g">
    {% for item in items %}
      <div class="dd-alternating__item dd-u-1-1">
        <div class="dd-alternating__content dd-g">
          <div class="dd-alternating__image dd-u-1-1 dd-u-lg-12-24" data-aos="{{ aos|default('fade-up') }}">
            <img src="{{ item.image_src }}" class="dd-img" alt="{{ item.image_alt }}" />
          </div>
          <div class="dd-alternating__copy l-box dd-u-1-1 dd-u-lg-12-24" data-aos="{{ aos|default('fade-up') }}">
            <div class="dd-alternating__title"><h{{ item.heading_level|default(2) }}>{{ item.title }}</h{{ item.heading_level|default(2) }}></div>
            <div class="dd-alternating__body">
              {{ item.body|raw }}
              {% if item.links %}
              <div class="dd-alternating__links">
                {% for link in item.links %}
                  <div class="dd-alternating__link"><a href="{{ link.href }}" class="dd-button {{ link.variant|default('-primary') }}">{{ link.text }}</a></div>
                {% endfor %}
              </div>
              {% endif %}
            </div>
          </div>
        </div>
      </div>
    {% endfor %}
  </div>
</div>
```

**WordPress:** Mirror the Twig pattern in `render.php` using `foreach`. Escape with `esc_url`, `esc_attr`, `esc_html`, `wp_kses_post` per field.
