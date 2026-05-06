# dd-framework — ldnddev Framework Component Skill

Guides AI agents to add, configure, and update pages built on the ldnddev Framework component system. Covers component contracts, parameters, accessibility (WCAG AA), and common page templates.

## Install — Claude Code plugin

```bash
/plugin marketplace add jlyvers/dd-ai-skills
/plugin install dd-framework@dd-skills
```

No deps. Loads instantly.

## Install — Codex skill

```bash
bash install.sh
```

Installs to `${CODEX_HOME:-$HOME/.codex}/skills/dd-framework/`.

## Trigger phrases

- "add a dd-hero with..."
- "build a 3-column dd-card grid"
- "wrap this in a dd-section"
- "update the hero on /about"

## Components covered

`dd-hero`, `dd-card`, `dd-section`, `dd-alert`, `dd-banner`, `dd-tabs`, `dd-accordion`, `dd-cta`, `dd-modal`, `dd-slider`, `dd-spacer`, `dd-timeline`.

## Layout

```
dd-framework/
├── .claude-plugin/plugin.json
├── install.sh
└── skills/dd-framework/
    ├── SKILL.md
    ├── references/
    │   ├── Agent-UI-Colors.md
    │   └── Agent-UI-Theme-Builder.md
    └── assets/components/
```

## Color system (WCAG AA)

- Primary `#88d9f7`, Secondary `#ffca76`, Tertiary `#f98971`, Support `#46be8c`
- Light text `#1c1e21` / `#5a5f66` · Dark text `#f5f6f7` / `#9ea3aa`
- Interactive contrast: 4.5:1 normal text, 3:1 large text. 2px focus outline minimum.

## Build commands (run via `lando`)

```bash
lando grunt build       # full build
lando grunt dev         # dev build with watch
lando grunt sync        # sync assets to web/
```
