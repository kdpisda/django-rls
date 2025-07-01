# GitHub Actions Workflows

This directory contains simplified CI/CD workflows for django-rls.

## Workflows

### ci.yml - Main CI Pipeline
- **Triggers**: Push to main/develop, PRs to main
- **Jobs**:
  - **test**: Runs PostgreSQL tests on Python 3.11-3.12 × Django 5.1-5.2 (4 combinations)
  - **sqlite-test**: Single smoke test with SQLite
  - **lint**: Code quality checks (informational only, won't fail builds)
- **Total test runs**: 5 (4 PostgreSQL + 1 SQLite)

### release.yml - PyPI Release
- **Triggers**: Manual dispatch or version tags
- **Jobs**:
  - **sanity-check**: Quick import test (no full test suite)
  - **bump-version**: Updates version numbers
  - **build**: Creates distribution packages
  - **publish-testpypi**: Publishes to TestPyPI
  - **test-installation**: Verifies installation from TestPyPI
  - **publish-pypi**: Publishes to PyPI
  - **create-release**: Creates GitHub release

### deploy-docs.yml - Documentation
- **Triggers**: Push to main or manual
- **Deploys documentation to GitHub Pages**

### docs-monitor.yml - Documentation Health
- **Triggers**: Daily at 2 AM UTC or manual
- **Checks if documentation site is accessible**

## Design Principles

1. **No redundant testing**: Tests run in CI, not repeated in release
2. **Minimal version matrix**: Only test supported Python/Django combinations
3. **Fast feedback**: PostgreSQL-only tests (except one SQLite smoke test)
4. **Non-blocking quality checks**: Linting and coverage are informational
5. **Simple configuration**: Consistent environment variables and caching