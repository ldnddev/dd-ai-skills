# dd-milestones

## Purpose
Statistics / achievements grid with prominent percentages or numbers, plus title, subtitle, copy, and optional link per cell.

## Context
- Wraps in `dd-section`.
- Default layout: 3-up at large viewport (`dd-u-lg-8-24`), 2-up at small/medium (`dd-u-12-24`).

## Required parameters
| name | type | description |
|---|---|---|
| `items` | array of `milestone` | One per cell. |

### `milestone` shape
| name | type | description |
|---|---|---|
| `number` | int (required) | Counter target. Animated 0 → target on scroll. |
| `title` | string (required) | Cell title (default `<h2>`). |
| `unit` | string | Optional suffix (`%`, `+`, `M`). Default `%`. |
| `subtitle` | string | Optional `<strong>` subtitle. |
| `copy` | string | Optional body line. |
| `link` | object | Optional `{ text, href, variant }`. |
| `heading_level` | int | 2–6. Default `2` may be wrong context — match parent section. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `aos` | string | `fade-up` | AOS animation. |
| `column_units` | string | `dd-u-12-24 dd-u-sm-12-24 dd-u-md-12-24 dd-u-lg-8-24` | Unit class chain per cell. |

## Variants
None at root.

## Canonical structure
```html
<div class="dd-milestones">
  <div class="dd-milestones__content">
    <div class="dd-milestones__items dd-g">
      <!-- repeat per item; default heading_level = 3 -->
      <div class="dd-milestones__item {column_units} l-box" data-aos="{aos}">
        <div class="dd-milestones__body l-box">
          <div class="dd-milestones__percentage" data-number="{number}">
            <span class="number" aria-hidden="true">0</span>{unit|default '%'}
            <span class="-scrn-reader-only">{number}{unit|default '%'}</span>
          </div>
          <div>
            <div class="dd-milestones__title"><h{heading_level|default 3}>{title}</h{heading_level|default 3}></div>
            {% if subtitle %}<div class="dd-milestones__subtitle"><strong>{subtitle}</strong></div>{% endif %}
            {% if copy %}<div class="dd-milestones__copy">{copy}</div>{% endif %}
            {% if link and link.href %}
            <div class="dd-milestones__link">
              <a href="{link.href}" class="dd-button {link.variant|default '-primary'}">{link.text}</a>
            </div>
            {% endif %}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```
**Note:** The static reference (`dd-milestones.html`) has visible `<span class="number">70</span>` regardless of `data-number`, and lacks an SR-only final value. Canonical structure above adds `aria-hidden` to the animating digit and an SR-only span with the final value.

## Accessibility
**WCAG criteria touched:** 1.3.1, 1.4.3, 2.2.2, 4.1.2.

- Animated counters: AT users should hear the FINAL value, not interim ticks. `aria-hidden="true"` on the animating span and an SR-only sibling with the static final value.
- Alternative: use `aria-live="off"` on the animating span and re-announce only on completion via JS — more complex, equivalent SR outcome.
- Counter animation must respect `prefers-reduced-motion: reduce` — skip animation, render final value immediately.
- Decorative `data-number` triggers the counter; if no JS, the SR-only span still conveys the value.
- Cell title `heading_level` chosen by context. `h2` only when section has no parent heading; usually `h3`.
- Contrast: percentage glyph qualifies for the 1.4.3 large-text 3:1 threshold ONLY when the rendered size is ≥ 18pt (24px) regular or ≥ 14pt (18.66px) bold. Below that, the 4.5:1 normal-text threshold applies. Verify computed font-size against the threshold; don't assume "large display type" qualifies.

## Design tokens
| token | usage |
|---|---|
| `$c_primary_strong` / `--dark` | percentage glyph color (emphasis) |
| `$c_text_primary` / `--dark` | title + copy |
| `$c_text_secondary` / `--dark` | subtitle |
| `$c_primary_action_*` | optional link button |
| `$c_support_focus` / `--dark` | focus outline |
| Grid: `dd-u-lg-8-24` (3-up), `dd-u-12-24` (2-up fallback) |
| `l-box` | padding |

## JS hooks
- `data-number="N"` — counter library reads target; animates from 0 to N on element entering viewport.
- `data-aos="fade-up"` — AOS scroll-in.

### Reference counter JS contract
```js
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;
    const target = parseInt(e.target.dataset.number, 10);
    const span = e.target.querySelector('.number');
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      span.textContent = target;
      return;
    }
    animateCounter(span, 0, target, 1200);
    io.unobserve(e.target);
  });
});
document.querySelectorAll('.dd-milestones__percentage').forEach(el => io.observe(el));
```

## Example params
```json
{
  "items": [
    { "number": 70, "unit": "%", "title": "Faster builds", "subtitle": "vs hand-coding", "copy": "Average across 12 sites." },
    { "number": 12, "unit": "+", "title": "CMS targets", "subtitle": "Drupal, WP, static" },
    { "number": 100, "unit": "%", "title": "WCAG AA", "subtitle": "All components" }
  ]
}
```

## Platform translation
**Static HTML:** Loop items in build pipeline. Include counter JS.

**Drupal Twig:**
```twig
<div class="dd-milestones">
  <div class="dd-milestones__content">
    <div class="dd-milestones__items dd-g">
      {% for item in items %}
        <div class="dd-milestones__item {{ column_units|default('dd-u-12-24 dd-u-lg-8-24') }} l-box" data-aos="{{ aos|default('fade-up') }}">
          <div class="dd-milestones__body l-box">
            <div class="dd-milestones__percentage" data-number="{{ item.number }}">
              <span class="number" aria-hidden="true">0</span>{{ item.unit|default('%') }}
              <span class="-scrn-reader-only">{{ item.number }}{{ item.unit|default('%') }}</span>
            </div>
            <div>
              <div class="dd-milestones__title"><h{{ item.heading_level|default(2) }}>{{ item.title }}</h{{ item.heading_level|default(2) }}></div>
              {% if item.subtitle %}<div class="dd-milestones__subtitle"><strong>{{ item.subtitle }}</strong></div>{% endif %}
              {% if item.copy %}<div class="dd-milestones__copy">{{ item.copy }}</div>{% endif %}
              {% if item.link %}<div class="dd-milestones__link"><a href="{{ item.link.href }}" class="dd-button {{ item.link.variant|default('-primary') }}">{{ item.link.text }}</a></div>{% endif %}
            </div>
          </div>
        </div>
      {% endfor %}
    </div>
  </div>
</div>
```

**WordPress:** Mirror in `render.php`. Counter JS lives in theme/plugin assets, registered globally.
