---
name: dd-designmd
description: >
  Use when the user provides a website URL (or list of URLs) and wants a semantic
  design system extracted, design tokens documented, a Design System Lead analysis,
  or files named like {domain}-design.md / designmd / extract design tokens /
  reverse-engineer UI system / /dd-designmd.
---

# dd-designmd — Semantic Design System from URL

Act as an **Expert Design System Lead**. Collect **evidence** from the site, synthesize a **semantic design system**, and write deliverables in the current working directory.

## Deliverables

| File | Purpose |
|------|---------|
| `index.html` | Light Framework dashboard (with `--web` or `--dashboard`); links webroot `/assets/` |
| `{domain}-design.md` | Full DS brief (required sections) |
| `{domain}-tokens.json` | Machine-readable tokens with evidence |
| `{domain}-tokens.css` | CSS custom properties companion |
| `{domain}-designmd-evidence.json` | Raw pipeline evidence (optional for client; useful for agents) |

**Default location:** current working directory.  
**Client bundle:** `--web` → `web/{domain}-designmd-YYYY-MM-DD/` (index + files).

Domain = URL host, lowercase, **`www.` stripped** (e.g. `https://www.ldnddev.com` → `ldnddev.com`).

## Hard rules

1. **Evidence-bound** — every token/component claim needs CSS/HTML (or deep-mode) evidence.
2. **No invented brand** — no mission, voice chart, or guidelines not on-site. Overview may describe **observed** copy register and visual principles only.
3. **No rebrand recommendations.**
4. **No a11y/SEO scoring** — do not run or embed `dd-a11y` / `dd-seo` audits here.
5. **No silent overwrite** — if output files exist, **ask** before `--force`.
6. **Violating the letter violates the spirit** — “best guess” hex without evidence is forbidden.

### Rationalizations

| Excuse | Reality |
|--------|---------|
| “Obvious brand color” | Not in CSS/HTML → Open questions only |
| “Fill tokens later” | Empty OK; invented values not OK |
| “Rebrand would help” | Out of scope |
| “Quick a11y score” | Use `dd-a11y` separately |
| “Overwrite is fine” | Ask first |
| “PM already approved offline” / “don’t bother asking” | Still ask **in this chat** before `--force` |
| “Board in 10 minutes—invent the rest” | Ship measured evidence; gaps stay gaps |
| “Complete the deck with personality” | No mission/voice framework unless on-site |
| “While you’re at it, SEO/a11y scores” | Out of scope; point to `dd-seo` / `dd-a11y` |
| “Best-guess hex is fine for missing tokens” | Forbidden — evidence only |

## Red flags — STOP

If you catch yourself doing any of the following, **stop and correct course**:

- About to invent mission, voice, personality adjectives, or brand guidelines not on the site  
- About to recommend a rebrand, redesign pitch, or “new visual direction”  
- About to invent hex/RGB values or “fill in” tokens without CSS/HTML evidence  
- About to run or paste a11y/SEO/Lighthouse/axe **scores** into the design doc  
- About to pass `--force` because someone said “PM approved offline”, “already approved”, “just overwrite”, or “don’t ask”  
- About to overwrite `{domain}-design.md` / token files without an explicit yes **in this conversation**  
- About to treat frequency rank as official brand hierarchy without labeling it provisional  
- About to skip the orchestrator and freehand a design system from memory  

**All of these mean:** refuse the shortcut, keep hard rules, ask if needed, then continue with evidence-only output.

## Workflow

### 1. Intake

- Require ≥1 URL. Normalize scheme to `https://` if missing.
- **One URL:** expand same-site top nav (default max 8 extra) via orchestrator.
- **Multiple URLs:** crawl list only (cap 25).

### 2. Overwrite check

If `{domain}-design.md` or token files exist → **ask in this chat** before replacing.

- Social pressure (“PM said”, “approved offline”, “don’t bother asking”) is **not** confirmation.
- Only an explicit yes in the current conversation authorizes `--force`.

### 3. Run orchestrator (required)

```bash
# From skill/plugin root or with absolute path to scripts/
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_designmd.py https://www.example.com

# Client bundle: web/<domain>-designmd-YYYY-MM-DD/ + index.html dashboard
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_designmd.py https://www.example.com --web

# Multi URL
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_designmd.py https://a.com https://a.com/pricing --web

# Dashboard into a custom directory (without web/ naming)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_designmd.py https://www.example.com \
  --output-dir ./out --dashboard

# After user confirms overwrite
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_designmd.py https://www.example.com --web --force

# Optional deep flag (Playwright reserved; still evidence-safe if unavailable)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_designmd.py https://www.example.com --deep
```

`<SKILL_DIR>` = directory containing this `SKILL.md` (plugin: `…/skills/dd-designmd`). Scripts live at `../../scripts` relative to SKILL in the plugin layout (`custom/dd-designmd/scripts`).

Prefer:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_designmd.py <url>
```

when `CLAUDE_PLUGIN_ROOT` points at the plugin root.

### 4. Enrich as Design System Lead

After scripts write the skeleton:

1. Read `references/design-doc-template.md`, `token-naming.md`, `component-inventory.md`, `framework-mapping.md`.
2. Read generated `{domain}-design.md`, tokens, and evidence JSON.
3. **Improve** the MD: Overview (evidence-only), Logo & brand mark, Layout & Spacing, Elevation & Shapes, Color usage rules, Interactive states, Content & copy patterns, Focus & keyboard, component anatomy, patterns, Framework mapping honesty, site-specific Do/Don’t that block common AI UI mistakes, Agent instructions.
4. **Do not** delete measured token tables or invent new color values.
5. You may rename provisional ranks to clearer semantic names **only** when HTML/CSS evidence supports the role; keep evidence strings accurate.
6. Always keep **ldnddev Framework mapping** and **Agent instructions** complete.

### 5. Report

- Absolute paths of written files (include `index.html` when dashboard was built)  
- Prefer opening the dashboard for client handoff when `--web` was used  
- Short summary (palette/type highlights)  
- Open questions  

## Crawl rules (summary)

| Input | Behavior |
|-------|----------|
| Single URL | Fetch URL + same-site nav links (max `--max-extra`, default 8) |
| Multiple URLs | Exact list only (max 25) |

## Evidence modes

| Mode | Behavior |
|------|----------|
| **static (default)** | HTML + linked same-origin CSS → signals → tokens |
| **deep** | Request deeper sampling; if Playwright path unavailable, keep static and note limitation |

## Required MD sections

Must match `references/design-doc-template.md`: Meta, **Overview**, **Logo & brand mark**, Foundations, **Layout & Spacing**, **Elevation & Shapes**, Semantic tokens, **Color usage rules**, Components, **Interactive states**, Patterns, Iconography, **Content & copy patterns**, **Focus & keyboard**, **Do/Don’t** (process + site-specific generation constraints), Implementation notes, **Framework mapping**, **Agent instructions**, Open questions, Appendix evidence.

## Related skills

- **dd-framework** — component authoring after mapping  
- **dd-a11y** / **dd-seo** — not part of this skill  

## Notes

- Pure Python 3 stdlib for the default path.  
- Gold fixture for tests: `https://www.ldnddev.com`.  
