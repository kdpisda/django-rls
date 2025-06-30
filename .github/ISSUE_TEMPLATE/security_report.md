---
name: 🔒 Security Vulnerability Report
about: Report a security vulnerability in Django RLS
title: '[SECURITY] '
labels: 'security, priority-high'
assignees: ''

---

⚠️ **IMPORTANT**: If this is a critical security vulnerability that could affect users in production, please consider responsible disclosure by emailing the maintainers directly instead of opening a public issue.

## Vulnerability Description
<!-- Describe the security vulnerability -->

## Type of Vulnerability
<!-- Check all that apply -->
- [ ] SQL Injection
- [ ] RLS Bypass
- [ ] Privilege Escalation
- [ ] Information Disclosure
- [ ] Authentication Bypass
- [ ] Cross-Tenant Data Access
- [ ] Other: 

## OWASP Category
<!-- Which OWASP Top 10 category does this relate to? -->
- [ ] A01:2021 – Broken Access Control
- [ ] A02:2021 – Cryptographic Failures
- [ ] A03:2021 – Injection
- [ ] A04:2021 – Insecure Design
- [ ] A05:2021 – Security Misconfiguration
- [ ] A06:2021 – Vulnerable and Outdated Components
- [ ] A07:2021 – Identification and Authentication Failures
- [ ] A08:2021 – Software and Data Integrity Failures
- [ ] A09:2021 – Security Logging and Monitoring Failures
- [ ] A10:2021 – Server-Side Request Forgery

## Steps to Reproduce
<!-- Provide detailed steps to reproduce the vulnerability -->
1. 
2. 
3. 

## Proof of Concept
```python
# Provide code that demonstrates the vulnerability
# Please be responsible and avoid including actual exploit code
```

## Impact Assessment
<!-- What is the potential impact of this vulnerability? -->

### Severity
- [ ] Critical - Remote code execution, complete RLS bypass
- [ ] High - Unauthorized data access, partial RLS bypass
- [ ] Medium - Limited data exposure, requires authentication
- [ ] Low - Minor issue, limited impact

### Affected Components
- [ ] RLSModel
- [ ] Policies
- [ ] Middleware
- [ ] Schema Editor
- [ ] Migration Operations
- [ ] Other: 

## Affected Versions
<!-- Which versions of Django RLS are affected? -->
- Django RLS versions: 
- Django versions: 
- PostgreSQL versions: 

## Mitigation
<!-- Have you identified any workarounds or mitigations? -->

## Suggested Fix
<!-- If you have ideas on how to fix this vulnerability -->

## Environment
- **Django RLS Version**: 
- **Django Version**: 
- **Python Version**: 
- **PostgreSQL Version**: 
- **Operating System**: 

## Additional Context
<!-- Add any other context about the vulnerability here -->

## Disclosure Timeline
<!-- If you've already attempted to contact maintainers -->
- Date discovered: 
- Date reported privately (if applicable): 
- Date of public disclosure: 

## Credit
<!-- How would you like to be credited for this discovery? -->