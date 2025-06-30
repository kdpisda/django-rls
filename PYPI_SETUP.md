# PyPI Setup Guide for django-rls

## Option 1: Trusted Publishing (Recommended)

This is the most secure method as it doesn't require storing API tokens.

### 1. Create PyPI Account
1. Go to [pypi.org](https://pypi.org) and create an account
2. Verify your email address

### 2. Create the Project on PyPI
1. Go to [pypi.org/manage/projects/](https://pypi.org/manage/projects/)
2. Click "Add a project"
3. Project name: `django-rls`

### 3. Configure Trusted Publishing
1. In your PyPI project, go to "Publishing" settings
2. Add a new trusted publisher:
   - **Publisher**: GitHub
   - **Owner**: `kdpisda`
   - **Repository**: `django-rls`
   - **Workflow name**: `.github/workflows/release.yml`
   - **Environment name**: `release` (important!)

### 4. Configure GitHub Environments
1. Go to your GitHub repo → Settings → Environments
2. Create environment: `release`
3. Add protection rules (optional):
   - Required reviewers: 1
   - Restrict to protected branches

### 5. For TestPyPI (Optional)
1. Create account on [test.pypi.org](https://test.pypi.org)
2. Same process as above but with environment name: `test-release`

## Option 2: API Token Method

If you prefer using API tokens:

### 1. Get PyPI API Token
1. Log in to [pypi.org](https://pypi.org)
2. Go to Account settings → API tokens
3. Add API token:
   - Token name: `django-rls-github-actions`
   - Scope: Select "Project: django-rls" (after first manual upload) or "Entire account"
4. Copy the token (starts with `pypi-`)

### 2. Add to GitHub Secrets
1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. New repository secret:
   - Name: `PYPI_API_TOKEN`
   - Value: (paste the token)

### 3. Update Workflow
Uncomment the API token lines in `.github/workflows/release.yml`:
```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    password: ${{ secrets.PYPI_API_TOKEN }}
```

## First Release Steps

### 1. Ensure Tests Pass
```bash
poetry run pytest
```

### 2. Trigger Release
Go to Actions → Release to PyPI → Run workflow:
- Version bump: `patch`
- This will release v0.1.0

### 3. Verify
- Check [pypi.org/project/django-rls/](https://pypi.org/project/django-rls/)
- Test installation: `pip install django-rls==0.1.0`

## Troubleshooting

### "Not authorized" Error
- Ensure environment name matches exactly (`release`)
- Check workflow file path is correct
- Wait a few minutes after configuring (PyPI caches)

### "Project not found" Error
- You may need to do first upload manually:
  ```bash
  poetry build
  poetry publish
  ```

### Trusted Publishing Not Working
- Ensure `permissions: id-token: write` is in workflow
- Check GitHub repo and owner names match exactly
- Environment protection rules might be blocking

## Questions for PyPI Form

When PyPI asks for GitHub Actions details:

- **Workflow file**: `.github/workflows/release.yml`
- **Environment**: `release`
- **Owner**: `kdpisda`
- **Repository**: `django-rls`