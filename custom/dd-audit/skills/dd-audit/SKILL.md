---
name: dd-audit
description: >
  Orchestrate a primary-URL site audit by invoking installed dd-crawl, dd-seo,
  and dd-site-speed skills into one nested folder with a cover dashboard.
  Requires dd-crawl, dd-seo, dd-site-speed, and dd-site-compare installed.
  Use when the user wants a full site audit package, master dashboard, combined
  crawl+SEO+speed report, /dd-audit, or "run all the site audits".
---

# dd-audit — Orchestrator (handoff wrapper)

Act as a **thin orchestrator**. This skill does **not** crawl, score SEO, or call PageSpeed. It requires four sibling skills to be installed, runs three of them **in full** for a primary URL, and writes a cover dashboard that **links** to each child dashboard without rewriting them.

**v1 run set:** `dd-crawl` + `dd-seo` + `dd-site-speed`.  
**v1 install set (all required):** those three **plus** `dd-site-compare` (installed, not invoked).

## Hard rules

1. **Preflight first** — if any of the four skills is missing or unusable, **stop**. Print the preflight `install_help` verbatim. Do not improvise a substitute audit.
2. **Invoke children in full** — for each v1 run module, **read that skill's SKILL.md and follow it**. Do not skip LLM/enrichment steps those skills require.
3. **Do not inline** crawl, SEO, speed, or compare logic here. Do not copy their scripts.
4. **Do not rewrite** child HTML, CSS, or reports. Nested `crawl/`, `seo/`, `speed/` bundles stay as those skills wrote them.
5. **Continue on child run error** — a failed child becomes a Failed tile. Still run the remaining children and still assemble the cover dashboard.
6. **No invented scores** — overview headlines come from child `data.json` / `tasks.csv` / presence of `index.html` only.
7. **No silent overwrite** — if the parent folder already has files, **ask** before `--force`.
8. **Compare is not run in v1** — still must be installed. Do not invent peer URLs to force a compare.

## Workflow

### 1. Intake

Require ≥1 primary URL. Normalize missing scheme to `https://`. v1 uses the **first URL only**.

### 2. Preflight (required)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_audit.py --preflight
```

If `ok` is false: show `install_help` to the user and **stop**. Typical install:

```text
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-crawl@dd-skills
/plugin install dd-seo@dd-skills
/plugin install dd-site-speed@dd-skills
/plugin install dd-site-compare@dd-skills
```

Codex, from the dd-ai-skills repo:

```text
bash custom/dd-crawl-audit/install.sh
bash custom/dd-seo-audit/install.sh
bash custom/dd-site-speed-audit/install.sh
bash custom/dd-site-compare-audit/install.sh
```

Overrides if plugins live outside the search path: `DD_CRAWL_ROOT`, `DD_SEO_ROOT`, `DD_SITE_SPEED_ROOT`, `DD_SITE_COMPARE_ROOT`.

### 3. Init parent folder

If `{domain}-site-audit-*` already exists with files → **ask** before `--force`.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_audit.py https://www.example.com
# After yes:
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_audit.py https://www.example.com --force
```

Default parent: `web/<domain>-site-audit-YYYY-MM-DD/` (`www.` stripped).  
The JSON `modules` list is the source of `skill_md`, `entry`, and `output_dir` for each child.

### 4. Invoke children (full skills, continue on error)

For each module with `run_in_v1` (crawl, seo, speed), **in that order**:

1. Read that module's `skill_md`.
2. Execute that skill **in full** against the primary URL.
3. Constrain its bundle to `output_dir` from the plan (`--no-web --output-dir` for crawl; `--output-dir` for SEO `generate_report.py` and speed). `invoke_hint` is the output-dir constraint only — the rest of the child skill still applies (SEO LLM report + `generate_report.py`, speed enrichment, crawl options).
4. If the child fails: write `output_dir/error.txt` with the error, **do not stop**, continue to the next module.

Do not run `dd-site-compare` in v1.

PageSpeed API key: follow **dd-site-speed** (not dd-seo). Ask once before the speed child run.

### 5. Assemble cover dashboard

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_audit.py --assemble web/<domain>-site-audit-YYYY-MM-DD
```

Writes `index.html` + `data.json` in the parent. Does not modify child files.

### 6. Report

- Absolute path to the parent `index.html`
- Which modules are OK vs failed (and the error text)
- Paths to each child dashboard that exists
- Open questions / environment limitations from the children (do not merge into a fake overall score)

## Folder (v1)

```text
web/<domain>-site-audit-YYYY-MM-DD/
  index.html      ← cover (this skill)
  data.json       ← rollup headlines only
  plan.json
  crawl/          ← full dd-crawl bundle
  seo/            ← full dd-seo bundle
  speed/          ← full dd-site-speed bundle
```

## Related

- **dd-crawl**, **dd-seo**, **dd-site-speed** — invoked in v1  
- **dd-site-compare** — required installed; not invoked in v1  
