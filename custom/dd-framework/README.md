# dd-framework — ldnddev Framework Component Skill

Canonical component contracts (params, BEM classes, WCAG 2.2 AA accessibility rules, design tokens) plus a Python helper CLI for the ldnddev Framework component system. Consumed by AI agents and other skills (e.g. `dd-blogs`, page-builders) to author static HTML, Drupal Twig, or WordPress block markup.

**Scope:** reference + validation, not render. Drupal renders its own Twig, WordPress renders its own PHP/blocks, static sites copy markup verbatim — each consumer renders natively. dd-framework supplies the contract everyone agrees on.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-framework@dd-skills
```

## Install — Codex / Cursor skill

```bash
bash install.sh
```

See [root README](../../README.md#codex-install-legacy) for context.

## Helper CLI

```bash
python3 scripts/dd_framework_helper.py list                          # enumerate
python3 scripts/dd_framework_helper.py get dd-hero                   # spec + html + params
python3 scripts/dd_framework_helper.py get dd-hero --section spec
python3 scripts/dd_framework_helper.py validate page.html            # strict (exit 1 on error)
python3 scripts/dd_framework_helper.py validate page.html --warn     # advisory (exit 0)
```

JSON output by default. `--human` flag for prose.

Deps: `beautifulsoup4` (validate only). `pip install -r skills/dd-framework/scripts/requirements.txt`.

## Trigger phrases

- "add a dd-hero with..."
- "build a 3-column dd-card grid"
- "wrap this in a dd-section"
- "validate this page against dd-framework"

## Components (17)

`dd-accordion`, `dd-alert`, `dd-alternating`, `dd-banner`, `dd-blockquote`, `dd-card`, `dd-cookie-consent`, `dd-cta`, `dd-filmstrip`, `dd-hero`, `dd-milestones`, `dd-modal`, `dd-section`, `dd-slider`, `dd-spacer`, `dd-tabs`, `dd-timeline`.

Per-component contract: `skills/dd-framework/assets/components/dd-{name}.spec.md`.
Static HTML reference: `skills/dd-framework/assets/components/dd-{name}.html`.
Manifest index: `skills/dd-framework/assets/components.manifest.json`.

## Layout

```
dd-framework/
├── .claude-plugin/plugin.json
├── install.sh
├── README.md                             ← you are here
└── skills/dd-framework/
    ├── SKILL.md                          ← full agent guidance
    ├── references/
    │   ├── Agent-UI-Colors.md
    │   └── Agent-UI-Theme-Builder.md
    ├── scripts/
    │   ├── dd_framework_helper.py
    │   ├── test_dd_framework_helper.py
    │   └── requirements.txt
    └── assets/
        ├── components.manifest.json
        └── components/
            ├── dd-{name}.html
            └── dd-{name}.spec.md
```

## Cross-skill consumption

Three options for downstream skills:

1. **Skill tool invocation** — load `dd-framework` and follow `SKILL.md`.
2. **Direct file read** — parse `components.manifest.json` + read `dd-{name}.spec.md` files.
3. **Helper shell-out** — call `dd_framework_helper.py` and pipe its JSON output.

`dd-blogs` uses option 3 for component discovery and validation of emitted blog body HTML.

## Color system (WCAG AA)

| Role | Base | Light text contrast | Dark text contrast |
|---|---|---|---|
| Primary | `#88d9f7` | ~10:1 with `#1c1e21` | varies |
| Secondary | `#ffca76` | ~10:1 with `#1c1e21` | varies |
| Tertiary | `#f98971` | ~7:1 with `#1c1e21` | varies |
| Support | `#46be8c` | ~5:1 with `#1c1e21` | varies |

Full token map: `skills/dd-framework/references/Agent-UI-Colors.md`. Interactive targets ≥ 24×24 CSS px (2.5.8). 2px focus outline minimum.

## Tests

```bash
cd skills/dd-framework/scripts
python3 -m pytest test_dd_framework_helper.py -v
```

39 cases cover manifest integrity, `list`/`get` for each of 17 components, section filters, unknown-component handling, and validate scenarios.

## Build commands (consumer-side)

dd-framework ships no build artifacts. When working inside an ldnddev site that uses Lando:

```bash
lando grunt build       # full build
lando grunt dev         # dev build with watch
lando grunt sync        # sync assets to web/
```
