# Security Policy

## Supported Versions

Currently supported versions for security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Django RLS seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue
If the vulnerability is critical and could be exploited in production systems, please DO NOT create a public GitHub issue.

### 2. Report Privately
Send an email to: security@django-rls.org (or contact maintainers directly)

Include the following information:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Affected versions
- Any suggested fixes

### 3. Response Timeline
- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (Critical: 1-2 weeks, High: 2-4 weeks)

## Security Considerations

### PostgreSQL Row Level Security
Django RLS implements database-level security using PostgreSQL's Row Level Security feature. This provides:

1. **Database-enforced access control** - Security is enforced at the database level, not in application code
2. **Consistent security** - All queries, including raw SQL, respect RLS policies
3. **Performance** - PostgreSQL optimizes RLS policies as part of query planning

### Key Security Features

#### 1. SQL Injection Prevention
- All SQL operations use Django's parameterized queries
- Policy names and table names are properly quoted using Django's `quote_name()`
- User input is never directly concatenated into SQL strings

#### 2. Context Isolation
- Each request has its own RLS context
- Context is cleared after each request
- Database connections use transaction-level settings

#### 3. Authentication Integration
- RLS context is automatically set from Django's authentication
- Anonymous users don't get user context
- Middleware prevents context manipulation via headers/parameters

#### 4. Policy Validation
- Policies are validated at model definition time
- Invalid policies raise exceptions early
- Policy expressions are type-checked

### Security Best Practices

When using Django RLS, follow these best practices:

#### 1. Database Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django_rls.backends.postgresql',
        # Use strong passwords
        'PASSWORD': 'use-a-strong-password',
        # Use SSL for production
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
```

#### 2. Policy Design
```python
class SecureModel(RLSModel):
    class Meta:
        rls_policies = [
            # Use restrictive policies
            UserPolicy('owner_only', user_field='owner', permissive=False),
            # Combine multiple policies for defense in depth
            TenantPolicy('tenant_isolation', tenant_field='tenant'),
        ]
```

#### 3. Force RLS
Always force RLS to prevent bypass by table owners:
```python
# In migrations or management commands
schema_editor.force_rls(Model)
```

#### 4. Audit Policies
Regularly audit your RLS policies:
```sql
-- List all policies
SELECT schemaname, tablename, policyname, permissive, roles, qual, with_check
FROM pg_policies
WHERE schemaname = 'public';
```

### Common Vulnerabilities and Mitigations

#### 1. SQL Injection
**Risk**: Malicious SQL in policy expressions
**Mitigation**: 
- Use parameterized expressions
- Validate custom policy expressions
- Never concatenate user input

#### 2. Context Manipulation
**Risk**: Users trying to change RLS context
**Mitigation**:
- Context is set only from authenticated user
- Headers and parameters are ignored
- Use signed sessions

#### 3. Privilege Escalation
**Risk**: Users accessing data outside their permission
**Mitigation**:
- Use restrictive policies by default
- Implement defense in depth with multiple policies
- Regular security audits

#### 4. Cross-Tenant Access
**Risk**: Data leakage between tenants
**Mitigation**:
- Strict tenant isolation in policies
- Validate tenant membership
- Test with multiple tenants

### Security Testing

Run security tests regularly:
```bash
# Run security-specific tests
poetry run pytest tests/test_security.py -v

# Run with security markers
poetry run pytest -m security

# Check for SQL injection vulnerabilities
poetry run bandit -r django_rls/
```

### Security Headers

When using Django RLS in production, ensure proper security headers:
```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

## Security Checklist

Before deploying Django RLS:

- [ ] Database user has minimum required privileges
- [ ] RLS is forced on all sensitive tables
- [ ] Policies are restrictive by default
- [ ] SSL is enabled for database connections
- [ ] Security tests pass
- [ ] Audit logging is configured
- [ ] Regular security updates are planned
- [ ] Incident response plan is in place

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)

## Contact

For security concerns, contact:
- Email: security@django-rls.org
- PGP Key: [Available on request]

Thank you for helping keep Django RLS secure!