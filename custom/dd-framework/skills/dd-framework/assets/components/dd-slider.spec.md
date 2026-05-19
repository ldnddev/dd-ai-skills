# dd-slider

## Purpose
Carousel of slide items with prev/next buttons and tab indicators. Each slide carries an image plus title/copy/links.

## Context
- Wraps in `dd-section`.
- Carousels are accessibility-fragile. Prefer static grids (`dd-card`) unless a sliding interaction is essential.

## Required parameters
| name | type | description |
|---|---|---|
| `title` | string | Slider heading (default `<h2>`). |
| `slides` | array of `slide` | One per slide. Minimum 2; with 1 slide, render as a static block instead. |

### `slide` shape
| name | type | description |
|---|---|---|
| `id` | string (required) | Unique slide id. |
| `title` | string (required) | Slide title. |
| `copy` | string (HTML) (required) | Body. |
| `image_src` | string (URL) (required) | Slide image. |
| `image_alt` | string (required) | Alt text. `""` if purely decorative AND title/copy carry meaning. |
| `links` | array of `{text, href, variant}` | Optional CTAs. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `heading_level` | int | `2` | Slider title heading level. |
| `autoplay` | boolean | `false` | Auto-advance slides. **Strongly recommend `false`** for accessibility. |
| `autoplay_interval_ms` | int | `5000` | Auto-advance interval. |
| `aria_label` | string | `"{title} carousel"` | Region landmark label. |

## Variants
None at root.

## Canonical structure
```html
<div id="{id}" class="dd-slider" role="region" aria-roledescription="carousel" aria-label="{aria_label}">
  <div class="dd-slider__heading"><h{heading_level}>{title}</h{heading_level}></div>
  <!-- Live region for slide-position announcements only. NOT the slide container itself. -->
  <div class="-scrn-reader-only" aria-live="polite" id="{id}-status"></div>
  <ul class="dd-slider__items -nostyle">
    <!-- repeat per slide -->
    <li class="dd-slider__item"
        role="group"
        aria-roledescription="slide"
        aria-label="{slide_index} of {slide_total}: {slide.title}"
        id="{id}-slide-{slide_index}">
      <div class="dd-slider__content">
        <div class="dd-g">
          <div class="dd-slider__body dd-u-1-1 dd-u-lg-12-24 l-box">
            <div class="dd-slider__item-title">{slide.title}</div>
            <div class="dd-slider__copy">
              {slide.copy}
              <div class="dd-slider__links">
                <div class="dd-slider__link">
                  <a href="{slide.links[].href}" class="dd-button {slide.links[].variant}">{slide.links[].text}</a>
                </div>
              </div>
            </div>
          </div>
          <div class="dd-slider__image dd-u-1-1 dd-u-lg-12-24">
            <img src="{slide.image_src}" alt="{slide.image_alt}" />
          </div>
        </div>
      </div>
    </li>
  </ul>
  <div class="dd-slider__navigation">
    <button type="button" id="{id}-prev" aria-label="Previous slide"><span aria-hidden="true">&lt;</span></button>
    <ul class="dd-slider__indicators -nostyle">
      <!-- one per slide; plain buttons with aria-current="true" on active -->
      <li>
        <button type="button"
                aria-label="Go to slide {slide_index}"
                aria-current="{slide.active ? 'true' : 'false'}"
                aria-controls="{id}-slide-{slide_index}">
          <span aria-hidden="true">●</span>
        </button>
      </li>
    </ul>
    <button type="button" id="{id}-next" aria-label="Next slide"><span aria-hidden="true">&gt;</span></button>
  </div>
  {% if autoplay %}
  <button type="button" id="{id}-pause" aria-label="Pause carousel">Pause</button>
  {% endif %}
</div>
```
**Note:** the static reference (`dd-slider.html`) has malformed attributes (`data-id="uid_0001` missing closing quote), repeats `dd-slider__title` inside slides, mixes `role="tablist"`/`role="tab"` with the carousel pattern (APG forbids), uses `aria-live` on the slides container (announces all slide content on advance — very noisy), and uses `<button>` without `type` and without `aria-label`. Canonical structure above is the accessible target: pure carousel pattern with plain indicator buttons (no tablist roles), instance-scoped nav button IDs, and a small SR-only live region used ONLY for position announcements ("Slide 3 of 5: Globex").

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 2.1.1, 2.2.2, 2.4.3, 2.4.4, 2.4.7, 4.1.2.

