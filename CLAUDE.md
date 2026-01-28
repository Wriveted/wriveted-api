# CLAUDE.md

## Engineering Principles

- **Test-Design-Code Alignment**: When tests fail, analyze the **design intent** (documentation, API contracts), **current implementation**, and **test expectations** to determine the correct path forward. Don't take the easy path of changing tests to match broken implementations. Instead, compare all three sources to determine what the correct behavior should be and fix accordingly.
- **REST API Consistency**: DELETE operations should return appropriate HTTP status codes per REST conventions (typically 204 No Content for successful deletions with no response body, or 200 OK if returning meaningful response data).
- **Declarative Database Infrastructure**: Use `alembic_utils` with Python-defined functions and triggers in `app/db/functions.py` and `app/db/triggers.py` for version-controlled, type-safe database logic.

Only Professional Comments Should Be used.
- Remove task-focused comments like "OLD import removed"
- Remove "NEW:" markers etc.
- Focus on why not what
- Remove comments that just restate the code

## Development Commands

### Dependencies
- **Install dependencies**: `poetry install`
- **Add new dependency**: `poetry add <package_name>`
- **Update dependencies**: `poetry update`

### Database Operations
- **Apply migrations**: `poetry run alembic upgrade head`
- **Create new migration**: `poetry run alembic revision --autogenerate -m "Description"`
- **Set database connection**: `export SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@localhost/postgres`

### Testing
- **Run all tests**: `bash scripts/start-tests.sh` or `poetry run pytest -v app/tests`
- **Run integration tests in Docker**: `bash scripts/integration-tests.sh` (recommended - provides proper environment)
- **Run integration tests locally**: Direct pytest may have async fixture issues, use Docker instead
- **Single test**: `poetry run pytest -v app/tests/integration/test_specific.py::test_function`

**Important Note**: Integration tests should be run using `bash scripts/integration-tests.sh` which provides the proper Docker environment with database migrations and all dependencies. Running integration tests directly with pytest may encounter async fixture configuration issues. Ensure no conflicting postgres containers are running on port 5432.

### Code Quality
- **Lint code**: `poetry run ruff check`
- **Fix linting issues**: `poetry run ruff check --fix`
- **Pre-commit hooks**: `poetry run pre-commit run --all-files`

### Local Development
- **Start with Docker Compose**: `docker compose up -d`
- **Run API directly**: `uvicorn app.main:app --reload`
- **Run internal API**: `gunicorn --workers=1 --worker-class=uvicorn.workers.UvicornWorker app.internal_api:internal_app`

### Seed Test Data (Admin UI / Chatflows)
Use the declarative fixture + seeder to create a consistent school, users, books, CMS content, and flows.

**Config**: `scripts/fixtures/admin-ui-seed.json`  
**Seeder**: `scripts/seed_admin_ui_data.py`

```bash
# Seed data and print JWTs for each user role
docker compose run --rm --entrypoint python \
  -v "$PWD/scripts:/app/scripts" \
  api /app/scripts/seed_admin_ui_data.py --emit-tokens --tokens-format json
```

### Configuring Local User Permissions
To grant admin access for testing features like the CMS/chatflow builder in the admin UI:

```sql
-- Update user type to WRIVETED admin
UPDATE users SET type = 'WRIVETED' WHERE email = 'your-email@example.com';

-- Create corresponding wriveted_admins record (required for joined-table inheritance)
INSERT INTO wriveted_admins (id)
SELECT id FROM users WHERE email = 'your-email@example.com';
```

Or via Python:
```python
export SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@localhost/postgres
poetry run python -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:password@localhost/postgres')
with engine.begin() as conn:
    result = conn.execute(text(\"SELECT id FROM users WHERE email = 'your-email@example.com'\"))
    user_id = result.fetchone()[0]
    conn.execute(text(f\"UPDATE users SET type = 'WRIVETED' WHERE id = '{user_id}'\"))
    conn.execute(text(f\"INSERT INTO wriveted_admins (id) VALUES ('{user_id}')\"))
"
```

After updating, log out and back in to the admin UI to get a new JWT with updated permissions.

## Declarative Database Pattern

### Overview
All PostgreSQL functions, triggers, and complex database objects are defined declaratively in Python using `alembic_utils`. This ensures version control, type safety, and maintainability.

### Key Files
- **`app/db/functions.py`**: PostgreSQL function definitions
- **`app/db/triggers.py`**: Trigger definitions that reference functions
- **Migrations**: Use `op.create_entity()` and `op.drop_entity()` for declarative objects

