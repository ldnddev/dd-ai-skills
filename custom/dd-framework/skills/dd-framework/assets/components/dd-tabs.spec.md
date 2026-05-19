# dd-tabs

## Purpose
Tabbed content interface using ARIA `tablist` / `tab` / `tabpanel` roles. Switches between related content panels.

## Context
- Wraps in `dd-section`.
- Use tabs when content is parallel and only one panel is relevant at a time. If users need to compare panels, use side-by-side cards instead.
- 2–7 tabs typical. Beyond 7, consider an accordion or filter UI.

## Required parameters
| name | type | description |
|---|---|---|
| `id` | string | Unique tabs container id (data-id attr). |
| `tabs` | array of `tab` | One per tab + panel. |

### `tab` shape
| name | type | description |
|---|---|---|
| `id` | string (required) | Tab id (e.g. `tab-001`). |
| `label` | string (required) | Visible tab label. |
| `content` | string (HTML) (required) | Panel content. |
| `panel_id` | string | Optional explicit panel id (defaults to `tabpanel-{tab.id}`). |
| `active` | boolean | Mark default-active tab. Exactly one must be active. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `aria_label` | string | `Content tabs` | `tablist` accessible name. |

## Variants
None at root.

## Canonical structure
```html
<div class="dd-tabs" data-id="{id}">
  <div class="dd-tabs__content dd-g">
    <ul class="dd-tabs__menu dd-g" role="tablist" aria-label="{aria_label}">
      <!-- per tab -->
      <li class="dd-tabs__menu-item" role="presentation">
        <button type="button"
                class="dd-tabs__menu-link {tab.active ? '-active' : ''}"
                id="{tab.id}"
                role="tab"
                aria-selected="{tab.active ? 'true' : 'false'}"
                aria-controls="{tab.panel_id|default 'tabpanel-' + tab.id}"
                tabindex="{tab.active ? '0' : '-1'}">
          {tab.label}
        </button>
      </li>
    </ul>
    <div class="dd-tabs__items dd-g">
      <!-- per panel -->
      <div class="dd-tabs__item dd-u-1-1 {tab.active ? '-active' : ''}"
           role="tabpanel"
           id="{tab.panel_id|default 'tabpanel-' + tab.id}"
           aria-labelledby="{tab.id}"
           tabindex="0"
           {% if not tab.active %}hidden{% endif %}>
        {tab.content}
      </div>
    </div>
  </div>
</div>
```

**`aria-selected` MUST always be the string `"true"` or `"false"` — never the empty string. Falsey values (`null`, `undefined`, empty) coerced via templating produce invalid ARIA. Always stringify the boolean.**
**Note:** the static reference (`dd-tabs.html`) uses `<a>` elements for tab buttons (semantically incorrect — tabs are buttons, not links), missing `tabindex` roving, and sets `aria-hidden="false"` on inactive panels (should be `hidden` attribute instead). Canonical structure above corrects this.

## Accessibility
**WCAG criteria touched:** 1.3.1, 2.1.1, 2.4.3, 2.4.7, 4.1.2.

- Follow ARIA APG tabs pattern strictly.
- Tab triggers MUST be `<button type="button">`, not `<a>`. Tabs are not links — they don't navigate to a new resource.
- Exactly one tab is `aria-selected="true"` and has `tabindex="0"`. All others `aria-selected="false"` and `tabindex="-1"` (roving tabindex).
- `role="tab"` on the button. Parent `<ul>` has `role="tablist"` and `aria-label` (or `aria-labelledby`). `role="presentation"` on `<li>` removes default list semantics.
- Panel: `role="tabpanel"` + `aria-labelledby="{tab.id}"` + `tabindex="0"` (panel itself focusable). Hide inactive panels with `hidden` attribute (NOT `display:none` only — `hidden` removes from accessibility tree).
- Keyboard:
  - Left/Right arrows: move focus between tabs and activate (if automatic activation) OR move focus only (manual activation, then Enter/Space to activate). Manual is preferred for tabs that swap large content.
  - Home/End: first/last tab.
  - Tab key: from tablist into the active panel content (not next tab).
- Focus visible on tabs and panel.
- URL hash sync: optional. If used, `href`-style links aren't needed — sync via JS push/replaceState.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | tab label + panel text |
| `$c_text_secondary` / `--dark` | inactive tab label |
| `$c_primary_action_default_*` | active tab surface/border |
| `$c_support_border` / `--dark` | tab divider |
| `$c_support_focus` / `--dark` | focus outline |
| Grid: `dd-g`, `dd-u-1-1` for panel width |

## JS hooks
- `data-id="{id}"` on root for instance targeting.
- Tab activation: handler swaps `aria-selected`, `tabindex`, `hidden` attributes.
- Arrow-key handler implements roving tabindex.

### Reference JS contract
```js
document.querySelectorAll('.dd-tabs').forEach(root => {
  const tabs = root.querySelectorAll('[role="tab"]');
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => activate(tab));
    tab.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight') focusTab(tabs, i + 1);
      if (e.key === 'ArrowLeft')  focusTab(tabs, i - 1);
      if (e.key === 'Home')       focusTab(tabs, 0);
      if (e.key === 'End')        focusTab(tabs, tabs.length - 1);
    });
  });
});

// Hash sync: when URL hash matches a tab id, activate it AND focus the matching panel
// so SR users following a deep link land in the content, not on the tab strip.
window.addEventListener('hashchange', () => {
  const tab = document.getElementById(location.hash.slice(1));
  if (tab?.role === 'tab') {
    activate(tab);
    document.getElementById(tab.getAttribute('aria-controls'))?.focus();
  }
});
```

## Example params
```json
{
  "id": "features-tabs",
  "tabs": [
    { "id": "tab-static", "label": "Static",  "content": "<p>Copy-paste HTML.</p>",    "active": true },
    { "id": "tab-drupal", "label": "Drupal",  "content": "<p>Twig templates.</p>" },
    { "id": "tab-wp",     "label": "WordPress","content": "<p>Block markup.</p>" }
  ]
}
```

## Platform translation
**Static HTML:** Include reference JS once. Loop tabs in build pipeline.

**Drupal Twig:**
```twig
<div class="dd-tabs" data-id="{{ id }}">
  <div class="dd-tabs__content dd-g">
    <ul class="dd-tabs__menu dd-g" role="tablist" aria-label="{{ aria_label|default('Content tabs') }}">
      {% for tab in tabs %}
        <li class="dd-tabs__menu-item" role="presentation">
          <button type="button" class="dd-tabs__menu-link{% if tab.active %} -active{% endif %}"
                  id="{{ tab.id }}" role="tab"
                  aria-selected="{{ tab.active ? 'true' : 'false' }}"
                  aria-controls="{{ tab.panel_id|default('tabpanel-' ~ tab.id) }}"
                  tabindex="{{ tab.active ? '0' : '-1' }}">{{ tab.label }}</button>
        </li>
      {% endfor %}
    </ul>
    <div class="dd-tabs__items dd-g">
      {% for tab in tabs %}
        <div class="dd-tabs__item dd-u-1-1{% if tab.active %} -active{% endif %}"
             role="tabpanel" id="{{ tab.panel_id|default('tabpanel-' ~ tab.id) }}"
             aria-labelledby="{{ tab.id }}" tabindex="0"{% if not tab.active %} hidden{% endif %}>
          {{ tab.content|raw }}
        </div>
      {% endfor %}
    </div>
  </div>
</div>
```

**WordPress:** Use `InnerBlocks` (one per panel) or ACF Repeater for tabs. Enqueue tabs JS globally.
