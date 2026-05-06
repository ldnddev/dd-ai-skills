# Assets

This folder holds brand assets used by the dashboard template.

Included:

- `agency-logo.svg` — placeholder logo for the dashboard template

If you want your real agency branding:

1. Replace `agency-logo.svg` with your real logo file, or add a different asset here.
2. Update `templates/brand.json`:

```json
{
  "agency_logo": "assets/your-logo-file.ext"
}
```

Keep paths relative to the installed skill root so generated dashboards can reference them consistently.
