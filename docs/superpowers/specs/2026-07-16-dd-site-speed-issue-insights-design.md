# dd-site-speed: Per-Issue Insights Design

**Date:** 2026-07-16  
**Status:** Approved  
**Skill:** `custom/dd-site-speed-audit`  
**Scope:** Add structured insights (what / why / how) to every speed issue across all client deliverables; align standalone PSI helper with env API key.

---

## Problem

The skill already generates prioritized remediation tasks from Lighthouse opportunities and CWV ratings. Each task has a short `how` string from an in-code `PLAYBOOK`, and full how-to text is available in `ACTION-PLAN.md` / `tasks.csv`. Gaps:

1. There is no plain-language **description of the issue** or **why it matters** (only title + short fix).
2. The **HTML dashboard** task table does not surface how-to or educational text (footnote points to other files).
3. Clients opening any single artifact should still understand each issue end-to-end.

Separately: `run_speed_audit.py` reads `PAGESPEED_API_KEY` / `PSI_API_KEY` by default; standalone `pagespeed.py` does not, which caused failed tests when the key was only in the environment.

---

## Goals

1. Every remediation task includes three insight fields:
   - **What it means** — plain-language description of the issue
   - **Why it matters** — impact on CWV, score, and user experience
   - **How to fix** — actionable remediation (existing playbook quality or better)
2. Insights appear in **all** deliverables: dashboard, both Markdown reports, both DOCX files, and `tasks.csv`.
3. Content is **deterministic** (curated playbook + fallbacks), offline-safe, no LLM required for the bundle.
4. Dashboard remains scannable: insights live in **expandable detail rows**.
5. `pagespeed.py` CLI defaults API key from the same env vars as the orchestrator.

## Non-goals

- LLM post-processing of insight prose after the pipeline
- Changing PSI fetch strategy, thresholds, or severity heuristics
- Redesigning the full dashboard layout or introducing a new CSS framework
- Moving playbook content to a separate YAML/MD loader in this iteration

---

## Decisions (from design discussion)

| Topic | Choice |
|-------|--------|
| Deliverable coverage | All artifacts (dashboard + MD + DOCX + CSV) |
| Insight structure | Three fields: what / why / how |
| Content source | Hybrid: curated playbook for all three; PSI `description` fallback when ID unknown |
| Dashboard UX | Expandable row under each task |
| Implementation approach | Expand `PLAYBOOK` in `generate_report.py` (single source of truth) |

---

## Architecture

```
PSI opportunities + diagnostics
        │
        ▼
build_task_rows() ──► PLAYBOOK[id] {what, why, how, owner, effort, metric}
        │                 └─ unknown id → what=PSI description, why=generic, how=generic
        │                 └─ stack_tips() appended to how
        ▼
task rows (dict per task)
        │
        ├─► SPEED-AUDIT-REPORT.md
        ├─► ACTION-PLAN.md
        ├─► SPEED-CLIENT-REPORT.docx
        ├─► ACTION-PLAN.docx
        ├─► tasks.csv  (columns: what, why, how, …)
        └─► index.html  (table row + expandable detail)
```

No new runtime dependencies. Pure Python stdlib + existing templates.

---

## Data model

### PLAYBOOK entry shape

```python
"render-blocking-resources": {
    "owner": "Frontend Development",
    "effort": "M",
    "metric": "LCP",
    "what": "Stylesheets or scripts block the browser from painting the first screen until they finish downloading and executing.",
    "why": "Increases Largest Contentful Paint and First Contentful Paint, lowering the Lighthouse performance score and delaying when users see primary content.",
    "how": "Defer non-critical CSS/JS, inline critical CSS, use async/defer on scripts, or split bundles so above-the-fold content is not blocked.",
},
```

### Task row fields (additions)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `what` | str | yes | From playbook or fallback |
| `why` | str | yes | From playbook or fallback |
| `how` | str | yes | Existing field; may include stack tip suffix |

Existing fields (`task_id`, `priority`, `severity`, `title`, `opportunity_id`, `metric`, `est_savings*`, `owner`, `timeline`, `evidence`, `page_url`, etc.) remain.

### Fallback rules

When `opportunity_id` is not in `PLAYBOOK` (or entry missing a field):

| Field | Fallback |
|-------|----------|
| `what` | PSI opportunity `description` (trimmed, max ~400 chars), else: `"Lighthouse flagged this opportunity during the performance audit."` |
| `why` | `"Improves {metric} and the overall performance score when addressed."` using task metric when known |
| `how` | Existing short default: `"Review the Lighthouse opportunity and apply the documented fix."` (+ stack tip if any) |

CWV synthetic tasks (`cwv-lcp`, `cwv-inp`, `cwv-cls`) must have explicit PLAYBOOK (or inline curated) entries with all three fields.

### CSV columns

Include `what` and `why` as dedicated columns. Keep `how`. Suggested column order for readability:

`task_id`, `priority`, `severity`, `title`, `what`, `why`, `how`, `metric`, `est_savings`, `owner`, `timeline`, `page_url`, `page_slug`, `effort`, `stack`, `strategy`, `evidence`, `opportunity_id`, `status`

Do not remove columns consumers may already depend on.

---

## Content coverage

Expand PLAYBOOK for every opportunity ID already present (render-blocking, unused JS/CSS, images, server-response, redirects, compression, cache TTL, preconnect, font-display, bootup, mainthread, third-party, dom-size, total-byte-weight, legacy-js, minify, animated content, unsized images, layout-shift, priority-hints, offscreen-images, etc.).

Also document CWV metric tasks:

- `cwv-lcp`
- `cwv-inp`
- `cwv-cls`

Tone: client-friendly, technical enough for implementers, no invented savings numbers, no FID references.

