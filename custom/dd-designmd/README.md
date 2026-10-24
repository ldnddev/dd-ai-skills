# dd-designmd

Extract a **semantic design system** from a website URL as an Expert Design System Lead.

## Install

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-designmd@dd-skills
```

Codex:

```bash
bash custom/dd-designmd/install.sh
```

## Usage

```bash
# Files in CWD
python3 scripts/run_designmd.py https://www.ldnddev.com

# Client bundle + Framework dashboard
python3 scripts/run_designmd.py https://www.ldnddev.com --web
```

**CWD mode** writes:

- `ldnddev.com-design.md`
- `ldnddev.com-tokens.json`
- `ldnddev.com-tokens.css`
- `ldnddev.com-designmd-evidence.json`

**`--web` mode** writes `web/ldnddev.com-designmd-YYYY-MM-DD/`:

- `index.html` — light Framework dashboard (swatches, tokens, Framework map, downloads); links webroot `/assets/`
- same design/token/evidence files as above

### Options

| Flag | Meaning |
|------|---------|
| `--web` | Bundle under `web/<domain>-designmd-<date>/` with dashboard |
| `--dashboard` | Write `index.html` into `--output-dir` (implied by `--web`) |
| `--force` | Overwrite existing outputs |
| `--max-extra N` | Nav expand cap when single URL (default 8) |
| `--deep` | Request deep evidence mode (optional Playwright later) |
| `--urls-file path` | Multi-URL list |
| `--output-dir path` | Output directory (default `.`; ignored with `--web`) |

## Rules

- Evidence-bound tokens only  
- No invented brand guidelines  
- No rebrand recommendations  
- No a11y/SEO scores  
- No silent overwrite  

## Skill body

See [`skills/dd-designmd/SKILL.md`](skills/dd-designmd/SKILL.md).
