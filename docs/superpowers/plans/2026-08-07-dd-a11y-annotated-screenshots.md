# dd-a11y Annotated Screenshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace useless unmarked full-page / bare element screenshots with a hybrid pin map + annotated viewport shots so clients see *where* and *what*, while developers keep selector/snippet as source of truth.

**Architecture:** Keep axe → capture → report pipeline. Rewrite `capture_a11y_screenshots.py` to prioritize/capped plan, inject numbered pins + highlight/badge overlays via Playwright, emit `pin-map.png` + `A11Y-###.png` and a structured manifest. Normalize that shape in `run_a11y_audit.py`, then wire MD/CSV/DOCX/HTML in `generate_a11y_report.py` to prefer annotated paths and pin legends.

**Tech Stack:** Python 3, Playwright (Node), existing stdlib DOCX zip builder, pytest-style unit tests under `scripts/` or new `tests/`.

**Spec:** `docs/superpowers/specs/2026-08-07-dd-a11y-annotated-screenshots-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `custom/dd-a11y-audit/scripts/capture_a11y_screenshots.py` | Plan building (pure Python), Playwright capture with overlays |
| `custom/dd-a11y-audit/scripts/run_a11y_audit.py` | Call capture; attach `pin_map` / `pin_legend` / `issues`; optional `--screenshot-cap` / `--no-screenshots` |
| `custom/dd-a11y-audit/scripts/generate_a11y_report.py` | Task rows, MD, DOCX, dashboard HTML use pin map + annotated shots |
| `custom/dd-a11y-audit/templates/dashboard.html` | Only if copy/labels need change (prefer Python-rendered HTML first) |
| `custom/dd-a11y-audit/scripts/test_capture_plan.py` | Unit tests for plan builder (no Chromium) |
| `custom/dd-a11y-audit/scripts/test_generate_report_screenshots.py` | Unit tests for report path resolution |
| `custom/dd-a11y-audit/skills/dd-a11y/SKILL.md` | Deliverable docs |
| `custom/dd-a11y-audit/README.md`, `CLAUDE.md` | Artifact paths + pipeline notes |
| `custom/dd-a11y-audit/.claude-plugin/plugin.json` | Version bump → `1.2.0` |
| `.claude-plugin/marketplace.json` | Marketplace metadata version bump |

---

### Task 1: Unit tests for capture plan builder

**Files:**
- Create: `custom/dd-a11y-audit/scripts/test_capture_plan.py`
- Modify: `custom/dd-a11y-audit/scripts/capture_a11y_screenshots.py` (extract pure Python `build_capture_plan`)

- [ ] **Step 1: Write the failing tests**

Create `custom/dd-a11y-audit/scripts/test_capture_plan.py`:

```python
#!/usr/bin/env python3
"""Unit tests for annotated screenshot capture plan (no Chromium)."""
import unittest

from capture_a11y_screenshots import IMPACT_ORDER, build_capture_plan


def _violation(rule_id, impact, selector="main .bad"):
    return {
        "id": rule_id,
        "impact": impact,
        "nodes_preview": [{"target": [selector], "html": "<div class='bad'>x</div>"}]
        if selector
        else [{"target": [], "html": ""}],
    }


