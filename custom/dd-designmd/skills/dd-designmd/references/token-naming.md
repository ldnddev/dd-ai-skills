# Token naming (semantic)

Prefer role-based names over raw scales when evidence supports a role.

## Patterns

| Category | Examples |
|----------|----------|
| Color | `color.bg.canvas`, `color.bg.surface`, `color.text.primary`, `color.text.muted`, `color.brand.primary`, `color.border.subtle` |
| Font | `font.family.base`, `font.family.display`, `font.size.body`, `font.weight.bold` |
| Space | `space.xs` … `space.3xl` or measured ranks `space.01` until scale is clear; `space.container` for a repeated `max-width` |
| Radius | `radius.sm`, `radius.md`, `radius.pill` |
| Shadow | `shadow.sm`, `shadow.md` |
| Breakpoint | `breakpoint.md`, `breakpoint.lg` |

## Rules

1. **Measured first** — value must appear in CSS/HTML evidence.
2. **Provisional semantics** — if role is unclear, keep `color.palette.NN` or `space.NN` ranks.
3. **No invented hex** — never approximate a “brand blue” without a CSS hit.
4. **CSS variables** — if site defines `--*`, preserve names under `cssvar.*` and prefer them.