### Example Pattern
```python
# In app/db/functions.py
from alembic_utils.pg_function import PGFunction

my_function = PGFunction(
    schema="public",
    signature="my_function_name()",
    definition="returns trigger LANGUAGE plpgsql AS $$ ... $$"
)

# In app/db/triggers.py
from alembic_utils.pg_trigger import PGTrigger
from app.db.functions import my_function

my_trigger = PGTrigger(
    schema="public",
    signature="trg_my_trigger",
    on_entity="public.my_table",
    definition=f"... EXECUTE FUNCTION {my_function.signature}"
)

# In migration
def upgrade():
    op.create_entity(my_function)
    op.create_entity(my_trigger)
```

### Benefits
- **Single Source of Truth**: Database logic defined once in Python
- **Version Control**: All changes tracked in git
- **Type Safety**: Python validates syntax before deployment
- **Migration Safety**: Automatic up/down migration generation
- **IDE Support**: Full Python tooling available

## Architecture Overview

### Dual API Structure
The application consists of two separate FastAPI applications:
- **Public API** (`app.main:app`): External-facing REST API with authentication/authorization
- **Internal API** (`app.internal_api:internal_app`): Background task processing, webhook handling

### Database Architecture
- **ORM**: SQLAlchemy 2.0 with async support (asyncpg driver)
- **Migrations**: Alembic for schema management
- **Base Class**: Custom `Base` class with auto-generated table names
- **User Model**: Uses joined-table inheritance for different user types (Student, Educator, Parent, etc.)

### Key Domain Models
- **Users**: Hierarchical user system (User → Student/Educator/Parent/etc.)
- **Books**: Work → Edition → CollectionItem relationship
- **Schools**: Schools contain ClassGroups and Users
- **Collections**: Library collections with items and activity tracking
- **Labels**: AI-powered book categorization system via LabelSets

### Authentication & Authorization
- **Firebase Authentication**: Users authenticate via Firebase, exchange token for Wriveted JWT
- **RBAC**: Role-based access control with principals (user-xyz, school-1)
- **Service Accounts**: Long-lived tokens for LMS integrations

### Configuration
- **Settings**: Pydantic-based configuration in `app.config.py`
- **Environment Variables**: Database connection, API keys, feature flags
- **GCP Integration**: Cloud SQL, Cloud Storage, Cloud Tasks

### API Structure
- **External API**: Routes in `app/api/` with dependencies in `app/api/dependencies/`
- **Schemas**: Pydantic models for request/response in `app/schemas/`
- **CRUD Operations**: Database operations in `app/crud/` (legacy pattern)
- **Repositories**: Domain-focused data access interfaces in `app/repositories/`
- **Services**: Business logic in `app/services/`


## Development Notes

### Database Connection Patterns
- Always use environment variable `SQLALCHEMY_DATABASE_URI` for connections
- Local development: `postgresql://postgres:password@localhost/postgres`

### Testing Environment
- Integration tests use Docker Compose with real PostgreSQL
- Tests are in `app/tests/integration/` and `app/tests/unit/`
- Test configuration in `conftest.py` files

### Code Style
- Ruff for linting (configured in `pyproject.toml`)

### Migration Workflow
1. Modify SQLAlchemy models in `app/models/`
2. Add imports to `app/models/__init__.py`
3. Generate migration: `poetry run alembic revision --autogenerate -m "Description"`
4. Review generated migration file manually. Try ensure models are source of truth.
5. Apply: `poetry run alembic upgrade head`

## Integration Test Insights & Patterns

### Data Access Patterns  
- **Legacy CRUD Pattern**: Some classes still use generic `CRUDBase` (being phased out)
- **Modern Repository Pattern**: New domain-focused repositories in `app/repositories/`
- **Service Layer**: Business logic extracted from data access layer to `app/services/`
- **Async Operations**: All new services use proper async/await patterns consistently
- **Field Validation**: Pydantic schemas use consistent field names between database and API

### API Endpoint Patterns
- **Authentication**: Many endpoints require service account or admin authentication
- **Validation Endpoints**: Custom endpoints like `/flows/{id}/validate` for business logic validation
- **Query Parameters**: Support filtering, searching, pagination consistently across list endpoints

### Testing Best Practices
- **Docker Environment**: Always use `bash scripts/integration-tests.sh` for proper database setup
- **Test Isolation**: Clean up test data in fixtures to prevent test interference
- **Async Context**: Be careful with SQLAlchemy async operations

### Performance Considerations
- **Bulk Operations**: Implement batch create/update operations for efficiency
- **Query Optimization**: Full-text search uses PostgreSQL tsvector and GIN indexes

### Common Pitfalls
- **Status Code Expectations**: Verify actual API behavior vs REST conventions
- **Async/Await Consistency**: Ensure all database operations use proper async patterns