Optionally align `skills/dd-site-speed/references/optimization-playbook.md` with What/Why/How one-liners so agents stay consistent with report text (documentation sync, not a second runtime source).

---

## Dashboard UX

### Main table

Unchanged columns:

ID | Priority | Severity | Issue | Metric | Est. savings | Owner | Timeline | Page

### Expand / collapse

- Each main row has a keyboard-accessible control (e.g. button on the Issue cell or a dedicated “Details” control) with:
  - `aria-expanded="true|false"`
  - `aria-controls` pointing at the detail row id
- Activating the control toggles a **detail row** immediately below the main row spanning all columns.
- Detail content structure:

```html
<div class="task-insights">
  <section>
    <h3>What it means</h3>
    <p>…</p>
  </section>
  <section>
    <h3>Why it matters</h3>
    <p>…</p>
  </section>
  <section>
    <h3>How to fix</h3>
    <p>…</p>
  </section>
</div>
```

- Prefer existing `dd-*` utility/spacing classes; add minimal CSS only if required (can live in dashboard inline style block or template assets if the skill already copies CSS).
- Filter behavior: include insight text in filterable content (e.g. `data-filter-text` on the main row concatenating title + what + why + how) so search still finds issues by insight keywords.
- Update the muted footer note: insights are expandable in the table; full text also remains in ACTION-PLAN / CSV / DOCX.
- No third-party JS. Inline script in `dashboard.html` (or extend existing script block) is fine.

### Accessibility

- Toggle is a real `<button type="button">`, not a clickable `<div>`.
- Detail region is not focus-trapped; natural tab order continues.
- Expanded state announced via `aria-expanded` (optional polite live region only if already present for filter status).

---

## Markdown & DOCX

### ACTION-PLAN.md and SPEED-AUDIT-REPORT.md

For each task, render:

```markdown
### SPEED-001 — Eliminate render-blocking resources
- **Priority:** P0 · **Severity:** Critical · **Metric:** LCP · **Est. savings:** 1.2s
- **Owner:** Frontend Development · **Timeline:** …
- **What it means:** …
- **Why it matters:** …
- **How to fix:** …
- **Evidence:** …
```

(Keep existing fields; insert the three insight bullets in a consistent order.)

### DOCX (client report + action plan)

Mirror the same three labeled paragraphs under each task. Truncate only if an existing length guard applies; prefer full insight text (insights are typically 1–3 sentences each).

---

## `pagespeed.py` env key default

Align CLI with orchestrator:

```python
parser.add_argument(
    "--api-key",
    default=os.environ.get("PAGESPEED_API_KEY") or os.environ.get("PSI_API_KEY"),
    help="Google PageSpeed API key (optional; also PAGESPEED_API_KEY / PSI_API_KEY env)",
)
```

Requires `import os` if not already present. No behavior change when env is unset.

---

## Files to change

| Path | Change |
|------|--------|
| `custom/dd-site-speed-audit/scripts/generate_report.py` | Expand PLAYBOOK; set `what`/`why`/`how` in `build_task_rows`; CSV headers; MD/DOCX/HTML renderers |
| `custom/dd-site-speed-audit/templates/dashboard.html` | Expandable rows, detail markup, filter data, footer copy, small JS/CSS |
| `custom/dd-site-speed-audit/scripts/test_generate_report.py` | Assertions for insights + fallbacks + HTML expand markup |
| `custom/dd-site-speed-audit/scripts/pagespeed.py` | Default `--api-key` from env |
| `custom/dd-site-speed-audit/skills/dd-site-speed/references/optimization-playbook.md` | Optional: document What/Why/How pattern |
| `custom/dd-site-speed-audit/skills/dd-site-speed/SKILL.md` / README | Brief mention of insights in deliverables (if needed) |

---

## Testing

1. **Unit (no network):** `python3 scripts/test_generate_report.py`
   - Known opportunity ID → non-empty `what`, `why`, `how`
   - Unknown ID → fallback path produces all three strings
   - CWV-only tasks include curated insights
   - `tasks.csv` contains `what` and `why` columns
   - Generated `index.html` includes expand control attributes and insight headings
   - MD action plan contains “What it means” / “Why it matters” / “How to fix”
2. **Manual (optional, needs API key):** run `run_speed_audit.py` on a slow page; open dashboard and expand a task; spot-check CSV and ACTION-PLAN.md.
3. **Env key:** `pagespeed.py https://example.com` with `PAGESPEED_API_KEY` set succeeds without `--api-key`.

---

## Success criteria

- [ ] Every generated task has non-empty `what`, `why`, and `how`
- [ ] Dashboard: each task expands to show the three sections; keyboard operable
- [ ] ACTION-PLAN.md, SPEED-AUDIT-REPORT.md, both DOCX, and tasks.csv include all three fields
- [ ] Unknown Lighthouse IDs still get usable fallbacks
- [ ] Existing tests pass; new insight tests pass
- [ ] `pagespeed.py` uses env API key by default
- [ ] No new pip dependencies

---

## Implementation notes

- Keep playbook prose concise (roughly 1–3 sentences per field) to avoid oversized DOCX/CSV cells.
- Escape HTML when injecting insights into the dashboard.
- Do not invent `est_savings` values; insights must not claim specific ranking improvements.
- Stack tips remain appended to `how` only (not duplicated into `what`/`why`).
- Prefer minimal CSS; if expand chevron is needed, use text (“Details” / “Hide”) for clarity without icon fonts.

---

## Open items resolved

| Item | Resolution |
|------|------------|
| Where insights show | All deliverables |
| Structure | what + why + how |
| Source | Curated PLAYBOOK + PSI/generic fallback |
| Dashboard | Expandable detail rows |
| Approach | In-code PLAYBOOK expansion |
| pagespeed env key | In scope as small related fix |
