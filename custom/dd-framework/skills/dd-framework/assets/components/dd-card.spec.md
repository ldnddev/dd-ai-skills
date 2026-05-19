# dd-card

## Purpose
Card grid for grouped content (articles, products, team, services). Each card carries an image, title, optional subtitle/copy, and zero-or-more CTA links.

## Context
- Wraps in `dd-section`. Cards live inside `dd-section__item` columns or alongside other components.
- Default layout: cards flow horizontally, each `dd-u-md-12-24` (50%) on tablet+. Override via column unit classes on `dd-card__item`.
- `-horizontal` variant: image-left, copy-right per card (full-width items).

## Required parameters
| name | type | description |
|---|---|---|
| `items` | array of `card` | One per card. See `card` shape below. |

### `card` shape
| name | type | description |
|---|---|---|
| `title` | string (required) | Card title. Rendered as `<h3>` by default; promote to `<h2>` if cards are sole section content. |
| `image_src` | string (URL) (required) | Card image. |
| `image_alt` | string (required) | Alt text. `""` only if decorative. |
| `subtitle` | string | Optional. Rendered inside `<strong>`. |
| `copy` | string (HTML) | Optional body. |
| `links` | array of `{text, href, target, variant}` | Optional. `variant` ∈ `-primary -ghost -secondary`. |
| `image_width` | int | Optional. Native pixel width for `width` attr (prevents CLS). |
| `image_height` | int | Optional. Native pixel height. |
| `column_units` | string | Optional class override, e.g. `dd-u-md-8-24` for 3-column grid. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `variant` | enum | — | `-horizontal` for image-left rows. |
| `aos` | string | `fade-up` | AOS animation per card. |
| `heading_level` | int | `3` | Override card heading level (2–6). |

## Variants
| modifier | effect |
|---|---|
| `-horizontal` | Cards flow as image-left rows, full width per card. Best for 1-up or 2-up stacked. |

## Canonical structure
```html
<div class="dd-card {variant}">
  <div class="dd-card__items dd-g">
    <!-- repeat per item; default heading_level = 3 -->
    <div class="dd-card__item l-box dd-u-1-1 {column_units}" data-aos="{aos}">
      <div class="dd-card__body dd-g">
        <div class="dd-card__image">
          <img src="{image_src}" alt="{image_alt}" class="dd-image"
               {% if image_width %}width="{image_width}" height="{image_height}"{% endif %}
               loading="lazy">
        </div>
        <div class="dd-card__copy l-box">
          <div class="dd-card__title"><h{heading_level|default 3}>{title}</h{heading_level|default 3}></div>
          {% if subtitle %}<div class="dd-card__sub-title"><strong>{subtitle}</strong></div>{% endif %}
          {% if copy %}{copy}{% endif %}
          {% if links %}
          <div class="dd-card__links dd-g">
            {% for link in links %}{% if link.href %}
            <div class="dd-card__link">
              <a href="{link.href}" {% if link.target %}target="{link.target}"{% endif %} class="dd-button {link.variant|default '-primary'}">{link.text}</a>
            </div>
            {% endif %}{% endfor %}
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
```
See `dd-card.html` for static reference output.

**Gating:** Omit `<strong>`, link list, and image width/height attrs when their values are absent. Empty conditional elements (`<strong></strong>`, `<a href=""></a>`) get announced by SR and can navigate to the current page on click — never emit them.

**Copy handling:** `{copy}` may contain block HTML (`<p>`, `<ul>`). Render it directly, not wrapped in `<p>`. Nested `<p>` is auto-closed by the parser and breaks AT structure. If your data model guarantees plain inline text, wrap it; otherwise pass through.

**Class note:** The static reference uses `class="dd-image"` on card images (not `dd-img` like other components). This is pre-existing CSS — keep as-is for compatibility; do not rename without coordinating a CSS update.

**LCP:** Drop `loading="lazy"` on the first row of cards if cards live above the fold — lazy-loading the LCP image hurts performance (this is a perf concern, not a WCAG criterion).

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 1.4.3, 1.4.11, 2.4.4 Link Purpose (In Context), 2.4.6, 2.4.7, 2.5.8 Target Size (Minimum), 4.1.2 Name Role Value.

