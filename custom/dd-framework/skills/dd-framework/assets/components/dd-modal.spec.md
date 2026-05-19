# dd-modal

## Purpose
Native `<dialog>` modal for confirmations, forms, or content overlays. Trigger button + close control.

## Context
- **Standalone.** Modal trigger lives wherever needed; `<dialog>` itself typically renders late in the body to avoid stacking context issues.
- Uses HTML5 `<dialog>` element — native focus trap, backdrop, ESC-to-close come free in modern browsers.
- Multiple modals per page OK; each needs unique `id`.

## Required parameters
| name | type | description |
|---|---|---|
| `id` | string | Unique element id linking trigger to dialog. |
| `content` | string (HTML) | Modal body. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `title` | string | — | Title rendered as `<h2>` at top of modal. Strongly recommended. |
| `trigger_text` | string | `Open Modal` | Trigger button label. |
| `trigger_class` | string | (empty) | Trigger button class. Common: `dd-button -primary`. |
| `close_label` | string | `Close modal window` | `aria-label` on close button. |
| `close_text` | string | `×` | Close button visible text (use multiplication sign U+00D7, not letter x). |
| `render_trigger` | boolean | `true` | If false, only the `<dialog>` is rendered. Wire your own trigger. |

## Variants
None at root.

## Canonical structure
```html
{% if render_trigger %}
<button type="button" class="{trigger_class}" data-modal-open data-id="{id}" aria-haspopup="dialog">{trigger_text}</button>
{% endif %}
<dialog data-modal id="{id}" class="dd-modal" {% if title %}aria-labelledby="{id}-title"{% endif %}>
  <button type="button" data-modal-close data-id="{id}" aria-label="{close_label}">
    <span aria-hidden="true">{close_text}</span>
  </button>
  <div class="dd-modal__content">
    {% if title %}<h2 id="{id}-title">{title}</h2>{% endif %}
    {content}
  </div>
</dialog>
```
**Note:** the static reference (`dd-modal.html`) lacks `aria-labelledby`, `aria-haspopup`, and explicit `type="button"`. Canonical structure above is the accessible target.

**Autofocus target:** Native `<dialog>` autofocus moves to the first focusable descendant on `.showModal()`. In the canonical above that's the close button. For modals containing a form, mark the first form field with the `autofocus` attribute so it receives focus instead — fields are typically the user's intent target, not the close button.

**Click-outside dismiss:** Optional. If implemented, the close button AND `Esc` MUST remain functional — never make click-outside the only dismiss path (keyboard-only users cannot trigger it).

## Accessibility
**WCAG criteria touched:** 1.3.1, 2.1.1, 2.1.2 No Keyboard Trap, 2.4.3, 2.4.7, 2.4.11, 4.1.2.

- Open via `dialog.showModal()` — provides native modal semantics, focus trap, inert background, and `Esc` key handling. Avoid `dialog.show()` (non-modal) unless intentionally non-blocking.
- `aria-labelledby` points to the modal title `<h2>`. Required for screen reader to announce dialog name.
- Trigger button: `type="button"` (prevents form submit). `aria-haspopup="dialog"` advertises behavior.
- Close button: `aria-label` carries semantic ("Close modal window") — visible `×` glyph is decorative. Use `×` (U+00D7), not letter `x`.
- Focus management: opening — move focus to first focusable element OR the close button; closing — return focus to the trigger element. `<dialog>` does this natively in supporting browsers.
- ESC dismisses by default (HTML5 dialog spec). Do NOT prevent default unless modal contains unsaved work warranting confirmation — in which case, intercept and show a sub-confirmation.
- Backdrop click dismiss: NOT free with `<dialog>`. Add JS if needed: `dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); })`.
- Tab cycles within dialog automatically (`<dialog>` is inert outside).
- 2.4.11 Focus not obscured: ensure focused descendants remain visible (modal scrolls if content tall).

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | modal copy + close glyph |
| `$c_support_overlay` / `--dark` | `::backdrop` color |
| `$c_support_border` / `--dark` | modal border |
| `$c_support_focus` / `--dark` | focus outline on close + trigger |
| `$c_primary_action_*` | trigger button states |

## JS hooks
- `data-modal-open` + `data-id` — handler calls `document.getElementById(id).showModal()`.
- `data-modal-close` + `data-id` — handler calls `document.getElementById(id).close()`.

### Reference JS contract
```js
document.querySelectorAll('[data-modal-open]').forEach(btn => {
  btn.addEventListener('click', () => document.getElementById(btn.dataset.id).showModal());
});
document.querySelectorAll('[data-modal-close]').forEach(btn => {
  btn.addEventListener('click', () => document.getElementById(btn.dataset.id).close());
});
// Optional: click-outside dismiss
document.querySelectorAll('dialog[data-modal]').forEach(d => {
  d.addEventListener('click', e => { if (e.target === d) d.close(); });
});
```

## Example params
```json
{
  "id": "newsletter-modal",
  "title": "Subscribe to updates",
  "trigger_text": "Subscribe",
  "trigger_class": "dd-button -primary",
  "content": "<form>... newsletter form ...</form>"
}
```

## Platform translation
**Static HTML:** Substitute directly. Include reference JS once.

**Drupal Twig:**
```twig
{% if render_trigger is not defined or render_trigger %}
<button type="button" class="{{ trigger_class }}" data-modal-open data-id="{{ id }}" aria-haspopup="dialog">{{ trigger_text|default('Open') }}</button>
{% endif %}
<dialog data-modal id="{{ id }}" class="dd-modal"{% if title %} aria-labelledby="{{ id }}-title"{% endif %}>
  <button type="button" data-modal-close data-id="{{ id }}" aria-label="{{ close_label|default('Close modal window') }}">
    <span aria-hidden="true">×</span>
  </button>
  <div class="dd-modal__content">
    {% if title %}<h2 id="{{ id }}-title">{{ title }}</h2>{% endif %}
    {{ content|raw }}
  </div>
</dialog>
```

**WordPress:** Mirror in `render.php`. JS lives in theme/plugin asset, enqueued site-wide.
