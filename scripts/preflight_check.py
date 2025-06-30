#!/usr/bin/env python3
"""Pre-flight check script for django-rls releases."""

import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def run_command(cmd, capture=True, check=True):
    """Run a shell command and return output."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, check=check)
        return result.stdout.strip() if capture else None
    except subprocess.CalledProcessError as e:
        if capture:
            return None
        raise


def print_status(message, status="info"):
    """Print colored status message."""
    if status == "success":
        print(f"{Colors.GREEN}✓ {message}{Colors.END}")
    elif status == "error":
        print(f"{Colors.RED}✗ {message}{Colors.END}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")
    else:
        print(f"{Colors.BLUE}→ {message}{Colors.END}")


def check_git_status():
    """Check if git working directory is clean."""
    print_status("Checking git status...")
    
    status = run_command("git status --porcelain")
    if status:
        print_status("Working directory is not clean", "error")
        print("  Uncommitted changes:")
        for line in status.split('\n'):
            if line:
                print(f"    {line}")
        return False
    
    branch = run_command("git rev-parse --abbrev-ref HEAD")
    if branch != "main":
        print_status(f"Not on main branch (current: {branch})", "warning")
    else:
        print_status("Git status is clean", "success")
    
    return True


def check_version():
    """Check and display current version."""
    print_status("Checking version...")
    
    try:
        sys.path.insert(0, str(Path.cwd()))
        from django_rls.__version__ import __version__
        print_status(f"Current version: {__version__}", "success")
        return __version__
    except Exception as e:
        print_status(f"Failed to get version: {e}", "error")
        return None


def run_tests():
    """Run test suite."""
    print_status("Running tests...")
    
    result = run_command("poetry run pytest -q --tb=short", capture=False, check=False)
    if result is None:
        print_status("Some tests failed", "warning")
        return False
    
    print_status("All tests passed", "success")
    return True


def check_coverage():
    """Check test coverage."""
    print_status("Checking coverage...")
    
    coverage = run_command("poetry run coverage report | grep TOTAL | awk '{print $4}'")
    if coverage:
        coverage_val = float(coverage.strip('%'))
        if coverage_val < 90:
            print_status(f"Coverage is {coverage}% (below 90%)", "warning")
        else:
            print_status(f"Coverage is {coverage}%", "success")
    
    return True


def build_package():
    """Build distribution packages."""
    print_status("Building packages...")
    
    # Clean old builds
    for path in ['dist', 'build']:
        if os.path.exists(path):
            shutil.rmtree(path)
    
    result = run_command("poetry build", capture=False, check=False)
    
    # Check if files were created
    dist_files = list(Path('dist').glob('*')) if Path('dist').exists() else []
    if len(dist_files) >= 2:
        print_status(f"Built {len(dist_files)} distribution files", "success")
        for f in dist_files:
            print(f"    {f.name}")
        return True
    else:
        print_status("Failed to build packages", "error")
        return False


def check_package_content():
    """Verify package contains expected files."""
    print_status("Checking package contents...")
    
    tar_files = list(Path('dist').glob('*.tar.gz'))
    if not tar_files:
        print_status("No tar.gz file found", "error")
        return False
    
    tar_file = tar_files[0]
    files = run_command(f"tar -tzf {tar_file}")
    
    required_files = [
        'LICENSE',
        'README.md',
        '__init__.py',
        '__version__.py',
        'models.py',
        'policies.py',
        'backends/postgresql/base.py'
    ]
    
    missing = []
    for req in required_files:
        if req not in files:
            missing.append(req)
    
    if missing:
        print_status(f"Missing files in package: {', '.join(missing)}", "error")
        return False
    
    print_status("Package contains all required files", "success")
    return True


def test_installation():
    """Test package installation in clean environment."""
    print_status("Testing package installation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / 'venv'
        
        # Create virtual environment
        run_command(f"python -m venv {venv_path}", check=False)
        
        # Install package
        pip_path = venv_path / 'bin' / 'pip'
        wheel_files = list(Path('dist').glob('*.whl'))
        if not wheel_files:
            print_status("No wheel file found", "error")
            return False
        
        result = run_command(f"{pip_path} install {wheel_files[0]}", check=False)
        
        # Test import
        python_path = venv_path / 'bin' / 'python'
        test_code = """
import django_rls
print(django_rls.__version__)
"""
        
        result = run_command([str(python_path), '-c', test_code], check=False)
        if result:
            print_status(f"Package installed and imported successfully (v{result})", "success")
            return True
        else:
            print_status("Failed to import package after installation", "error")
            return False


def check_pypi_config():
    """Check PyPI configuration."""
    print_status("Checking PyPI configuration...")
    
    # Check if twine is available
    result = run_command("which twine", check=False)
    if not result:
        print_status("twine not installed (pip install twine)", "warning")
    
    # Check package with twine
    result = run_command("twine check dist/*", capture=False, check=False)
    
    # Check poetry config
    testpypi = run_command("poetry config repositories.testpypi.url", check=False)
    if testpypi:
        print_status(f"TestPyPI configured: {testpypi}", "success")
    else:
        print_status("TestPyPI not configured", "warning")
    
    return True


def main():
    """Run all pre-flight checks."""
    print(f"\n{Colors.BLUE}=== Django-RLS Pre-flight Check ==={Colors.END}\n")
    
    checks = [
        ("Git Status", check_git_status),
        ("Version", check_version),
        ("Tests", run_tests),
        ("Coverage", check_coverage),
        ("Build", build_package),
        ("Package Content", check_package_content),
        ("Installation Test", test_installation),
        ("PyPI Config", check_pypi_config),
    ]
    
    results = {}
    for name, check_func in checks:
        print(f"\n{Colors.BLUE}--- {name} ---{Colors.END}")
        try:
            results[name] = check_func()
        except Exception as e:
            print_status(f"Check failed with error: {e}", "error")
            results[name] = False
    
    # Summary
    print(f"\n{Colors.BLUE}=== Summary ==={Colors.END}")
    failed = [name for name, result in results.items() if not result]
    warnings = [name for name, result in results.items() if result is None]
    
    if not failed:
        print_status("All checks passed! Ready for release.", "success")
        print("\nNext steps:")
        print("1. Push changes: git push origin main")
        print("2. Go to GitHub Actions → Release to PyPI")
        print("3. Run workflow with desired version bump")
        return 0
    else:
        print_status(f"Failed checks: {', '.join(failed)}", "error")
        if warnings:
            print_status(f"Warnings: {', '.join(warnings)}", "warning")
        return 1


if __name__ == "__main__":
    sys.exit(main())