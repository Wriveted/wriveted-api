# Test Credentials and Authentication Setup

This document describes how to set up test data and authentication tokens for development and testing of the Wriveted API.

## Recommended Approach: Seed Script

The primary way to set up test data is the declarative seed script, which creates a school, users (multiple roles), books, CMS content, chatflows, and themes from a JSON fixture.

**Config**: `scripts/fixtures/admin-ui-seed.json`
**Script**: `scripts/seed_admin_ui_data.py`

```bash
# 1. Start the stack
docker compose up -d --build

# 2. Apply migrations
docker compose run --rm migration

# 3. Seed data and print JWTs for each user role
docker compose run --rm --entrypoint python \
  -v "$PWD/scripts:/app/scripts" \
  api /app/scripts/seed_admin_ui_data.py --emit-tokens --tokens-format json
```

The seed script is **idempotent** -- safe to run multiple times. It outputs JWTs for each seeded user that you can use immediately.

### Seeded Test Data

#### Test School
- **Wriveted ID**: `84a5ade6-7f75-4155-831a-1d84c6256fc3`
- **Name**: Admin UI Test School
- **Country**: NZ (New Zealand)

#### Test Users

| Role | Email | Capabilities |
|------|-------|-------------|
| Wriveted Admin | `wriveted-admin@local.test` | Global admin, CMS flow management |
| School Admin | `school-admin@local.test` | School-specific operations, theme management |
| Educator | `educator@local.test` | Teaching-related operations |
| Parent | `parent@local.test` | Parent portal access |
| Student | `student@local.test` | Student experience, chatflows |
| Public Reader | `public-reader@local.test` | Public-facing features |

The `--emit-tokens` flag prints ready-to-use Bearer tokens for each user. Use `--tokens-format json` for machine-readable output.

## Authentication Examples

```bash
# List all CMS flows (requires admin)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     http://localhost:8000/v1/cms/flows

# List themes (school admin)
curl -H "Authorization: Bearer $SCHOOL_ADMIN_TOKEN" \
     http://localhost:8000/v1/cms/themes

# Get school details
curl -H "Authorization: Bearer $SCHOOL_ADMIN_TOKEN" \
     http://localhost:8000/v1/school/84a5ade6-7f75-4155-831a-1d84c6256fc3
```

### HTTPie Examples

```bash
http GET http://localhost:8000/v1/cms/flows \
    "Authorization:Bearer $ADMIN_TOKEN"

http GET http://localhost:8000/v1/cms/themes \
    "Authorization:Bearer $SCHOOL_ADMIN_TOKEN"
```

## Verifying Tokens

```bash
# Test admin token
curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     http://localhost:8000/v1/cms/flows | head -20

# Should return HTTP 200 and JSON data

# Test invalid token
curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer invalid_token" \
     http://localhost:8000/v1/cms/flows

# Should return HTTP 401 Unauthorized
```

## Environment Variables

For running the API or tests outside Docker, set these environment variables. The `scripts/setup-test-env.sh` script sets all of them:

```bash
source scripts/setup-test-env.sh
```

Or set them manually:

```bash
export POSTGRESQL_PASSWORD=password
export SECRET_KEY=CHrUJmNw1haKVSorf3ooW-D6eRooePyo-V8II--We78
export SENDGRID_API_KEY=unused-key-set-for-testing
export SHOPIFY_HMAC_SECRET=unused-key-for-testing
export SLACK_BOT_TOKEN=unused-key-for-testing
export OPENAI_API_KEY=unused-test-key-for-testing
export SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@localhost/postgres
export SQLALCHEMY_ASYNC_URI=postgresql+asyncpg://postgres:password@localhost/postgres
```

These are automatically set inside Docker containers via `docker-compose.yml`.

## Troubleshooting

### Database Connection Issues
```bash
# Check database is running
docker compose ps

# Restart database
docker compose restart db

# Check connection
psql postgresql://postgres:password@localhost/postgres -c "SELECT 1"
```

### Token Validation Issues
- Ensure `SECRET_KEY` matches between token generation and API server
- Check token hasn't expired
- Verify user/service account exists in database

### Permission Issues
- Wriveted Admin token has highest privileges
- School Admin token limited to school-specific resources
- Service accounts have specific scopes based on type

## Alternative: Legacy E2E Setup

The `setup_test_environment.py` script in the project root is an older, minimal setup used for Playwright E2E testing. It creates a different test school (ID `784039ba-7eda-406d-9058-efe65f62f034`) with fewer user roles. **Prefer the seed script above for most development work.**

If you need the legacy setup:

```bash
poetry run python3 setup_test_environment.py
```

Related legacy scripts:
- `get_user_token.py` -- Quick user token generator
- `get_service_token.py` -- Quick service token generator
- `scripts/get_auth_token.py` -- Legacy token generator (hardcoded user)

## API Documentation

For full API documentation, see:
- OpenAPI docs: http://localhost:8000/v1/docs
- ReDoc: http://localhost:8000/v1/redoc
