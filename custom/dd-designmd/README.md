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
python3 scripts/run_designmd.py https://www.ldnddev.com
```

Writes in CWD:

- `ldnddev.com-design.md`
- `ldnddev.com-tokens.json`
- `ldnddev.com-tokens.css`
- `ldnddev.com-designmd-evidence.json`

### Options

| Flag | Meaning |
|------|---------|
| `--force` | Overwrite existing outputs |
| `--max-extra N` | Nav expand cap when single URL (default 8) |
| `--deep` | Request deep evidence mode (optional Playwright later) |
| `--urls-file path` | Multi-URL list |
| `--output-dir path` | Output directory (default `.`) |

## Rules

- Evidence-bound tokens only  
- No invented brand guidelines  
- No rebrand recommendations  
- No a11y/SEO scores  
- No silent overwrite  

## Skill body

See [`skills/dd-designmd/SKILL.md`](skills/dd-designmd/SKILL.md).
