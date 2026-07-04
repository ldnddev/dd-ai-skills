# Lando Reference (non-Pantheon recipes, local-first workflow)

When `.lando.yml` has a recipe like `drupal10`, `drupal11`, `wordpress`, `lamp`, or `lemp`, Lando is local-only — hosting and deployment details come from `sites.yml`. All CMS commands get the `lando` prefix and run inside the app container.

## Reading .lando.yml

```yaml
name: my-site
recipe: drupal10           # identifies the CMS; drupalN → drupal, wordpress → wordpress
config:
  webroot: web
  php: '8.2'
```

`lamp`/`lemp` recipes don't identify the CMS — check for `composer.json` requiring `drupal/core` vs a `wp-content` directory, or ask.

## Preflight

```bash
lando list                 # app running?
lando start                # if not
lando info                 # local site URL for verification
```

## Command wrappers

| Hosted command | Local Lando equivalent |
|---|---|
| `drush <cmd>` | `lando drush <cmd>` |
| `wp <cmd>` | `lando wp <cmd>` |
| `composer <cmd>` | `lando composer <cmd>` |
| mysql | `lando mysql` / `lando db-import <file>` / `lando db-export` |

Run composer inside Lando, not on the host — match the container PHP to the server for accurate dependency resolution (compare `config.php` to the EC2 PHP version; flag mismatches).

## Local-first update flow

1. **Sync down**: get a fresh dump from the hosted environment (see "Getting a DB dump to your local machine" in SKILL.md), then `lando db-import <dump-file>`. Confirm with the user first — this overwrites the local DB.
2. **Update locally** with `lando`-prefixed commands from the CMS reference.
3. **Verify locally**: load the `lando info` URL; `lando drush core:requirements --severity=2` or `lando wp core verify-checksums`; check `lando logs -s appserver`.
4. **Commit** composer.json/lock, plugin files, exported config.
5. **Deploy** per the site's access method (pipeline PR flow or SSH deploy — see SKILL.md).
6. **Run post-deploy steps on the hosted env** (updb/cim/cr or update-db/cache flush) — deploying code does not run DB updates unless the pipeline does; check the pipeline config before double-running.

## Safety notes

- Never import a local database to a hosted environment unless the user explicitly asks and confirms — overwriting a hosted DB with local data is the most destructive operation in this skill.
- `lando destroy` deletes the local DB — don't suggest it casually.
