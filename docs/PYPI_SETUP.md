# PyPI Setup Guide

## Using Trusted Publishing (Recommended)

This project uses PyPI's Trusted Publishing feature, which is more secure than API tokens.

### Setup (Already Done)
1. PyPI has been configured with:
   - Repository: `kdpisda/django-rls`
   - Workflow: `release.yml`
   - Environment: `release`

2. The GitHub workflow is configured with:
   - `environment: release`
   - `permissions: id-token: write`

No API tokens or passwords needed!

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