- Use **one** APG pattern. dd-slider implements the **carousel** pattern. Per-slide `role="group"` + `aria-roledescription="slide"`. Indicator buttons are plain `<button>` with `aria-current="true"` on the active one — they are NOT `role="tab"`. Mixing tabs roles into a carousel is internally inconsistent and AT behaves unpredictably.
- `role="region"` + `aria-roledescription="carousel"` + accessible name from `aria-label`.
- **Live region is separate from the slide container.** Slide changes update the SR-only `{id}-status` div with text like `"Slide 3 of 5: Globex"` — JS writes that string on advance. NEVER put `aria-live` on the `<ul class="dd-slider__items">` directly: that announces all of every slide on advance, which is noise.
- Nav buttons MUST be `<button type="button">` with non-empty `aria-label`. Visible `<` `>` `●` glyphs are decorative — `aria-hidden="true"`.
- IDs MUST be scoped to the slider instance: `{id}-prev`, `{id}-next`, `{id}-pause`, `{id}-status`, `{id}-slide-N`. Multiple sliders on a page break otherwise.
- **Autoplay MUST default to off.** If enabled, MUST provide a visible pause button (2.2.2), pause on focus and hover, and stop auto-advance permanently on first user interaction (click, key press, indicator activation).
- Keyboard: Left/Right arrow keys move between slides (when slider region focused). Tab moves through interactive elements within the visible slide. Don't trap focus inside the slider.
- Respect `prefers-reduced-motion: reduce` — disable transition animations AND autoplay entirely.
- Image `alt`: real description, or empty if the slide's title/copy carries the meaning.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | slide title + copy |
| `$c_primary_action_*` | nav button + tab button states |
| `$c_secondary_action_*` | ghost link variant |
| `$c_support_focus` / `--dark` | focus outline |
| `$c_support_border` / `--dark` | tab indicator inactive state |
| Grid: `dd-u-lg-12-24` 50/50 split |
| `l-box` | inner padding on body |

## JS hooks
- Instance-scoped IDs `{id}-prev`, `{id}-next`, `{id}-pause` — bind a click handler that changes the active slide and writes `"Slide X of N: {title}"` into `{id}-status`.
- Indicator buttons (`aria-controls="{id}-slide-N"`) — click activates that slide and updates `aria-current` on all indicators.
- Slider library MUST manage `aria-current`, focus retention, arrow-key navigation, and `prefers-reduced-motion`.
- On first user interaction with the slider (any click or keypress), permanently stop autoplay.

## Example params
```json
{
  "title": "Customer stories",
  "slides": [
    {
      "id": "slide-1",
      "title": "Acme Co.",
      "copy": "<p>Cut page build time by 60%.</p>",
      "image_src": "/assets/imgs/acme.webp",
      "image_alt": "",
      "links": [{ "text": "Read case study", "href": "/case/acme", "variant": "-primary" }]
    },
    {
      "id": "slide-2",
      "title": "Globex",
      "copy": "<p>Shipped 4 microsites in a quarter.</p>",
      "image_src": "/assets/imgs/globex.webp",
      "image_alt": ""
    }
  ]
}
```

## Platform translation
**Static HTML:** Pair with your slider JS library (e.g., Splide, Embla) configured for accessibility.

**Drupal Twig:** Loop `slides` in template; attach a library that pulls in carousel JS + arrow-key handler. Validate against APG carousel pattern in audit.

**WordPress:** Register block with `InnerBlocks` per slide OR use ACF Repeater. Enqueue an accessible carousel library in `theme.js`.
