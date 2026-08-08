# dd-a11y: Annotated Screenshots Design

**Date:** 2026-08-07  
**Status:** Approved (design discussion)  
**Skill:** `custom/dd-a11y-audit`  
**Scope:** Make page screenshots useful for **both** client stakeholders and developers; remove unannotated element-only crops that do not show the problem.

---

## Problem

After axe runs, `capture_a11y_screenshots.py` reloads each URL and:

1. Saves a **full-page** PNG with **no markers**.
2. For each violation, takes only the **first node’s** CSS selector and runs `locator.screenshot()` — a tight crop with **no outline, no label, no page context**.

Clients see either a generic page picture or an isolated element that often looks fine. Developers already get selector + HTML snippet in tables/CSV; the images rarely add evidence. The WCAG audit rubric asks for **annotated** screenshots; the pipeline never produced them.

Many a11y failures are also **non-visual** (missing names, ARIA, document language). A bare crop cannot prove those issues without callouts.

---

## Goals

1. **Clients** can open the dashboard (or DOCX) and see *where* on the page a problem is and *which* rule/severity it is, without reading CSS selectors.
2. **Developers** still treat selector, HTML snippet, rule id, and axe help URL as the **source of truth**; screenshots are supporting evidence with stable `task_id` linkage (`A11Y-###`).
3. **No noise:** skip un-locatable / non-spatial issues; cap volume so multi-page audits stay bounded.
4. **Stop** shipping unannotated element-only crops and unmarked full-page PNGs.

## Non-goals (v1)

- Capturing in the **same** browser session as axe (SPA/modals) — desirable later; out of scope for v1.
- Interactive HTML evidence viewer (highlight-on-click).
- Separate mobile/tablet screenshot sets (multiple viewports).
- LLM-generated image captions or image analysis.
- Changing axe rules, scoring, or WCAG level defaults.

---

## Decisions (from design discussion)

| Topic | Choice |
|-------|--------|
| Primary audience | **Both** clients and developers (option C) |
| Approach | **Hybrid:** full-page pin map + annotated per-issue viewport shots |
| Priority for images | critical → serious → moderate |
| Cap (default) | **12** annotated issue shots + **1** pin map per page (CLI-overridable later if needed) |
| Pin map severity floor | Include issues in the capped set (same priority order); pin map only if ≥1 locatable target |
| Document-level / no bbox | **Skip image**; keep text evidence only |
| Full-page without pins | **Do not emit** unmarked full-page as issue evidence; pin map replaces it when possible |
| DOCX | **Embed** annotated issue images under findings when present; embed pin map once per page when present |
| Dashboard | Page card → pin map; issue row → annotated shot (fallback to pin map link) |
| CSV | Paths only (no binary) |
| Same-session axe capture | Deferred |

---

## Architecture

```
axe_audit.py  →  axe-results.json (violations + nodes_preview target/html)
        │
        ▼
capture_a11y_screenshots.py  (Playwright reload — v1)
        │
        ├─ prioritize + cap violations/nodes
        ├─ inject pin overlays (numbered) for locatable capped set
        ├─ full-page screenshot → screenshots/pin-map.png
        ├─ per issue: highlight + badge + viewport shot
        │              → screenshots/A11Y-###.png
        └─ manifest JSON (paths, status per task)
        │
        ▼
run_a11y_audit.py  attaches screenshots{} onto page data
        │
        ▼
generate_a11y_report.py  → MD / action plan / CSV / DOCX / index.html
```

No new runtime dependencies beyond existing Playwright + Chromium.

---

## Capture behavior (detailed)

### Plan construction

From each page’s `axe-results.json` `violations[]` (preserve existing task id order `A11Y-001…` as today):

1. For each violation, prefer the **first node** with a usable `target` selector (same as today for task↔selector mapping unless we later expand multi-node).
2. Sort candidates for **imaging** by impact: `critical` > `serious` > `moderate` > `minor`.
3. Take the first **N** (default **12**) that are eligible for capture attempts.
4. Remaining violations: no issue screenshot; still listed in reports with text evidence.

**Note:** Task IDs stay sequential over **all** violations (report order). Imaging is a subset; missing shot is normal, not an error.

### Locatability rules (skip image)

Mark status and do not write a misleading PNG when:

| Status | Condition |
|--------|-----------|
| `missing-selector` | No CSS target on the node |
| `not-found` | Locator count is 0 after load |
| `not-visible` | Bounding box missing, zero size, or fully outside layout (off-screen / `visibility:hidden` with no box) |
| `skipped-nonvisual` | Optional heuristic: document-level rules with no meaningful spatial target (e.g. pure `html`/`body` lang-only) when pin would not help — still attempt if a target exists |
| `capture-error` | Playwright exception |

Text evidence always remains.

### Pin map (client overview)

1. Navigate to URL (`networkidle`, same defaults as today).
2. For each locatable item in the capped set, inject a fixed-position **pin** at the element’s center (or top-left of box if center is awkward), labeled with pin index `1…k` and data attributes linking to `task_id`.
3. Pins use high-contrast styling (not color-alone: include the number text).
4. `page.screenshot({ fullPage: true })` → `screenshots/pin-map.png`.
5. Emit legend data in capture result JSON: `{ pin: 1, task_id, rule_id, impact }[]` for report generators (do not rely on OCR of the image).

If **zero** locatable targets: omit pin map (`full_page` / `pin_map` null); do not write an unmarked full-page PNG for “evidence.”

### Per-issue annotated viewport (shared detail)

For each locatable capped item:

