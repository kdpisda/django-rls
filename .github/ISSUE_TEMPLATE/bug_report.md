---
name: 🐛 Bug Report
about: Create a report to help us improve Django RLS
title: '[BUG] '
labels: 'bug, needs-triage'
assignees: ''

---

## Bug Description
<!-- A clear and concise description of what the bug is -->

## To Reproduce
Steps to reproduce the behavior:
1. Configure Django RLS with '...'
2. Create a model with '...'
3. Apply policy '...'
4. See error

## Expected Behavior
<!-- A clear and concise description of what you expected to happen -->

## Actual Behavior
<!-- What actually happened -->

## Error Messages
```python
# Paste any error messages or stack traces here
```

## Environment
- **Django RLS Version**: 
- **Django Version**: 
- **Python Version**: 
- **PostgreSQL Version**: 
- **Operating System**: 

## Database Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django_rls.backends.postgresql',
        # ... other settings
    }
}
```

## Model and Policy Configuration
```python
# Paste your model and policy configuration here
class MyModel(RLSModel):
    # ...
    
    class Meta:
        rls_policies = [
            # ...
        ]
```

## RLS Context
<!-- How is the RLS context being set? -->
- [ ] Using default middleware
- [ ] Custom context extraction
- [ ] Manual context setting

## Additional Context
<!-- Add any other context about the problem here -->

## Security Impact
<!-- Does this bug have any security implications? -->
- [ ] This bug could lead to unauthorized data access
- [ ] This bug could allow RLS bypass
- [ ] No security impact

## Possible Solution
<!-- If you have suggestions on how to fix the bug, please describe -->

## Screenshots
<!-- If applicable, add screenshots to help explain your problem -->