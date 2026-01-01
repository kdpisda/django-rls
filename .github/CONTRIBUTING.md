# Contributing to Django RLS

We love your input! We want to make contributing to Django RLS as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/django-rls.git
cd django-rls

# Run setup script
./scripts/setup_dev.sh

# Or manually:
poetry install
poetry run pre-commit install
```

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_policies.py

# Run with coverage
poetry run pytest --cov=django_rls
```

## Code Style

- We use [Black](https://github.com/psf/black) for code formatting
- We use [isort](https://github.com/PyCQA/isort) for import sorting
- We use [flake8](https://github.com/PyCQA/flake8) for linting

Run all checks:
```bash
poetry run black .
poetry run isort .
poetry run flake8 .
poetry run mypy django_rls
```

## Pull Request Process

1. Update the README.md with details of changes to the interface
2. Update the docs with any new functionality
3. The PR will be merged once you have the sign-off of at least one maintainer

## Any contributions you make will be under the BSD 3-Clause License

When you submit code changes, your submissions are understood to be under the same [BSD 3-Clause License](LICENSE) that covers the project.

## Report bugs using GitHub's [issue tracker](https://github.com/kdpisda/django-rls/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/kdpisda/django-rls/issues/new).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## License

By contributing, you agree that your contributions will be licensed under its BSD 3-Clause License.