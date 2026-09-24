# Local Testing Guide for Django RLS

## Prerequisites

1. **Docker** with Compose v2 (`docker compose`)
2. **Poetry** for Python dependencies

```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry install
```

## Quick start (recommended)

`make test` starts PostgreSQL via docker compose and runs the full suite against it:

```bash
make test
```

Under the hood this runs `scripts/run-tests.sh`, which:

1. `docker compose up -d --wait postgres`
2. Ensures `rls_test_user` exists
3. Runs `pytest` with `USE_POSTGRESQL=true` against `localhost:5433`

### Other test commands

```bash
make test-cov        # coverage report
make test-security   # security regression suite
make ci-local        # lint + type-check + full tests (same Postgres flow)
make test-local      # pytest only — you must provide Postgres yourself
```

### Run the script directly

```bash
./scripts/run-tests.sh
./scripts/run-tests.sh tests/security -m security -v
```

## Docker Compose details

PostgreSQL 17 runs in Docker on **host port 5433** (avoids conflicting with a local Postgres on 5432):

```bash
make docker-up      # start and wait for healthy Postgres
make docker-down    # stop containers
make docker-reset   # delete volume and recreate
make docker-logs    # tail Postgres logs
make db-shell       # psql as postgres superuser
```

The test user `rls_test_user` / `testpass` is created automatically via `docker/postgres/init/` on first volume creation. `scripts/run-tests.sh` also creates the role if the volume already existed.

### In-network test runner (optional)

Run pytest inside Compose, connected to the `postgres` service on port 5432:

```bash
docker compose --profile test run --rm test
```

## Environment variables

Used by `scripts/run-tests.sh` and CI:

| Variable | Local default | CI value |
|----------|---------------|----------|
| `USE_POSTGRESQL` | `true` | `true` |
| `DB_HOST` | `localhost` | `localhost` |
| `DB_PORT` | `5433` | `5432` |
| `DB_NAME` | `postgres` | `postgres` |
| `DB_USER` | `rls_test_user` | `rls_test_user` |
| `DB_PASSWORD` | `testpass` | `testpass` |

## Without Docker

Install PostgreSQL locally, create the test user and database, then:

```bash
export USE_POSTGRESQL=true
export DB_HOST=localhost
export DB_PORT=5432   # or your port
export DB_USER=rls_test_user
export DB_PASSWORD=testpass
poetry run pytest
```

## Testing best practices

1. **Always test with PostgreSQL** — SQLite does not enforce RLS.
2. **Use `make test`** before opening a PR — same real-Postgres path as CI.
3. **Use `system_rls_context()`** in tests when switching identity (1.0.0+).
4. **Do not mock `django_rls.context.connection`** for security tests — assert behavior via `get_rls_context()` on a live database.

## Troubleshooting

```bash
# Containers running?
docker compose ps

# Postgres healthy?
docker compose exec postgres pg_isready -U postgres

# Stale test DB connections
docker compose restart postgres

# Nuclear reset
make docker-reset
```

### `database "test_django_rls" is being accessed by other users`

Usually leftover connections from threaded tests. Restart Postgres or run:

```bash
docker compose exec postgres psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'test_django_rls';"
```

## Continuous Integration

GitHub Actions runs the same full `pytest` tree against a **real PostgreSQL 17 service** on every PR to `main`:

- Python 3.11 and 3.12
- Django 5.1, 5.2, and 6.0
- `USE_POSTGRESQL=true`, `DB_PORT=5432`

Local `make test` and CI exercise the same code paths; only the host port differs (5433 vs 5432).