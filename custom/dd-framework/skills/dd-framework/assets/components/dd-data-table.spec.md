# dd-data-table

## Purpose
Accessible data table with a caption, scoped header cells, and optional status cells that embed `dd-badge`. Wraps the table in a keyboard-focusable horizontal scroll region and supports optional column sorting and an empty state.

## Context
- Wraps in `dd-section`.
- For report data, comparison grids, and audit result listings.
- Status cells embed `dd-badge`. Provide an empty-state row when there is no data.

## Required parameters
| name | type | description |
|---|---|---|
| `caption` | string | Names the table via `<caption>`. Also used as the scroll-region label fallback. |
| `columns` | array | Each: `label` (string), `align` (`start`\|`end`), `sortable` (bool), `sort_key` (string, when sortable). |
| `rows` | array | Each row is an array of cells. First cell should be a row header (`<th scope="row">`). |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `variant` | enum | — | `-dense` reduces cell padding for compact tables. |
| `scroll_label` | string | `caption` | `data-label` supplying the scroll-region name; falls back to the caption text. |
| `empty` | string | — | Empty-state message rendered as a single row `<tr class="-empty">` (excluded from sorting). |

## Variants
| modifier | effect |
|---|---|
| (none) | Comfortable default spacing. |
| `-dense` | Reduced cell padding for data-heavy tables. |

## Canonical structure
```html
<!-- Scroll region's tabindex/role/aria-label are added by JS ONLY when the
     table overflows; data-label supplies the accessible name. -->
<div class="dd-data-table {variant}">
  <div class="dd-data-table__scroll" data-label="{scroll_label}">
    <table class="dd-data-table__table" id="{id}">
      <caption class="dd-data-table__caption">{caption}</caption>
      <thead>
        <tr>
          <!-- plain header -->
          <th scope="col" class="dd-data-table__th" data-align="start">{label}</th>
          <!-- sortable header: native button, aria-sort on the th -->
          <th scope="col" class="dd-data-table__th" data-align="start" aria-sort="none">
            <button type="button" class="dd-data-table__sort" data-sort-key="{sort_key}">{label}<span class="dd-data-table__sort-ind" aria-hidden="true"></span></button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr class="dd-data-table__row">
          <th scope="row" class="dd-data-table__td" data-align="start">{row_header}</th>
          <td class="dd-data-table__td"><!-- may embed dd-badge --></td>
          <td class="dd-data-table__td" data-align="end">{cell}</td>
        </tr>
        <!-- empty state -->
        <tr class="dd-data-table__row -empty"><td class="dd-data-table__td" colspan="{n}">{empty}</td></tr>
      </tbody>
    </table>
  </div>
</div>
```
See `dd-data-table.html`.

## Accessibility
**WCAG criteria touched:** 1.3.1 Info and Relationships, 1.4.10 Reflow, 2.1.1 Keyboard, 2.4.7 Focus Visible, 2.5.8 Target Size, 4.1.2 Name/Role/Value.

- **Semantic table.** Use a real `<table>` with a `<caption>` and `<th scope="col">` / `<th scope="row">`. The caption names the table; scope associates headers with cells (1.3.1).
- **Scroll region is conditional.** The JS gives `.dd-data-table__scroll` `tabindex="0"`, `role="region"`, and an `aria-label` **only when it actually overflows** — so keyboard users can scroll a wide table without an empty tab stop / stray landmark when it fits (1.4.10, 2.1.1). Do NOT hard-code these attributes in source; let the JS toggle them. `data-label` provides the name; it falls back to the caption text.
- **Region name should differ from the caption.** When the region is promoted, its `aria-label` and the table's `<caption>` announce back-to-back. If `data-label` equals the caption text, a SR user hears the same string twice ("…region", then "…table"). Prefer a `data-label` that appends a scroll hint — e.g. `"Prioritized remediation tasks, scrollable"` — so the region name is distinct and explains why it is focusable.
- **Sorting is native + keyboard-operable.** Sortable columns use `<button>` inside the `<th>`; `aria-sort` lives on the `<th>` and is `ascending`/`descending`/`none`, with **exactly one** column non-`none` at a time (4.1.2). The `__sort-ind` arrow is decorative (`aria-hidden`).
- **Focus ring** uses a high-contrast dark color (not brand green) so it stays visible on every cell background (2.4.7). Sort buttons meet the 24×24 target minimum (2.5.8).
- Status cells embed `dd-badge` — severity is the badge word, not color alone (1.4.1).

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | cell + header text |
| `$c_support_border` / `--dark` | cell borders, scroll edge |
| `$c_text_primary` / `--dark` | focus outline (high-contrast, not brand green) |

## JS hooks
`source/js/components/_dd_data_table.js`:
- `.dd-data-table__scroll` — overflow detection toggles `tabindex`/`role`/`aria-label` on load, `htmx:afterSettle`, and `resize`.
- `.dd-data-table__sort` (button) with `data-sort-key` — click sorts rows, flips `aria-sort`, resets all other headers to `none`. Numeric-aware; `-empty` rows are excluded from sorting.
- Re-inits idempotently via `data-dd-init`.

## Example params
```json
{
  "caption": "Prioritized remediation tasks",
  "columns": [
    { "label": "ID", "align": "start" },
    { "label": "Priority", "align": "start", "sortable": true, "sort_key": "priority" },
    { "label": "Finding", "align": "start" },
    { "label": "Effort", "align": "end", "sortable": true, "sort_key": "effort" }
  ],
  "rows": [
    ["SEO-001", { "badge": "-critical", "label": "Critical" }, "Missing <title> tag", "2h"]
  ]
}
```

## Platform translation
**Static HTML:** Emit the semantic table; do NOT add scroll-region `tabindex`/`role`/`aria-label` (JS owns those). Set `aria-sort="none"` on sortable headers.

**Drupal Twig / WordPress:** Loop `columns` into `<thead>` (wrap sortable labels in the sort button), loop `rows` into `<tbody>` (first cell `<th scope="row">`, status cells render a `dd-badge`). Emit the `-empty` row when `rows` is empty. Enqueue `_dd_data_table.js`.
