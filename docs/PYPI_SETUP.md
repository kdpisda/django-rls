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

## Publishing Options

### Option 1: Simple Direct Publish (Recommended)
```bash
# 1. Update version in django_rls/__version__.py
# 2. Commit and push
# 3. Go to Actions > Publish to PyPI
# 4. Run workflow, type "yes" to confirm
```

### Option 2: Full Release Workflow
```bash
# 1. Go to Actions > Release to PyPI
# 2. Choose version bump type
# 3. Run workflow
# Note: This requires fixing the trusted publishing setup
```

## Manual Publishing (Local)
```bash
# Build
poetry build

# Check
twine check dist/*

# Upload
twine upload dist/*
```

## Verify Publication
- Check https://pypi.org/project/django-rls/
- Test installation: `pip install django-rls`