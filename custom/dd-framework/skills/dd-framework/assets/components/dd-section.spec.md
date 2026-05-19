# dd-section

## Purpose
Layout wrapper providing consistent vertical spacing, width constraint, and column grid for child components.

## Context
- Wraps most other dd-* components. Exceptions: `dd-hero`, `dd-cta`, `dd-banner`, `dd-modal`, `dd-cookie-consent` render standalone edge-to-edge.
- One `<section>` per logical content area. Sections nest only if outer is `-full-bleed` and inner needs constrained width.

## Required parameters
| name | type | description |
|---|---|---|
| `content` | string (HTML) | Child components / content. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `id` | string | — | Anchor id for skip-links or in-page navigation. |
| `aria_label` | string | — | Landmark name. Provide when multiple `<section>` landmarks exist on the page. Mutually exclusive with `title_id`. |
| `title_id` | string | — | Id assigned to the section's heading. When set, the section automatically receives `aria-labelledby="{title_id}"`. Preferred over `aria_label` when a visible heading exists. |
| `title` | string | — | Section heading rendered as `<h2>` inside `dd-section__title`. Set together with `title_id` to link landmark naming to the visible heading. |
| `heading_level` | int | `2` | Override heading level (2–6). |
| `variant` | enum | — | See Variants. |
| `column_layout` | enum | `single` | `single` (one column), `2-up`, `3-up`, `4-up`. Maps to `dd-u-lg-12-24`, `8-24`, `6-24`. |
| `items` | array | — | If component holds multiple child blocks, render each in its own `dd-section__item`. |

## Variants
| modifier | effect |
|---|---|
| `-full-contained` | Standard contained max-width (default behavior; explicit). |
| `-full-bleed` | Removes max-width — content spans full viewport. |
| `-narrow` | Tighter max-width (reading column ~70ch). |

## Canonical structure
```html
<section class="dd-section {variant}"
         {% if id %}id="{id}"{% endif %}
         {% if title_id %}aria-labelledby="{title_id}"{% elseif aria_label %}aria-label="{aria_label}"{% endif %}>
  <div class="dd-section__content">
    {% if title %}
    <div class="dd-section__title l-box">
      <h{heading_level} {% if title_id %}id="{title_id}"{% endif %}>{title}</h{heading_level}>
    </div>
    {% endif %}
    <div class="dd-section__items dd-g">
      <!-- single content block -->
      <div class="dd-section__item dd-u-1-1 {column_class} l-box">
        {content}
      </div>
      <!-- or repeated items -->
      <div class="dd-section__item dd-u-1-1 {column_class} l-box">
        {items[i]}
      </div>
    </div>
  </div>
</section>
```
See `dd-section.html` for `-full-contained` 3-up example.

**Naming priority:** `title_id` (preferred — points at visible heading) > `aria_label` (when no visible heading) > none (results in a generic container, not a landmark).

## Accessibility
**WCAG criteria touched:** 1.3.1, 2.4.1 Bypass Blocks, 2.4.6, 2.4.10 Section Headings, 4.1.2 Name Role Value.

- `<section>` becomes a landmark when it has an accessible name. Without `title_id` / `aria_label`, it's a generic container — no AT landmark. Provide one of:
  - `title_id` + visible heading (PREFERRED — landmark name matches visible name; the helper auto-generates `aria-labelledby`).
  - `aria_label` with a concise label, used only when no visible heading exists.
- Avoid manually authoring `aria-labelledby` — set `title_id` and let the canonical structure wire both ends. This prevents the common bug where `aria-labelledby` references an id that doesn't exist on any element.
- Heading hierarchy: `dd-section__title` heading level chosen by document outline. Sections containing hero (`h1`) typically use `h2`; nested sections use `h3`.
- Avoid `<div class="dd-section">` — keep semantic `<section>` element.
- Provide unique `id` to support skip-link targets. `id` and `title_id` are distinct: `id` is the section anchor, `title_id` is the heading anchor.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | section title + content text |
| `$c_support_border` / `--dark` | optional top/bottom rule for visual separation |
| Spacing tokens (vertical padding) come from `.dd-section` CSS rules |
| Grid: `dd-g`, `dd-u-lg-12-24` (2-up), `dd-u-lg-8-24` (3-up), `dd-u-lg-6-24` (4-up) |
| `l-box` | inner padding on `__item` and `__title` |

## JS hooks
- None required.

## Example params
```json
{
  "variant": "-full-contained",
  "title": "Why dd-framework",
  "title_id": "why-section-title",
  "column_layout": "3-up",
  "items": [
    "<!-- card 1 -->",
    "<!-- card 2 -->",
    "<!-- card 3 -->"
  ]
}
```

## Platform translation
**Static HTML:** Direct substitution.

**Drupal Twig:**
```twig
<section class="dd-section{% if variant %} {{ variant }}{% endif %}"
         {% if id %}id="{{ id }}"{% endif %}
         {% if title_id %}aria-labelledby="{{ title_id }}"{% elseif aria_label %}aria-label="{{ aria_label }}"{% endif %}>
  <div class="dd-section__content">
    {% if title %}
      <div class="dd-section__title l-box">
        <h{{ heading_level|default(2) }}{% if title_id %} id="{{ title_id }}"{% endif %}>{{ title }}</h{{ heading_level|default(2) }}>
      </div>
    {% endif %}
    <div class="dd-section__items dd-g">
      {% set col = {'single':'', '2-up':'dd-u-lg-12-24', '3-up':'dd-u-lg-8-24', '4-up':'dd-u-lg-6-24'}[column_layout|default('single')] %}
      {% if items %}
        {% for item in items %}
          <div class="dd-section__item dd-u-1-1 {{ col }} l-box">{{ item|raw }}</div>
        {% endfor %}
      {% else %}
        <div class="dd-section__item dd-u-1-1 {{ col }} l-box">{{ content|raw }}</div>
      {% endif %}
    </div>
  </div>
</section>
```

**WordPress:** Use `InnerBlocks` for Gutenberg block authoring; render via `<?php echo $content; ?>` (InnerBlocks rendered children) inside the section wrapper.