- Card titles use a single heading level across the grid. Determine level by parent context — typically `h3` inside a section with an `h2` section heading.
- `image_alt` MUST describe meaningful images. Decorative card images (e.g. abstract patterns) use `alt=""`.
- Provide explicit `width`/`height` whenever image natural dimensions are known — prevents reflow on load. `loading="lazy"` for below-the-fold cards only.
- Card link text must be self-descriptive when read in isolation by screen reader rotor. Avoid "Read more" / "Click here". Use "Read more about {card title}" or apply `aria-label` carrying the title.
- 2.5.8: card CTA buttons must meet 24×24 CSS px minimum target size (or exclude per the exception list).
- If the entire card is clickable (link wraps body): only one focusable interactive descendant allowed. Either wrap whole card in `<a>` and remove inner link buttons, or keep buttons and don't wrap.
- `-horizontal` variant: reading order DOM (image then copy) matches visual order. No CSS reordering that breaks tab sequence.
- AOS `fade-up` honors `prefers-reduced-motion`.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | title, copy |
| `$c_text_secondary` / `--dark` | subtitle |
| `$c_primary_action_*` | `-primary` button states |
| `$c_secondary_action_*` | `-secondary` button states |
| `$c_support_border` / `--dark` | card border / divider |
| `$c_support_focus` / `--dark` | focus outline on links |
| Grid: `dd-g`, `dd-u-1-1`, `dd-u-md-12-24` (2-up), `dd-u-md-8-24` (3-up), `dd-u-md-6-24` (4-up) |
| `l-box` | inner padding for `__item` and `__copy` |

## JS hooks
- `data-aos` — AOS scroll animation.
- No custom JS required.

## Example params
```json
{
  "variant": "",
  "items": [
    {
      "title": "Static HTML sites",
      "image_src": "/assets/imgs/static.webp",
      "image_alt": "",
      "image_width": 768,
      "image_height": 287,
      "subtitle": "Zero build",
      "copy": "Copy-paste components into any HTML page.",
      "links": [{ "text": "See examples", "href": "/static", "target": "_self", "variant": "-primary" }]
    },
    {
      "title": "Drupal sites",
      "image_src": "/assets/imgs/drupal.webp",
      "image_alt": "",
      "image_width": 768,
      "image_height": 287,
      "subtitle": "Twig templates",
      "copy": "Drop into theme as components.",
      "links": [{ "text": "See examples", "href": "/drupal", "target": "_self", "variant": "-primary" }]
    }
  ]
}
```

## Platform translation
**Static HTML:** Loop `items` array in your build pipeline (Eleventy, Astro, etc.) emitting the canonical structure per card.

**Drupal Twig (`dd-card.html.twig`):**
```twig
<div class="dd-card{% if variant %} {{ variant }}{% endif %}">
  <div class="dd-card__items dd-g">
    {% for item in items %}
      <div class="dd-card__item l-box dd-u-1-1 {{ item.column_units|default('dd-u-md-12-24') }}" data-aos="{{ aos|default('fade-up') }}">
        <div class="dd-card__body dd-g">
          <div class="dd-card__image">
            <img src="{{ item.image_src }}" alt="{{ item.image_alt }}" class="dd-image"
                 {% if item.image_width %}width="{{ item.image_width }}" height="{{ item.image_height }}"{% endif %} loading="lazy">
          </div>
          <div class="dd-card__copy l-box">
            <div class="dd-card__title"><h{{ heading_level|default(3) }}>{{ item.title }}</h{{ heading_level|default(3) }}></div>
            {% if item.subtitle %}<div class="dd-card__sub-title"><strong>{{ item.subtitle }}</strong></div>{% endif %}
            {% if item.copy %}<p>{{ item.copy|raw }}</p>{% endif %}
            {% if item.links %}
            <div class="dd-card__links dd-g">
              {% for link in item.links %}
                <div class="dd-card__link"><a href="{{ link.href }}" target="{{ link.target|default('_self') }}" class="dd-button {{ link.variant|default('-primary') }}">{{ link.text }}</a></div>
              {% endfor %}
            </div>
            {% endif %}
          </div>
        </div>
      </div>
    {% endfor %}
  </div>
</div>
```

**WordPress (ACF Flexible Content or block render.php):**
```php
<?php $items = $attributes['items'] ?? []; ?>
<div class="dd-card<?php echo ! empty( $attributes['variant'] ) ? ' ' . esc_attr( $attributes['variant'] ) : ''; ?>">
  <div class="dd-card__items dd-g">
    <?php foreach ( $items as $item ) : ?>
      <div class="dd-card__item l-box dd-u-1-1 <?php echo esc_attr( $item['column_units'] ?? 'dd-u-md-12-24' ); ?>" data-aos="fade-up">
        <div class="dd-card__body dd-g">
          <div class="dd-card__image">
            <img src="<?php echo esc_url( $item['image_src'] ); ?>" alt="<?php echo esc_attr( $item['image_alt'] ); ?>" class="dd-image" loading="lazy">
          </div>
          <div class="dd-card__copy l-box">
            <div class="dd-card__title"><h3><?php echo esc_html( $item['title'] ); ?></h3></div>
            <?php if ( ! empty( $item['copy'] ) ) : ?><p><?php echo wp_kses_post( $item['copy'] ); ?></p><?php endif; ?>
          </div>
        </div>
      </div>
    <?php endforeach; ?>
  </div>
</div>
```
