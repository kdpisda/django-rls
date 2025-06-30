#!/usr/bin/env python
"""
Django RLS test runner.

Based on Django REST Framework's test runner pattern.
"""
import os
import subprocess
import sys


def runtests(*test_args):
    """
    Run tests with pytest.
    
    Examples:
        ./runtests.py
        ./runtests.py TestRLSModel
        ./runtests.py test_policies
        ./runtests.py TestRLSModel.test_enable_rls
    """
    pytest_args = ['pytest']
    
    # Add coverage if requested
    if '--coverage' in test_args:
        pytest_args.extend([
            '--cov=django_rls',
            '--cov-report=term-missing',
            '--cov-report=html',
            '--cov-report=xml'
        ])
        test_args = [arg for arg in test_args if arg != '--coverage']
    
    # Add verbose if requested
    if '--verbose' in test_args or '-v' in test_args:
        pytest_args.append('-vv')
        test_args = [arg for arg in test_args if arg not in ['--verbose', '-v']]
    else:
        pytest_args.append('-v')
    
    # Add fail fast
    if '--failfast' in test_args:
        pytest_args.append('-x')
        test_args = [arg for arg in test_args if arg != '--failfast']
    
    # Show print statements
    if '--debug' in test_args:
        pytest_args.append('-s')
        test_args = [arg for arg in test_args if arg != '--debug']
    
    # If no tests specified, run all tests
    if not test_args:
        pytest_args.append('tests')
    else:
        # Convert test arguments to pytest format
        for arg in test_args:
            if '.' in arg:
                # TestCase.test_method format
                parts = arg.split('.')
                test_class = parts[0]
                test_method = parts[1] if len(parts) > 1 else ''
                
                # Find the test file
                test_path = find_test_path(test_class)
                if test_path:
                    if test_method:
                        pytest_args.append(f'{test_path}::{test_class}::{test_method}')
                    else:
                        pytest_args.append(f'{test_path}::{test_class}')
                else:
                    pytest_args.append(arg)
            else:
                # Try to find test file or class
                test_path = find_test_path(arg)
                if test_path:
                    pytest_args.append(test_path)
                else:
                    pytest_args.append(arg)
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
    
    # Run pytest
    return subprocess.call(pytest_args)


def find_test_path(name):
    """Find test file path for a given test name."""
    import os
    
    # Check if it's already a file path
    if os.path.exists(name):
        return name
    
    # Check common test file patterns
    patterns = [
        f'tests/test_{name.lower()}.py',
        f'tests/{name.lower()}.py',
        f'tests/test_{name}.py',
    ]
    
    for pattern in patterns:
        if os.path.exists(pattern):
            return pattern
    
    # Search for class name in test files
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                    if f'class {name}' in content:
                        return filepath
    
    return None


if __name__ == '__main__':
    sys.exit(runtests(*sys.argv[1:]))