class TestBuildCapturePlan(unittest.TestCase):
    def test_task_ids_stable_over_all_violations(self):
        results = {
            "violations": [
                _violation("image-alt", "minor"),
                _violation("color-contrast", "critical"),
            ]
        }
        plan = build_capture_plan(results, cap=12)
        self.assertEqual([p["task_id"] for p in plan["all_tasks"]], ["A11Y-001", "A11Y-002"])
        # Imaging order prioritizes critical first among capped image candidates
        self.assertEqual(plan["image_tasks"][0]["task_id"], "A11Y-002")
        self.assertEqual(plan["image_tasks"][0]["rule_id"], "color-contrast")

    def test_cap_limits_image_tasks_not_task_ids(self):
        results = {
            "violations": [
                _violation(f"rule-{i}", "moderate", f".e{i}") for i in range(15)
            ]
        }
        plan = build_capture_plan(results, cap=3)
        self.assertEqual(len(plan["all_tasks"]), 15)
        self.assertEqual(len(plan["image_tasks"]), 3)

    def test_missing_selector_flagged(self):
        results = {"violations": [_violation("html-has-lang", "serious", selector="")]}
        plan = build_capture_plan(results, cap=12)
        self.assertEqual(plan["all_tasks"][0]["selector"], "")
        self.assertEqual(plan["image_tasks"], [])  # not eligible without selector

    def test_impact_order_critical_before_minor(self):
        self.assertLess(IMPACT_ORDER["critical"], IMPACT_ORDER["minor"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests — expect fail (import / function missing)**

```bash
cd /home/jlyvers/projects/dd-ai-skills/custom/dd-a11y-audit/scripts
python3 test_capture_plan.py -v
```

Expected: `ImportError` or `AttributeError` for `build_capture_plan` returning the new shape / `IMPACT_ORDER`.

- [ ] **Step 3: Implement pure Python plan builder**

In `capture_a11y_screenshots.py`, replace `build_capture_plan` with:

```python
IMPACT_ORDER = {
    "critical": 0,
    "serious": 1,
    "moderate": 2,
    "minor": 3,
}


def _first_selector(violation):
    previews = violation.get("nodes_preview") or []
    if not previews:
        return ""
    targets = previews[0].get("target") or []
    if not targets:
        return ""
    # axe target can be a string or nested list; normalize to a CSS selector string
    t = targets[0]
    if isinstance(t, list):
        return t[0] if t else ""
    return str(t) if t else ""


def build_capture_plan(results, cap=12):
    """Build full task list (stable IDs) and capped image subset.

    Returns:
      {
        "all_tasks": [{task_id, rule_id, impact, selector}, ...],
        "image_tasks": same shape, impact-sorted, selector required, max cap
      }
    """
    all_tasks = []
    for index, violation in enumerate(results.get("violations", []), start=1):
        all_tasks.append(
            {
                "task_id": f"A11Y-{index:03d}",
                "rule_id": violation.get("id", ""),
                "impact": (violation.get("impact") or "minor").lower(),
                "selector": _first_selector(violation),
            }
        )

    eligible = [t for t in all_tasks if t["selector"]]
    eligible.sort(
        key=lambda t: (IMPACT_ORDER.get(t["impact"], 9), t["task_id"])
    )
    image_tasks = eligible[: max(0, int(cap))]
    # Assign pin numbers 1..k in image_tasks order (for legend + pin map)
    for pin, item in enumerate(image_tasks, start=1):
        item["pin"] = pin

    return {"all_tasks": all_tasks, "image_tasks": image_tasks}
```

Keep existing `load_results` and CLI entry; `run_capture` will use the new plan in Task 2.

- [ ] **Step 4: Run tests — expect pass**

```bash
cd /home/jlyvers/projects/dd-ai-skills/custom/dd-a11y-audit/scripts
python3 test_capture_plan.py -v
```

Expected: `OK` (4 tests).

- [ ] **Step 5: Commit**

```bash
cd /home/jlyvers/projects/dd-ai-skills
git add custom/dd-a11y-audit/scripts/capture_a11y_screenshots.py \
        custom/dd-a11y-audit/scripts/test_capture_plan.py
git commit -m "$(cat <<'EOF'
feat(dd-a11y): add prioritized screenshot capture plan builder

Stable A11Y-### task IDs for all violations; image subset capped and sorted by impact.
EOF
)"
```

---

### Task 2: Playwright pin map + annotated viewport capture

**Files:**
- Modify: `custom/dd-a11y-audit/scripts/capture_a11y_screenshots.py`

- [ ] **Step 1: Rewrite `run_capture` to emit new result shape**

Replace the Node script body so that after `page.goto`:

1. Call Python plan: `plan = build_capture_plan(load_results(...), cap=cap)`.
2. Pass `image_tasks` into JS.
3. Inject helper functions in page for overlays (via `page.evaluate`).

**Result JSON contract (stdout):**

```json
{
  "pin_map": "/abs/or/path/pin-map.png or null",
  "pin_legend": [
    {"pin": 1, "task_id": "A11Y-002", "rule_id": "color-contrast", "impact": "critical"}
  ],
  "issue_screenshots": [
    {
      "task_id": "A11Y-002",
      "rule_id": "color-contrast",
      "selector": "...",
      "pin": 1,
      "path": ".../A11Y-002.png",
      "status": "captured"
    }
  ]
}
```

Statuses allowed: `captured`, `missing-selector`, `not-found`, `not-visible`, `capture-error`.

**JS capture algorithm (inline in the generated script string):**

```javascript
// Pseudo — implement fully in the f-string script

async function measure(locator) {
  return locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return {
      width: r.width,
      height: r.height,
      top: r.top,
      left: r.left,
      visible: style.visibility !== 'hidden' && style.display !== 'none' && r.width > 0 && r.height > 0,
    };
  });
}

async function clearOverlays(page) {
  await page.evaluate(() => {
    document.querySelectorAll('[data-dd-a11y-overlay]').forEach((n) => n.remove());
    document.documentElement.style.filter = '';
  });
}

async function addPins(page, items) {
  // items: [{pin, selector, task_id}]
  await page.evaluate((items) => {
    items.forEach((item) => {
      let el;
      try { el = document.querySelector(item.selector); } catch (e) { return; }
      if (!el) return;
      const r = el.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return;
      const pin = document.createElement('div');
      pin.setAttribute('data-dd-a11y-overlay', 'pin');
      pin.textContent = String(item.pin);
      pin.style.cssText = [
        'position:fixed',
        `top:${Math.max(0, r.top + window.scrollY)}px`.replace('scrollY', '') // use r.top + scroll in evaluate properly
      ].join(';');
      // Use position:absolute on body with getBoundingClientRect + scrollX/Y:
      // left = r.left + window.scrollX + r.width/2 - 12
      // top  = r.top + window.scrollY + r.height/2 - 12
      // z-index: 2147483646; 24x24 circle; background #b00020; color #fff;
      // font: bold 12px/24px sans-serif; text-align center; border: 2px solid #fff;
      // box-shadow 0 0 0 1px #000; pointer-events:none;
      document.documentElement.appendChild(pin);
    });
  }, items);
}

async function highlightIssue(page, item) {
  await page.evaluate((item) => {
    let el;
    try { el = document.querySelector(item.selector); } catch (e) { return; }
    if (!el) return;
    el.setAttribute('data-dd-a11y-overlay-target', '1');
    el.style.outline = '3px solid #b00020';
    el.style.outlineOffset = '2px';
    const r = el.getBoundingClientRect();
    const badge = document.createElement('div');
    badge.setAttribute('data-dd-a11y-overlay', 'badge');
    badge.textContent = `${item.task_id} · ${item.rule_id} · ${item.impact}`;
    // position absolute near element; high z-index; dark bg, white text, padding, max-width 360px
    document.documentElement.appendChild(badge);
  }, item);
}
```

**Order of operations in JS:**

1. `goto` + wait networkidle.
2. For each `image_tasks` item: resolve locator; if missing → `not-found`; if not visible → `not-visible`; else keep in `locatable`.
3. Clear overlays → add pins for all locatable → `screenshot fullPage` → `pin-map.png` (if locatable.length > 0).
4. For each locatable: clear overlays → scrollIntoView → highlightIssue → `page.screenshot` (viewport, **not** element-only) → `{task_id}.png` → status `captured`.
5. Emit result JSON. **Do not** write unmarked `full-page.png`.

**CLI:** add optional args:

```python
parser.add_argument("--cap", type=int, default=12)
```

Pass `cap` into `build_capture_plan` and `run_capture(url, results_path, output_dir, cap=12)`.

Also accept empty `image_tasks`: return `pin_map: null`, `pin_legend: []`, `issue_screenshots: []` without error.

- [ ] **Step 2: Smoke-check syntax without live site**

```bash
cd /home/jlyvers/projects/dd-ai-skills/custom/dd-a11y-audit/scripts
python3 -c "
from capture_a11y_screenshots import build_capture_plan
print(build_capture_plan({'violations': []}, cap=12))
"
```

Expected: `{'all_tasks': [], 'image_tasks': []}`.

- [ ] **Step 3: Commit**

```bash
git add custom/dd-a11y-audit/scripts/capture_a11y_screenshots.py
git commit -m "$(cat <<'EOF'
feat(dd-a11y): capture pin-map and annotated viewport screenshots

Replace bare element crops with overlay pins, badges, and capped issue shots.
EOF
)"
```

---

### Task 3: Orchestrator attaches new screenshot shape

**Files:**
- Modify: `custom/dd-a11y-audit/scripts/run_a11y_audit.py`

- [ ] **Step 1: Add helper to normalize capture output**

```python
def normalize_screenshots(shot_data, output_dir):
    """Map capture stdout into page_data['screenshots'] with relative paths."""
    if shot_data.get("error"):
        return {"error": True, "message": shot_data.get("message", "")}

    def rel(p):
        return relpath(p, output_dir) if p else None

    pin_map = shot_data.get("pin_map") or shot_data.get("full_page")  # transition
    issues = shot_data.get("issue_screenshots") or shot_data.get("issues") or []
    return {
        "pin_map": rel(pin_map) if pin_map else None,
        # Keep full_page alias = pin_map for one release so old report code can be migrated gradually
        "full_page": rel(pin_map) if pin_map else None,
        "pin_legend": shot_data.get("pin_legend") or [],
        "issues": [
            {
                **item,
                "path": rel(item["path"]) if item.get("path") else None,
            }
            for item in issues
        ],
    }
```

- [ ] **Step 2: Wire helper in single- and multi-page paths**

Replace both blocks that build `page_data["screenshots"]` with:

```python
page_data["screenshots"] = normalize_screenshots(shot_data, output_dir)
```

- [ ] **Step 3: Pass cap / skip flags**

```python
parser.add_argument("--screenshot-cap", type=int, default=12,
                    help="Max annotated issue screenshots per page (default 12)")
parser.add_argument("--no-screenshots", action="store_true",
                    help="Skip screenshot capture entirely")
```

Update `capture_screenshots`:

```python
def capture_screenshots(url, input_json, screenshots_dir, cap=12):
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "capture_a11y_screenshots.py"),
        url,
        "--input", str(input_json),
        "--output-dir", str(screenshots_dir),
        "--cap", str(cap),
    ]
    ...
```

In `main` / `run_multi_audit`, skip capture when `args.no_screenshots`; pass `args.screenshot_cap`.

Refactor `run_multi_audit` to accept `cap` and `no_screenshots` parameters from `main`.

- [ ] **Step 4: Commit**

```bash
git add custom/dd-a11y-audit/scripts/run_a11y_audit.py
git commit -m "$(cat <<'EOF'
feat(dd-a11y): attach pin_map screenshot manifest from capture

Support --screenshot-cap and --no-screenshots on the audit runner.
EOF
)"
```

---

### Task 4: Report generator — task rows + MD + CSV

**Files:**
- Modify: `custom/dd-a11y-audit/scripts/generate_a11y_report.py`
- Create: `custom/dd-a11y-audit/scripts/test_generate_report_screenshots.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python3
import unittest
import generate_a11y_report as r


class TestScreenshotRows(unittest.TestCase):
    def test_prefers_pin_map_and_captured_issue_only(self):
        results = {
            "metadata": {"url": "https://ex.com", "timestamp": "t", "score": 50, "wcag_level": "AA"},
            "summary": {
                "critical_violations": 1, "serious_violations": 0,
                "moderate_violations": 0, "minor_violations": 0,
                "total_violations": 1, "total_passes": 0,
                "total_incomplete": 0, "total_inapplicable": 0,
            },
            "principle_counts": {"perceivable": 1, "operable": 0, "understandable": 0, "robust": 0},
            "violations": [{
                "id": "color-contrast",
                "impact": "critical",
                "description": "Elements must have sufficient color contrast",
                "help": "Fix contrast",
                "wcag_tags": ["wcag143"],
                "nodes_count": 1,
                "nodes_preview": [{"target": [".x"], "html": "<span class=x>a</span>"}],
            }],
            "screenshots": {
                "pin_map": "screenshots/pin-map.png",
                "full_page": "screenshots/pin-map.png",
                "pin_legend": [{"pin": 1, "task_id": "A11Y-001", "rule_id": "color-contrast", "impact": "critical"}],
                "issues": [{
                    "task_id": "A11Y-001",
                    "path": "screenshots/A11Y-001.png",
                    "status": "captured",
                }],
            },
            "recommendations": [],
        }
        # get_pages may wrap single-page as one page — use multi shape if required
        pages = r.get_pages(results)
        self.assertTrue(pages)
        rows = r.build_task_rows(results)
        self.assertEqual(rows[0]["page_screenshot"], "screenshots/pin-map.png")
        self.assertEqual(rows[0]["issue_screenshot"], "screenshots/A11Y-001.png")

    def test_skips_non_captured_issue_path(self):
        results = {
            "metadata": {"url": "https://ex.com", "timestamp": "t", "score": 50, "wcag_level": "AA"},
            "summary": {
                "critical_violations": 0, "serious_violations": 1,
                "moderate_violations": 0, "minor_violations": 0,
                "total_violations": 1, "total_passes": 0,
                "total_incomplete": 0, "total_inapplicable": 0,
            },
            "principle_counts": {"perceivable": 0, "operable": 1, "understandable": 0, "robust": 0},
            "violations": [{
                "id": "button-name",
                "impact": "serious",
                "description": "Buttons must have discernible text",
                "help": "Add name",
                "wcag_tags": ["wcag412"],
                "nodes_count": 1,
                "nodes_preview": [{"target": ["button"], "html": "<button></button>"}],
            }],
            "screenshots": {
                "pin_map": None,
                "issues": [{"task_id": "A11Y-001", "path": None, "status": "not-found"}],
            },
            "recommendations": [],
        }
        rows = r.build_task_rows(results)
        self.assertEqual(rows[0]["issue_screenshot"], "")


if __name__ == "__main__":
    unittest.main()
```

Adjust fixture if `get_pages` expects `pages: []` multi format — inspect `get_pages` and mirror real shape used by single-page JSON (screenshots on root).

- [ ] **Step 2: Run tests — expect fail**

```bash
cd /home/jlyvers/projects/dd-ai-skills/custom/dd-a11y-audit/scripts
python3 test_generate_report_screenshots.py -v
```

- [ ] **Step 3: Update `build_task_rows`**

```python
def _page_pin_map(page):
    shots = page.get("screenshots") or {}
    return shots.get("pin_map") or shots.get("full_page") or ""


def _issue_shot_lookup(page):
    lookup = {}
    for item in (page.get("screenshots") or {}).get("issues", []):
        tid = item.get("task_id")
        if not tid:
            continue
        if item.get("status") and item.get("status") != "captured":
            continue
        if item.get("path"):
            lookup[tid] = item["path"]
    return lookup
```

In `build_task_rows`:

```python
page_screenshot = _page_pin_map(page)
screenshot_lookup = _issue_shot_lookup(page)
...
"page_screenshot": page_screenshot or "",
"issue_screenshot": screenshot_lookup.get(local_task_id, "") or "",
```

- [ ] **Step 4: Update Markdown findings**

Replace full-page block:

```python
pin_map = _page_pin_map(page)
if pin_map:
    lines.extend([
        f"![Issue pin map]({pin_map})",
        "",
    ])
legend = (page.get("screenshots") or {}).get("pin_legend") or []
if legend:
    lines.append("**Pin legend:** " + ", ".join(
        f"#{p['pin']} → {p['task_id']} ({p.get('rule_id', '')})" for p in legend
    ))
    lines.append("")
```

Issue image alt text:

```python
if shot_lookup.get(local_task_id):
    lines.append(f"![Annotated issue {local_task_id}]({shot_lookup[local_task_id]})")
```

- [ ] **Step 5: Run unit tests — expect pass**

```bash
python3 test_generate_report_screenshots.py -v
python3 test_capture_plan.py -v
```

- [ ] **Step 6: Commit**

```bash
git add custom/dd-a11y-audit/scripts/generate_a11y_report.py \
        custom/dd-a11y-audit/scripts/test_generate_report_screenshots.py
git commit -m "$(cat <<'EOF'
feat(dd-a11y): wire pin map and annotated shots into MD/CSV rows

Only link captured issue images; page screenshot path is the pin map.
EOF
)"
```

---

### Task 5: Dashboard + DOCX presentation

**Files:**
- Modify: `custom/dd-a11y-audit/scripts/generate_a11y_report.py` (`_render_page_cards`, `_render_task_rows`, `build_docx`)

- [ ] **Step 1: Page cards use pin map wording**

In `_render_page_cards`:

```python
shot = _page_pin_map(page)
...
# button label:
f'<a href="{esc_shot}" class="dd-button -secondary">View pin map'
f'<span class="visually-hidden"> of accessibility issues on {esc_url}</span></a>'
...
# empty:
extra = '<p class="muted">No pin map captured for this page (no locatable issues or capture skipped).</p>'
```

- [ ] **Step 2: Task table links**

Keep issue-first, then pin map fallback:

```python
if r.get("issue_screenshot"):
    # "Issue" → "Annotated"
    shot = (
        f'<a href="{html.escape(r["issue_screenshot"])}">Annotated'
        f'<span class="visually-hidden"> screenshot for {html.escape(r["task_id"])}</span></a>'
    )
elif r.get("page_screenshot"):
    shot = (
        f'<a href="{html.escape(r["page_screenshot"])}">Pin map'
        f'<span class="visually-hidden"> for {html.escape(r["task_id"])}</span></a>'
    )
else:
    shot = '<span class="muted">n/a</span>'
```

- [ ] **Step 3: DOCX — embed PNGs when files exist**

Implement minimal image parts (stdlib only). Resolve paths relative to the JSON file’s directory (`Path(args.input).parent`).

Add helpers:

```python
def _png_extent_emu(path, max_width_in=6.0):
    """Return (cx, cy) EMUs for a PNG using only stdlib (struct). Fallback 6in x 4in."""
    # Read IHDR width/height; scale to max_width_in; 914400 EMU per inch
    ...

def image_paragraph_xml(rid, cx, cy):
    # w:drawing with a:blip r:embed=rid — standard OOXML snippet
    ...
```

When building the zip:

- Collect list of `(docx_media_name, filesystem_path)` for pin maps and issue shots that exist on disk.
- Add `word/media/imageN.png` parts.
- Extend `[Content_Types].xml` with `Default Extension="png"`.
- Extend `word/_rels/document.xml.rels` with `image` relationships.
- In body, after pin map / issue lines, append `image_paragraph_xml` instead of (or in addition to) path text.

If a path is missing on disk, fall back to `paragraph_xml(f"Issue screenshot path: {path}")` (do not fail the report).

**Keep YAGNI:** one shared helper used for pin map + issues; skip fancy wrapping.

- [ ] **Step 4: Manual HTML fixture check (optional)**

```bash
cd /home/jlyvers/projects/dd-ai-skills/custom/dd-a11y-audit/scripts
python3 - <<'PY'
import json, tempfile, generate_a11y_report as g
from pathlib import Path
# minimal results with fake relative screenshot paths; run generate_html / write index if exposed
print("helpers ok", g._page_pin_map({"screenshots": {"pin_map": "x.png"}}))
PY
```

- [ ] **Step 5: Commit**

```bash
git add custom/dd-a11y-audit/scripts/generate_a11y_report.py
git commit -m "$(cat <<'EOF'
feat(dd-a11y): show pin maps in dashboard and embed shots in DOCX

Client-facing labels and real PNG embeds when files exist on disk.
EOF
)"
```

---

### Task 6: Docs + version bumps

**Files:**
- Modify: `custom/dd-a11y-audit/skills/dd-a11y/SKILL.md`
- Modify: `custom/dd-a11y-audit/README.md`
- Modify: `custom/dd-a11y-audit/CLAUDE.md`
- Modify: `custom/dd-a11y-audit/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: SKILL.md deliverables**

Replace:

```markdown
- `pages/<slug>/screenshots/full-page.png`
- `pages/<slug>/screenshots/A11Y-###.png`
```

With:

```markdown
- `pages/<slug>/screenshots/pin-map.png` — full-page map with numbered pins (locatable critical→moderate, capped)
- `pages/<slug>/screenshots/A11Y-###.png` — annotated viewport shot (highlight + badge) when capture succeeded
```

Notes:

```markdown
- Screenshots are hybrid evidence for clients + devs: pin map for overview, annotated shots for detail.
- Cap default 12 annotated issues/page (`--screenshot-cap`). Skip with `--no-screenshots`.
- Selector + HTML snippet remain source of truth; non-locatable issues have no image.
```

- [ ] **Step 2: README + CLAUDE.md**

Same artifact names; note capture is best-effort; remove “full-page is the floor” language.

- [ ] **Step 3: Versions**

`plugin.json`: `"version": "1.2.0"` (user-visible deliverable change).

`marketplace.json` metadata.version: bump patch (e.g. `1.3.4` → `1.3.5` — use whatever is current on disk +1).

Optionally refresh dd-a11y marketplace description to mention annotated screenshots.

- [ ] **Step 4: Validate marketplace**

```bash
cd /home/jlyvers/projects/dd-ai-skills
python3 scripts/validate_marketplace.py
```

Expected: `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add custom/dd-a11y-audit/skills/dd-a11y/SKILL.md \
        custom/dd-a11y-audit/README.md \
        custom/dd-a11y-audit/CLAUDE.md \
        custom/dd-a11y-audit/.claude-plugin/plugin.json \
        .claude-plugin/marketplace.json
git commit -m "$(cat <<'EOF'
chore(dd-a11y): document annotated screenshots and bump to v1.2.0

Marketplace metadata bump so install/update picks up the skill.
EOF
)"
```

---

### Task 7: Integration smoke (Chromium when available)

**Files:** none required (commands only); optional fixture under `custom/dd-a11y-audit/scripts/fixtures/` if useful.

- [ ] **Step 1: Run unit suite**

```bash
cd /home/jlyvers/projects/dd-ai-skills/custom/dd-a11y-audit/scripts
python3 test_capture_plan.py -v
python3 test_generate_report_screenshots.py -v
```

Expected: all pass.

- [ ] **Step 2: Live smoke (if Chromium works)**

```bash
cd /home/jlyvers/projects/dd-ai-skills/custom/dd-a11y-audit
python3 scripts/run_a11y_audit.py https://example.com --level AA --output-dir /tmp/a11y-shot-smoke --screenshot-cap 5
ls -la /tmp/a11y-shot-smoke/screenshots/ 2>/dev/null || ls -la /tmp/a11y-shot-smoke/pages/*/screenshots/ 2>/dev/null
```

Expected when issues are locatable:

- `pin-map.png` present (if ≥1 locatable violation)
- zero or more `A11Y-###.png` with status captured in JSON
- `index.html` links “Pin map” / “Annotated”

If the site is clean (no violations), pin map may be absent — that is success.

If Chromium cannot launch, document as environment limitation; unit tests remain the gate.

- [ ] **Step 3: Final commit only if smoke required tiny fixes**

```bash
# only if needed
git add -u custom/dd-a11y-audit
git commit -m "fix(dd-a11y): annotated screenshot smoke follow-ups"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Hybrid pin map + annotated viewport | Task 2 |
| Cap 12, impact priority | Task 1–2 |
| Stable A11Y-### IDs; imaging subset | Task 1 |
| Skip missing/not-found/not-visible | Task 2 |
| No unmarked full-page / bare crop | Task 2 |
| Manifest pin_legend + statuses | Task 2–3 |
| run_a11y attach shape + flags | Task 3 |
| MD / CSV paths | Task 4 |
| Dashboard labels | Task 5 |
| DOCX embed when present | Task 5 |
| Docs + version/marketplace | Task 6 |
| Success criteria / smoke | Task 7 |
| Same-session axe (non-goal) | — not planned |
| Interactive HTML viewer (non-goal) | — not planned |

---

## Self-review notes

- No TBD placeholders left in tasks.
- `full_page` alias kept one release for safer report migration; docs promote `pin_map`.
- DOCX currently path-only; Task 5 adds real PNG parts with disk existence checks.
- Plan assumes single-page JSON may host `screenshots` on root; multi-page under `pages[]` — `get_pages` already normalizes; tests must match that helper.
