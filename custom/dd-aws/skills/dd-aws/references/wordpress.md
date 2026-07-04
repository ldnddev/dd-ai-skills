# WordPress Reference (wp-cli)

On Pantheon, wrap every command: `terminus remote:wp <site>.<env> -- <command>`. On AWS, run `wp <command>` in the docroot (add `--path=<docroot>` if running from elsewhere).

## Status checks (read-only, no backup needed)

```bash
wp core version
wp core check-update
wp plugin list --update=available --format=table
wp theme list --update=available
wp core verify-checksums
```

## Update sequence

Order matters: plugins → themes → core. Update plugins individually when possible so a failure is attributable:

```bash
wp plugin update <slug>            # one at a time for anything critical
wp plugin update --all             # acceptable for routine minor updates
wp theme update --all
wp core update
wp core update-db                  # ALWAYS after core update
wp cache flush
```

After each batch: `wp plugin list --format=table` to confirm versions, then verify the site loads.

## Gotchas

- **Premium/licensed plugins** (ACF Pro, Gravity Forms, etc.) often can't update via wp-cli without a license key configured — flag these to the user rather than silently skipping.
- **Composer-managed WP**: if the site has a root `composer.json` managing plugins (check first), update via composer + commit, NOT `wp plugin update` — direct updates will be reverted or cause drift.
- **Pantheon specifically**: dev must be in SFTP mode for `wp plugin update` to write files on the server. For git-mode sites, the correct flow is: update in the local environment (`lando wp plugin update <slug>`), verify locally, then `git add` the changed plugin directories and commit/push. Never update plugins directly on a git-mode server.
- **Multisite**: add `--network` to relevant commands; run `wp core update-db --network`.

## Database/content ops

```bash
wp db export backup-$(date +%Y%m%d).sql      # backup (AWS; Pantheon uses terminus backup)
wp search-replace 'https://old.com' 'https://new.com' --dry-run   # ALWAYS dry-run first
wp search-replace 'https://old.com' 'https://new.com' --all-tables
wp user list / wp post list                   # content inspection
```

`search-replace` is serialization-safe — never do this with raw SQL instead.

## Verification after updates

```bash
wp core verify-checksums
wp plugin status
curl -sI <homepage> | head -1
# spot-check /wp-admin loads and one key template page
```
