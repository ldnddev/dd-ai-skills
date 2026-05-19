# dd-timeline

## Purpose
Chronological event list with image, year/date, title, and copy per item. Vertical orientation.

## Context
- Wraps in `dd-section`.
- Use for company history, project milestones, release notes, biographical timelines.
- For non-chronological steps (process, instructions), use `dd-card` or a numbered list instead — timeline implies time.

## Required parameters
| name | type | description |
|---|---|---|
| `items` | array of `event` | One per event. Order is chronological as rendered. |

### `event` shape
| name | type | description |
|---|---|---|
| `year` | string (required) | Date or year label (e.g. `"2024"`, `"Q3 2024"`, `"March 2024"`). |
| `title` | string (required) | Event title. |
| `copy` | string (HTML) (required) | Event description. |
| `image_src` | string (URL) | Optional image. |
| `image_alt` | string | Required if `image_src` set. `""` if decorative. |
| `datetime` | string | Optional machine-readable date (YYYY, YYYY-MM, YYYY-MM-DD, etc.). REQUIRED when `year` isn't itself a valid date string. |
| `heading_level` | int | 2–6. Default `3`. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `aria_label` | string | `Timeline` | Region landmark name. |
| `aos` | string | `fade-up` | AOS animation per item. |

## Variants
None at root.

## Canonical structure
```html
<div class="dd-timeline" role="region" aria-label="{aria_label}">
  <div class="dd-timeline__content">
    <ol class="dd-timeline__items dd-g">
      <!-- repeat per item; default heading_level = 3 -->
      <li class="dd-timeline__item dd-u-1-1" data-aos="{aos}">
        <div class="dd-timeline__body dd-g">
          {% if image_src %}
          <div class="dd-timeline__image l-box dd-u-1-1">
            <img src="{image_src}" alt="{image_alt}" class="dd-img" />
          </div>
          {% endif %}
          <div class="dd-timeline__text l-box dd-u-1-1">
            <div class="dd-timeline__year"><time {% if datetime %}datetime="{datetime}"{% endif %}>{year}</time></div>
            <div class="dd-timeline__title"><h{heading_level|default 3}>{title}</h{heading_level|default 3}></div>
            <div class="dd-timeline__copy">{copy}</div>
          </div>
        </div>
      </li>
    </ol>
  </div>
</div>
```
**Note:** the static reference (`dd-timeline.html`) uses a generic `<div>` for the items list and reuses `dd-timeline__copy` on both the column wrapper and the body text — class collision that breaks `.dd-timeline__copy` selectors. Canonical structure switches to `<ol>` and renames the column wrapper to `dd-timeline__text` so the inner `dd-timeline__copy` stays scoped to the body text. Existing CSS targeting `.dd-timeline__copy` on the wrapper must be updated; consumers can keep both class names during migration if needed.

**`<time>` and `datetime`:** When the `year` label is a parseable date (e.g. `"2024"`, `"2024-03"`, `"2024-03-15"`), the `<time>` element alone satisfies HTML5. When the label is a non-machine-readable string (`"Q3 2024"`, `"Late spring"`), the `datetime` attribute is REQUIRED and must hold a valid date string (e.g. `datetime="2024-07-01"` for "Q3 2024").

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 1.4.3, 2.4.6, 2.4.7.

- Timeline data is inherently ordered — use `<ol>` not `<ul>` or `<div>`. AT users hear "list, N items".
- `<time>` element MUST contain either a valid date string OR carry a `datetime` attribute with one. "Q3 2024" is not a valid date, so it requires `datetime="2024-07-01"` (or similar). Otherwise the markup is invalid HTML5 and AT date semantics break.
- `role="region"` + `aria-label="Timeline"` makes the timeline a navigable landmark.
- Event title heading level: match parent section's outline. Typically `h3`.
- Decorative item images use `alt=""`. Meaningful images (e.g., product screenshots tied to release) use descriptive alt.
- Reading order: DOM is year → title → copy → image (or image → year → title → copy as in reference). Pick one and apply consistently. SR will follow DOM order.
- AOS fade-up respects reduced motion.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | title + copy |
| `$c_text_secondary` / `--dark` | year |
| `$c_primary_strong` / `--dark` | year/timeline marker color (emphasis) |
| `$c_support_border` / `--dark` | timeline vertical rule between items |
| Grid: `dd-u-1-1` full-width items |
| `l-box` | inner padding on image + copy columns |

## JS hooks
- `data-aos="fade-up"` — AOS scroll animation per item.

## Example params
```json
{
  "items": [
    {
      "year": "2022",
      "title": "Framework v1 released",
      "copy": "<p>Initial set of 12 components.</p>",
      "image_src": "/assets/imgs/v1.webp",
      "image_alt": ""
    },
    {
      "year": "2024",
      "title": "Cross-platform spec",
      "copy": "<p>Drupal + WordPress + static.</p>"
    },
    {
      "year": "Q2 2026",
      "title": "AI-skill integration",
      "copy": "<p>dd-framework available via Claude/Codex skills.</p>"
    }
  ]
}
```

## Platform translation
**Static HTML:** Loop items in build pipeline.

**Drupal Twig:**
```twig
<div class="dd-timeline" role="region" aria-label="{{ aria_label|default('Timeline') }}">
  <div class="dd-timeline__content">
    <ol class="dd-timeline__items dd-g">
      {% for item in items %}
        <li class="dd-timeline__item dd-u-1-1" data-aos="{{ aos|default('fade-up') }}">
          <div class="dd-timeline__body dd-g">
            {% if item.image_src %}
              <div class="dd-timeline__image l-box dd-u-1-1">
                <img src="{{ item.image_src }}" alt="{{ item.image_alt|default('') }}" class="dd-img" />
              </div>
            {% endif %}
            <div class="dd-timeline__copy l-box dd-u-1-1">
              <div class="dd-timeline__year"><time>{{ item.year }}</time></div>
              <div class="dd-timeline__title"><h{{ item.heading_level|default(3) }}>{{ item.title }}</h{{ item.heading_level|default(3) }}></div>
              <div class="dd-timeline__copy">{{ item.copy|raw }}</div>
            </div>
          </div>
        </li>
      {% endfor %}
    </ol>
  </div>
</div>
```

**WordPress:** Mirror via `foreach` in `render.php`. Use ACF Repeater for editor-friendly content authoring.
