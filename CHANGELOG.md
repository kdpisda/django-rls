# Changelog

All notable changes to django-rls will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-01

### Added
- **Django 6.0 Support**: Full compatibility with the upcoming Django 6.0 release.
- **Pythonic Policies**: Define RLS policies using standard Django `Q` objects and `ModelPolicy` class.
- **Context Processors**: Support for dynamic RLS context variables via `RLS_CONTEXT_PROCESSORS` setting.
- **Flexible User Models**: Full support for custom User models, including UUID primary keys.
- **Joined Field Support**: Automatic handling of related field lookups (e.g., `company__name`) in policies by converting them to subqueries.
- **Enterprise Features**: Examples and support for hierarchical (recursive) policies and granular ACLs.
- **Helpers**: `RLS.user_id()`, `RLS.tenant_id()`, and `RLS.context()` helpers for easy policy definition.

## [0.1.0] - 2025-01-30

### Added
- Initial release of django-rls
- Core RLSModel for Django models with PostgreSQL Row Level Security
- TenantPolicy and UserPolicy for common use cases
- Django schema editor integration for proper database operations
- Management commands: enable_rls, disable_rls
- Middleware for automatic RLS context setting
- Comprehensive test suite with >90% coverage
- Support for Django 5.0, 5.1, and 5.2 (LTS)
- Support for Python 3.10, 3.11, 3.12, and 3.13
- PostgreSQL 12+ support (tested with PostgreSQL 17)
- Documentation at https://django-rls.com

### Security
- Field name validation to prevent SQL injection
- Secure policy generation using Django's database abstraction

[unreleased]: https://github.com/kdpisda/django-rls/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kdpisda/django-rls/releases/tag/v0.1.0
