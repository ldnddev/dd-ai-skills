# Lando Reference (Pantheon recipe, local-first workflow)

When `.lando.yml` has `recipe: pantheon`, run updates locally first. All CMS commands get the `lando` prefix and run inside the app container. The recipe bundles terminus, so `lando terminus <cmd>` works without a host install.

## Reading .lando.yml

```yaml
name: my-site
recipe: pantheon
config:
  framework: drupal        # drupal | wordpress
  site: my-pantheon-site   # terminus site name
  id: <uuid>               # pantheon site UUID
```

## Preflight

```bash
lando list                 # app running?
lando start                # if not
lando info                 # local site URL for verification
```

## Command wrappers

| Hosted command | Local Lando equivalent |
|---|---|
| `terminus remote:drush <site>.<env> -- <cmd>` | `lando drush <cmd>` |
| `terminus remote:wp <site>.<env> -- <cmd>` | `lando wp <cmd>` |
| `composer <cmd>` | `lando composer <cmd>` |
| `terminus <cmd>` | `lando terminus <cmd>` |
| mysql | `lando mysql` / `lando db-import` / `lando db-export` |

Run composer inside Lando, not on the host — the container's PHP matches Pantheon's, so dependency resolution is accurate.

## Local-first update flow

1. **Sync down**: `lando pull --code=none --database=live --files=live` (use `--files=none` if files are huge and irrelevant). Confirm with the user first — this overwrites the local DB.
2. **Update locally** with `lando`-prefixed commands from the CMS reference.
3. **Verify locally**: load the `lando info` URL; `lando drush core:requirements --severity=2` or `lando wp core verify-checksums`; check `lando logs -s appserver`.
4. **Commit** composer.json/lock, plugin files, exported config.
5. **Deploy via git push** (see the git-mode flow in SKILL.md). `lando push` exists, but for git-mode sites push via git — and never push the local database up.
6. **Run post-deploy steps on the hosted env** (`terminus remote:drush <site>.dev -- updb -y` etc.) — deploying code does not run DB updates unless Quicksilver hooks do; check first.

## Safety notes

- **Never `lando push --database`** toward a hosted environment unless the user explicitly asks and confirms — pushing a local DB over live is the most destructive command in this skill.
- `lando destroy` deletes the local DB — don't suggest it casually.
- If `lando pull` fails auth: `lando terminus auth:login --machine-token=<token>` inside the app.
