# PyPI Setup Guide

## Prerequisites

1. Create a PyPI account at https://pypi.org/account/register/
2. Generate an API token:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token with scope "Entire account" or project-specific
   - Copy the token (starts with `pypi-`)

## GitHub Repository Setup

1. Go to your repository settings: https://github.com/kdpisda/django-rls/settings/secrets/actions
2. Click "New repository secret"
3. Name: `PYPI_API_TOKEN`
4. Value: Paste your PyPI token
5. Click "Add secret"

## Publishing with GitHub Actions

1. Go to Actions → "Release"
2. Click "Run workflow"
3. Select:
   - **version_bump**: patch, minor, or major
   - **publish_to_pypi**: ✓ (checked)
4. Click "Run workflow"

The workflow will:
- Bump the version
- Run tests
- Build the package
- Push changes and tag
- Publish to PyPI
- Create GitHub release

## Manual Publishing (Local)
```bash
# Bump version
python scripts/bump_version.py patch  # or minor/major

# Build
poetry build

# Check
twine check dist/*

# Upload
twine upload dist/*

# Create git tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main --tags
```

## Verify Publication
- Check https://pypi.org/project/django-rls/
- Test installation: `pip install django-rls`