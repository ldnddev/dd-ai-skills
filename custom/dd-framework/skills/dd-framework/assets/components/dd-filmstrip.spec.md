# dd-filmstrip

## Purpose
Continuous horizontal scrolling marquee for logos, badges, or short repeated items. Conveys trust/brand list visually.

## Context
- Wraps in `dd-section`.
- Items duplicated in DOM (visible + `aria-hidden`) for seamless CSS animation loop.
- Item count: 4–8 typical. Beyond 12 the loop becomes visually busy.

## Required parameters
| name | type | description |
|---|---|---|
| `items` | array of `item` | One per logo/glyph. |

### `item` shape
| name | type | description |
|---|---|---|
| `image_src` | string (URL) (required) | Logo image. |
| `image_alt` | string (required) | Brand/logo name. `""` only if a separate label is provided via `caption` AND no semantic content lives in image. |
| `caption` | string | Optional `<figure>` caption (shown below logo). |
| `href` | string | Optional. Wraps the item in `<a>` linking to brand page. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `variant` | enum | — | `-reverse` to flip scroll direction. |
| `speed_seconds` | int | `30` | CSS animation duration. |
| `pause_on_hover` | boolean | `true` | CSS `:hover` pauses animation. |

## Variants
| modifier | effect |
|---|---|
| `-reverse` | Scroll right-to-left becomes left-to-right (or inversion of base direction). |

## Canonical structure
```html
<div class="dd-filmstrip {variant}" style="--dd-filmstrip-speed: {speed_seconds}s;">
  <ul class="dd-filmstrip__content">
    <!-- repeat per item -->
    <li>
      <figure>
        <img src="{image_src}" alt="{image_alt}" />
        {% if caption %}<figcaption>{caption}</figcaption>{% endif %}
      </figure>
    </li>
  </ul>
  <!-- duplicate for seamless loop, removed from AT and focus order via `inert` -->
  <ul class="dd-filmstrip__content" aria-hidden="true" inert>
    <li>
      <figure>
        <img src="{image_src}" alt="" />
        {% if caption %}<figcaption>{caption}</figcaption>{% endif %}
      </figure>
    </li>
  </ul>
</div>
```
**Note:** the static reference (`dd-filmstrip.html`) uses `<figure>` as the caption element. `<figure>` is the container; `<figcaption>` is the caption. Canonical structure above corrects this and uses `inert` on the duplicate list so links inside aren't focusable.

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 2.2.2 Pause, Stop, Hide, 2.3.3 Animation from Interactions.

- Auto-scrolling content that loops MUST be pausable per 2.2.2. CSS `:hover`/`:focus-within` pause helps mouse/keyboard users but does NOT serve touch users. **Provide a visible pause button whenever animation runs** (not only for >5s strips).
- Respect `prefers-reduced-motion: reduce` — set animation to `paused` or `none`.
- Duplicate `<ul>` MUST use the `inert` attribute (modern browsers) — this both hides from AT and removes from focus order in a single declaration. Fallback: `aria-hidden="true"` + `tabindex="-1"` on every interactive descendant.
- Use `<figure>` as the container and `<figcaption>` as the caption. Treating `<figure>` as a caption produces invalid semantics.
- Each visible item's `alt` describes the brand. Decorative-only filmstrips can use `alt=""` per item AND the strip itself wrapped in `role="presentation"` or hidden from AT (`aria-hidden="true"` on the whole component).
- Avoid using filmstrip for critical info (it scrolls past attention).

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | `<figure>` caption |
| `$c_support_border` / `--dark` | optional divider rule |
| `$c_support_focus` / `--dark` | focus outline if items are links |
| CSS var `--dd-filmstrip-speed` | animation duration override |

## JS hooks
- None required for core scroll.
- Optional: JS pause button toggling `animation-play-state`.

## Example params
```json
{
  "variant": "",
  "speed_seconds": 40,
  "items": [
    { "image_src": "/assets/imgs/logo-acme.svg", "image_alt": "Acme Co." },
    { "image_src": "/assets/imgs/logo-globex.svg", "image_alt": "Globex" },
    { "image_src": "/assets/imgs/logo-initech.svg", "image_alt": "Initech" }
  ]
}
```

## Platform translation
**Static HTML:** Render items list twice — visible and aria-hidden duplicate.

**Drupal Twig:**
```twig
<div class="dd-filmstrip {{ variant }}"{% if speed_seconds %} style="--dd-filmstrip-speed: {{ speed_seconds }}s;"{% endif %}>
  {% for visible in [true, false] %}
    <ul class="dd-filmstrip__content"{% if not visible %} aria-hidden="true" inert{% endif %}>
      {% for item in items %}
        <li>
          <figure>
            <img src="{{ item.image_src }}" alt="{{ visible ? item.image_alt : '' }}" />
            {% if item.caption %}<figcaption>{{ item.caption }}</figcaption>{% endif %}
          </figure>
        </li>
      {% endfor %}
    </ul>
  {% endfor %}
</div>
```

**WordPress:** Same dual-render via `foreach`. Wire reduced-motion via stylesheet (`@media (prefers-reduced-motion: reduce)`).
