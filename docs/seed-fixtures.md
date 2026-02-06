# Seed Fixtures for CMS/Chatflow Testing

This repo now includes a declarative seed workflow for repeatable local UI testing (admin UI, chatflow builder, CMS screens).

## Why this approach
- **Repeatable**: One JSON file describes the school, users, books, booklists, CMS content, and flows.
- **Idempotent**: Re-running the script updates/creates data without duplicate records.
- **UI-friendly**: Gives consistent demo data for admin UI and frontend testing.

## What to use
- **Config**: `scripts/fixtures/admin-ui-seed.json`
- **Seeder**: `scripts/seed_admin_ui_data.py`

## Running locally
With docker-compose running the API:

```bash
# Seed data + print tokens

docker compose run --rm --entrypoint python \
  -v "$PWD/scripts:/app/scripts" \
  api /app/scripts/seed_admin_ui_data.py --emit-tokens --tokens-format json
```

Tokens are printed for each seeded user role (school admin, educator, student, etc.).

## Consolidating flow scripts into fixtures
**Recommendation:** use fixtures for local/dev and integration testing, while keeping the API scripts for curated/staging content.

- Keep `scripts/create_*_flow.py` for **curated flows** and explicit API creation.
- Use `scripts/fixtures/*.json` for **repeatable local/test setup**.

If a flow needs to be present in local UI testing, add it to the fixture JSON under `flows` and use the seeder. This keeps flow JSON in one place and avoids multiple scripts diverging over time.

## External flow files

For complex flows, the seed config supports a `flow_file` key that loads the flow definition from a separate JSON file in `scripts/fixtures/`:

```json
{
  "flows": [
    {
      "flow_file": "huey-bookbot-flow.json",
      "theme_seed_key": "huey-bookbot-theme"
    }
  ]
}
```

The external JSON file should contain the full flow config including `seed_key`, `name`, `entry_node_id`, and `flow_data` with nodes and connections. The seeder merges any additional keys (like `theme_seed_key`) from the parent entry.

## About JSON fixtures and `.gitignore`
`.gitignore` currently ignores `*.json`, so fixture JSON files must be added with:

```bash
git add -f scripts/fixtures/admin-ui-seed.json
```

If we decide to expand fixtures, consider updating `.gitignore` to whitelist `scripts/fixtures/*.json`.

