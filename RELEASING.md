# Releasing django-rls

This document describes the release process for django-rls.

## Release Types

django-rls follows [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0): Breaking changes
- **Minor** (0.X.0): New features, backwards compatible
- **Patch** (0.0.X): Bug fixes, backwards compatible
- **Pre-release**: Alpha, Beta, RC versions (e.g., 1.0.0-alpha.1)

## Automated Release Process

The preferred method is using GitHub Actions:

### 1. Via GitHub UI

1. Go to [Actions → Release to PyPI](https://github.com/kdpisda/django-rls/actions/workflows/release.yml)
2. Click "Run workflow"
3. Select version bump type:
   - `patch`: Bug fixes (0.1.0 → 0.1.1)
   - `minor`: New features (0.1.0 → 0.2.0)
   - `major`: Breaking changes (0.1.0 → 1.0.0)
   - `pre`: Pre-release versions
4. For pre-releases, select type: `alpha`, `beta`, or `rc`
5. Click "Run workflow"

The workflow will:
- Run all tests
- Bump version
- Create git tag
- Build packages
- Upload to TestPyPI
- Test installation
- Upload to PyPI (for stable releases)
- Create GitHub release

### 2. Via Git Tags

Push a version tag to trigger release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Manual Release Process

For local testing or manual releases:

### 1. Check Release Readiness

```bash
./scripts/release.sh check
```

This will:
- Verify git status is clean
- Check you're on main branch
- Run all tests
- Check coverage (>90%)

### 2. Bump Version

```bash
# Patch release (bug fixes)
./scripts/release.sh bump patch

# Minor release (new features)
./scripts/release.sh bump minor

# Major release (breaking changes)
./scripts/release.sh bump major

# Pre-release
./scripts/release.sh bump pre --pre-release alpha
./scripts/release.sh bump pre --pre-release beta
./scripts/release.sh bump pre --pre-release rc
```

### 3. Build Distribution

```bash
./scripts/release.sh build
```

### 4. Upload to TestPyPI

```bash
./scripts/release.sh test-pypi
```

Test installation:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple django-rls==VERSION
```

### 5. Upload to PyPI

```bash
./scripts/release.sh pypi
```

## Version Bumping Examples

Current version: 0.1.0

- `patch` → 0.1.1
- `minor` → 0.2.0
- `major` → 1.0.0
- `pre --pre-release alpha` → 0.1.1-alpha.1
- `pre --pre-release alpha` (again) → 0.1.1-alpha.2
- `pre --pre-release beta` → 0.1.1-beta.1
- `patch` (from pre-release) → 0.1.1

## Pre-release Workflow

1. Create alpha releases for early testing:
   ```bash
   ./scripts/release.sh bump pre --pre-release alpha
   ```

2. Progress to beta when feature-complete:
   ```bash
   ./scripts/release.sh bump pre --pre-release beta
   ```

3. Release candidates for final testing:
   ```bash
   ./scripts/release.sh bump pre --pre-release rc
   ```

4. Final release:
   ```bash
   ./scripts/release.sh bump patch
   ```

## GitHub Environments

The release workflow uses two environments:

1. **test-release**: For TestPyPI uploads
   - No additional secrets required
   - Automatic approval

2. **release**: For PyPI uploads
   - Requires PyPI API token
   - Manual approval for major versions

## Setting Up PyPI Tokens

1. Create account on [PyPI](https://pypi.org/)
2. Generate API token: Account settings → API tokens
3. Add to GitHub secrets:
   - Go to Settings → Secrets → Actions
   - Add `PYPI_API_TOKEN`

For TestPyPI:
1. Create account on [TestPyPI](https://test.pypi.org/)
2. Generate API token
3. Add `TEST_PYPI_API_TOKEN` to GitHub secrets

## Post-Release Checklist

After a successful release:

- [ ] Verify package on PyPI: https://pypi.org/project/django-rls/
- [ ] Test installation: `pip install django-rls==VERSION`
- [ ] Check documentation is updated: https://django-rls.com
- [ ] Update changelog if needed
- [ ] Announce release (if major/minor)

## Troubleshooting

### Build Failures

```bash
# Clean build artifacts
rm -rf dist/ build/ *.egg-info

# Rebuild
poetry build
```

### Version Conflicts

```bash
# Check current version
python -c "from django_rls.__version__ import __version__; print(__version__)"

# Reset to tag
git reset --hard v0.1.0
```

### Failed TestPyPI Upload

- Check if version already exists
- Use `--skip-existing` flag
- Bump version and retry

### Failed PyPI Upload

- Verify API token is correct
- Check version doesn't exist
- Ensure all tests pass

## Emergency Rollback

If a bad release is published:

1. Yank the release on PyPI (doesn't delete, just marks as "yanked")
2. Fix the issue
3. Release a new patch version

**Note**: Never delete or reuse version numbers!