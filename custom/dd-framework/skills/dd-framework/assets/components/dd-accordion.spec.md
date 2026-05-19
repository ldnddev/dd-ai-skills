# dd-accordion

## Purpose
Stack of collapsible panels using native `<details>`/`<summary>` — no JS required for core behavior.

## Context
- Wraps in `dd-section`.
- Native `<details>` provides keyboard/AT support out-of-box. Avoid replacing with custom `<button aria-expanded>` widget unless adding cross-panel coordination beyond what `name=""` supplies.

## Required parameters
| name | type | description |
|---|---|---|
| `items` | array of `panel` | One per panel. |

### `panel` shape
| name | type | description |
|---|---|---|
| `title` | string (required) | Summary text. |
| `content` | string (HTML) (required) | Panel body content. |
| `open` | boolean | Optional. Default closed. |
| `id` | string | Optional. For deep-linking via URL hash. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `group_name` | string | `group1` | `<details name>` attribute. When set, browser auto-closes siblings on open (exclusive mode). Omit string to allow multiple-open. |
| `heading_level` | int | — | If set, wraps `<summary>` text in `h{n}`. Use only when accordion functions as a structural outline. |

## Variants
None at root.

## Canonical structure
```html
<div class="dd-accordion">
  <div class="dd-accordion__items">
    <!-- repeat per item -->
    <details name="{group_name}" class="dd-accordion__item" {% if open %}open{% endif %} id="{id}">
      <summary class="dd-accordion__header dd-g -y-center">
        <div class="dd-accordion__title dd-u-1-1">{title}</div>
      </summary>
      <div class="dd-accordion__copy">{content}</div>
    </details>
  </div>
</div>
```
See `dd-accordion.html`.

## Accessibility
**WCAG criteria touched:** 1.3.1, 1.4.13 Content on Hover or Focus, 2.1.1 Keyboard, 2.4.3 Focus Order, 2.4.6, 2.4.7, 2.5.8 Target Size (Minimum), 4.1.2.

- Native `<details>`/`<summary>` is keyboard-accessible by default (Enter/Space toggles). Do not add `tabindex` or `role` attributes that override native semantics.
- `<summary>` is the click target. Ensure it meets 2.5.8 (24×24 CSS px minimum). Pad the summary, don't shrink it.
- `<summary>` is implicitly a button to AT — do not nest interactive elements inside it.
- If summary text needs to look like a heading visually, wrap in `<h2>`/`<h3>` etc. INSIDE `<summary>` rather than changing `<summary>` role.
- `name="group1"` on `<details>` causes exclusive (one-open) behavior in supporting browsers. Older Safari may show all open — graceful degrade, not blocking.
- Animated height changes must respect `prefers-reduced-motion: reduce`.
- Focus visible: 2px outline on `<summary>` focus.
- Avoid auto-collapsing on outside click. Native behavior is sufficient.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | title + body text |
| `$c_support_border` / `--dark` | divider between items |
| `$c_support_focus` / `--dark` | summary focus outline |
| `$c_primary_subtle` / `--dark` | open panel surface (optional) |
| Grid: `dd-g`, `-y-center`, `dd-u-1-1` |

## JS hooks
- None required.
- Deep-link via URL hash: optionally add a small JS to set `open` on `<details>` matching `location.hash`.

## Example params
```json
{
  "group_name": "faq",
  "items": [
    { "title": "What is dd-framework?", "content": "<p>Component-first design system.</p>" },
    { "title": "Does it work on Drupal?", "content": "<p>Yes — Twig templates provided.</p>", "open": true }
  ]
}
```

## Platform translation
**Static HTML:** Loop in build step. Set `open` attribute presence.

**Drupal Twig:**
```twig
<div class="dd-accordion">
  <div class="dd-accordion__items">
    {% for item in items %}
      <details name="{{ group_name|default('group1') }}" class="dd-accordion__item"{% if item.open %} open{% endif %}{% if item.id %} id="{{ item.id }}"{% endif %}>
        <summary class="dd-accordion__header dd-g -y-center">
          <div class="dd-accordion__title dd-u-1-1">{{ item.title }}</div>
        </summary>
        <div class="dd-accordion__copy">{{ item.content|raw }}</div>
      </details>
    {% endfor %}
  </div>
</div>
```

**WordPress (block render.php):**
```php
<?php $items = $attributes['items'] ?? []; $group = esc_attr( $attributes['group_name'] ?? 'group1' ); ?>
<div class="dd-accordion">
  <div class="dd-accordion__items">
    <?php foreach ( $items as $item ) : ?>
      <details name="<?php echo $group; ?>" class="dd-accordion__item"<?php echo ! empty( $item['open'] ) ? ' open' : ''; ?>>
        <summary class="dd-accordion__header dd-g -y-center">
          <div class="dd-accordion__title dd-u-1-1"><?php echo esc_html( $item['title'] ); ?></div>
        </summary>
        <div class="dd-accordion__copy"><?php echo wp_kses_post( $item['content'] ); ?></div>
      </details>
    <?php endforeach; ?>
  </div>
</div>
```