1. Clear previous issue-only overlays (keep pins optional: **remove pins** during issue shots so the frame is clean, or hide pin layer via CSS class).
2. Scroll target into view.
3. Apply **highlight**: outline/ring on the element; optional semi-transparent page dim with a “hole” over the target’s bounding box.
4. Apply **badge** near the element (not clipped off-screen if possible):  
   `{task_id} · {rule_id} · {impact}`  
   When rule is color-contrast and axe node data includes contrast ratio / colors, append ratio (and fg/bg if present in node `any`/`all` data — use only if already in our JSON; do not invent).
5. Capture **viewport** screenshot (not bare `locator.screenshot()`), path `screenshots/{task_id}.png`.
6. Status `captured`.

### Capture result shape (attached to page data)

```json
{
  "pin_map": "…/screenshots/pin-map.png",
  "pin_legend": [
    { "pin": 1, "task_id": "A11Y-001", "rule_id": "color-contrast", "impact": "serious" }
  ],
  "issues": [
    {
      "task_id": "A11Y-001",
      "rule_id": "color-contrast",
      "selector": "…",
      "path": "…/screenshots/A11Y-001.png",
      "status": "captured",
      "pin": 1
    }
  ]
}
```

Backward compatibility: report generator should accept both:

- New: `screenshots.pin_map`, `screenshots.pin_legend`, `screenshots.issues[]`
- Old: `screenshots.full_page`, `screenshots.issues[]` with only path — map `full_page` → treat as pin map if present during transition, then remove old field writes.

---

## Deliverable wiring

### HTML dashboard (`generate_a11y_report.py` + `templates/dashboard.html`)

- **Page cards:** show pin map thumbnail/link when available; accessible name e.g. “Pin map for {url}”.
- **Issues table:** screenshot column links to annotated issue image; if missing, link to pin map when that task is in the legend; else “—” / text-only.
- Pin legend can appear under the page section (list or small table), not only inside the PNG.

### Markdown (`WCAG-AUDIT-REPORT.md`, action plan as applicable)

- Per page: embed pin map once (`![Pin map](…)`).
- Per finding: embed annotated shot when `status === captured'`; otherwise omit image and keep selector/snippet.

### DOCX

- Same embedding policy as Markdown (images in package when paths exist and are readable).
- If embedding is too large for huge multi-page runs, still prefer embed for v1 with the **12-shot cap** controlling size; revisit link-only later if needed.

### CSV (`REMEDIATION-TASKS.csv`)

- Columns: keep/extend path fields: `page_screenshot` → prefer pin map path; `issue_screenshot` → annotated path or empty.
- No image binaries.

---

## CLI / orchestration

- `run_a11y_audit.py` continues to call capture after each page’s axe JSON is written.
- Defaults: cap **12**, priority as above. Optional flags (nice-to-have in same release if cheap):

  - `--screenshot-cap N`
  - `--no-screenshots` (skip capture entirely for speed/CI)

- Skill docs (`SKILL.md`, README, CLAUDE.md) updated: describe pin map + annotated shots; remove “full-page is the floor” wording that implies unmarked page shots are sufficient evidence.

---

## Failure modes

| Failure | Behavior |
|---------|----------|
| Chromium / Playwright unavailable | Existing structured error path; no screenshots; audit JSON/report text still generated when axe path allows |
| Capture script fails mid-page | Page `screenshots.error`; continue other pages |
| Selector works in axe but not on reload | `not-found`; text evidence only (document SPA limitation) |
| Overlay CSS broken by site CSP | Prefer injected DOM + inline styles via Playwright `addStyleTag` / element handles; if still blocked, fall back to unstyled viewport + badge in Playwright screenshot via canvas is **out of scope** — mark `capture-error` |

---

## Testing

1. **Unit:** plan builder — ordering by impact, cap, task id stability, legend length.
2. **Unit / fixture:** report generator links pin map vs issue path; missing shot does not break HTML.
3. **Integration (optional, Chromium):** small static HTML fixture with known contrast failure + missing alt; assert pin-map and at least one annotated file exist and are non-empty.
4. **Regression:** `test_a11y_skill.py` simulated path still works without requiring real screenshots.

---

## Rollout / versioning

- Bump `custom/dd-a11y-audit/.claude-plugin/plugin.json` version (patch or minor: recommend **minor** if behavior is user-visible deliverable change).
- Bump root `.claude-plugin/marketplace.json` `metadata.version`.
- Update marketplace plugin description only if needed for clarity.

---

## Success criteria

1. For on-screen critical/serious issues with valid selectors, the dashboard shows an image where a non-developer can point to the failing UI and read rule/severity from the badge or legend.
2. Developers can map pin number / badge `A11Y-###` → table row → selector + snippet without the image.
3. Multi-page runs do not unbounded-screenshot (default cap 12 + 1 pin map per page).
4. No deliverable presents an unmarked full-page or bare element crop as primary issue evidence.

---

## Implementation outline (for planning skill)

1. Rewrite `capture_a11y_screenshots.py` (plan, inject, pin map, annotated viewport, statuses, JSON shape).
2. Update `run_a11y_audit.py` attachment shape (`pin_map` / `pin_legend` / issues).
3. Update `generate_a11y_report.py` + `dashboard.html` wiring and accessible link names.
4. Docs: SKILL.md, README, CLAUDE.md, rubric note if needed.
5. Tests + version bumps + marketplace validate.

---

## Open points resolved

| Question | Resolution |
|----------|------------|
| Audience | Both (C) |
| Drop vs upgrade | Upgrade hybrid; drop only useless image types |
| Cap | 12 annotated + 1 pin map / page |
| DOCX | Embed when present |
