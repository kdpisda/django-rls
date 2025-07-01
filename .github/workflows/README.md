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

### release.yml - Release & PyPI Publishing
- **Triggers**: Manual dispatch only
- **Inputs**:
  - **version_bump**: patch, minor, or major
  - **publish_to_pypi**: Whether to publish to PyPI (default: true)
- **Single job that**:
  1. Bumps version
  2. Runs tests
  3. Builds package
  4. Commits and tags
  5. Publishes to PyPI (if enabled)
  6. Creates GitHub release
- **Uses**: PyPI Trusted Publishing (no API token needed)

### deploy-docs.yml - Documentation
- **Triggers**: Push to main or manual
- **Deploys documentation to GitHub Pages**

### docs-monitor.yml - Documentation Health
- **Triggers**: Daily at 2 AM UTC or manual
- **Checks if documentation site is accessible**

## Design Principles

1. **Single release workflow**: One workflow for version bump, PyPI, and GitHub release
2. **No redundant testing**: Tests run in CI, minimal tests in release
3. **Fast feedback**: PostgreSQL-only tests (except one SQLite smoke test)
4. **Non-blocking quality checks**: Linting and coverage are informational
5. **Simple configuration**: Direct PyPI publishing with API token