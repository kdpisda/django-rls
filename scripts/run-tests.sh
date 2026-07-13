#!/usr/bin/env bash
# Start PostgreSQL via docker compose and run the test suite against it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop or the Docker Engine CLI." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose (v2) is required." >&2
  exit 1
fi

echo "Starting PostgreSQL (docker compose)..."
docker compose up -d --wait postgres

# Ensure the test role exists (init scripts only run on first volume creation).
docker compose exec -T postgres psql -U postgres -tc \
  "SELECT 1 FROM pg_roles WHERE rolname = 'rls_test_user'" | grep -q 1 \
  || docker compose exec -T postgres psql -U postgres -c \
  "CREATE USER rls_test_user WITH PASSWORD 'testpass' CREATEDB;"

export USE_POSTGRESQL="${USE_POSTGRESQL:-true}"
export DB_NAME="${DB_NAME:-postgres}"
export DB_USER="${DB_USER:-rls_test_user}"
export DB_PASSWORD="${DB_PASSWORD:-testpass}"
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5433}"

echo "Running tests against PostgreSQL at ${DB_HOST}:${DB_PORT}..."
exec poetry run pytest "$@"