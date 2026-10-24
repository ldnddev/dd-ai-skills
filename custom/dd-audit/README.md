# dd-audit

Orchestrator for a **primary-URL site audit**. Requires four sibling plugins. v1 **runs** crawl + SEO + speed into one nested folder and writes a cover dashboard that links to each child report.

This plugin does not reimplement those audits.

## Required plugins

Install all four before `/dd-audit`:

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-crawl@dd-skills
/plugin install dd-seo@dd-skills
/plugin install dd-site-speed@dd-skills
/plugin install dd-site-compare@dd-skills
```

Codex (from this repo):

```bash
bash custom/dd-crawl-audit/install.sh
bash custom/dd-seo-audit/install.sh
bash custom/dd-site-speed-audit/install.sh
bash custom/dd-site-compare-audit/install.sh
bash custom/dd-audit/install.sh
```

`dd-site-compare` must be installed in v1 even though it is not invoked (compare needs peer URLs).

## Usage

```bash
# Check the four skills are installed
python3 scripts/run_audit.py --preflight

# Create web/<domain>-site-audit-YYYY-MM-DD/ + plan.json
python3 scripts/run_audit.py https://www.example.com

# After child skills have written crawl/, seo/, speed/:
python3 scripts/run_audit.py --assemble web/example.com-site-audit-YYYY-MM-DD
```

The agent skill (`skills/dd-audit/SKILL.md`) is what runs crawl, SEO, and speed **in full** into those subfolders. `run_audit.py` never shells out to them.

## Output

```
web/<domain>-site-audit-YYYY-MM-DD/
├── index.html
├── data.json
├── plan.json
├── crawl/
├── seo/
└── speed/
```

## Tests

```bash
python3 scripts/test_audit.py
```
