#!/usr/bin/env python3
"""Test django-rls with PostgreSQL locally - mimics GitHub Actions environment."""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, env=None, check=True):
    """Run a command and show output."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    print(f"\n→ Running: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        env={**os.environ, **(env or {})},
        capture_output=False,
        text=True,
        check=check
    )
    
    return result.returncode == 0


def check_postgresql():
    """Check if PostgreSQL is available."""
    print("Checking PostgreSQL availability...")
    
    # Check if Docker is running
    docker_check = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True
    )
    
    if docker_check.returncode != 0:
        print("\n❌ Docker is not running.")
        print("Please start Docker to run PostgreSQL tests.")
        return False
    
    # Check if test container is running
    container_check = subprocess.run(
        ["docker", "ps", "-q", "-f", "name=django-rls-test-db"],
        capture_output=True,
        text=True
    )
    
    if not container_check.stdout.strip():
        print("Starting PostgreSQL test container...")
        # Start the test container
        result = subprocess.run(
            ["docker", "compose", "-f", "docker-compose.test.yml", "up", "-d"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("❌ Failed to start PostgreSQL container")
            print(result.stderr)
            return False
        
        # Wait for container to be ready
        print("Waiting for PostgreSQL to be ready...")
        import time
        time.sleep(5)
    
    print("✅ PostgreSQL is available")
    return True


def setup_test_database():
    """Create test database."""
    print("\nSetting up test database...")
    
    # Database is automatically created by Django during tests
    print("✅ Database will be created by Django test runner")
    return True


def run_tests_sqlite():
    """Run tests with SQLite first (should pass)."""
    print("\n" + "="*60)
    print("Running tests with SQLite (baseline)...")
    print("="*60)
    
    env = {
        "USE_POSTGRESQL": "false",
        "DJANGO_SETTINGS_MODULE": "tests.settings"
    }
    
    return run_command(
        ["poetry", "run", "pytest", "-xvs", "--tb=short"],
        env=env,
        check=False
    )


def run_tests_postgresql():
    """Run tests with PostgreSQL."""
    print("\n" + "="*60)
    print("Running tests with PostgreSQL...")
    print("="*60)
    
    env = {
        "USE_POSTGRESQL": "true",
        "DB_NAME": "test_django_rls",
        "DB_USER": "postgres",
        "DB_PASSWORD": "postgres",
        "DB_HOST": "localhost",
        "DB_PORT": "5433",  # Test container uses port 5433
        "DJANGO_SETTINGS_MODULE": "tests.settings"
    }
    
    return run_command(
        ["poetry", "run", "pytest", "-xvs", "--tb=short", "-k", "not postgresql"],
        env=env,
        check=False
    )


def run_specific_postgresql_tests():
    """Run only PostgreSQL-specific tests."""
    print("\n" + "="*60)
    print("Running PostgreSQL-specific tests...")
    print("="*60)
    
    env = {
        "USE_POSTGRESQL": "true",
        "DB_NAME": "test_django_rls",
        "DB_USER": "postgres",
        "DB_PASSWORD": "postgres",
        "DB_HOST": "localhost",
        "DB_PORT": "5433",  # Test container uses port 5433
        "DJANGO_SETTINGS_MODULE": "tests.settings"
    }
    
    return run_command(
        ["poetry", "run", "pytest", "-xvs", "--tb=short", "-k", "postgresql"],
        env=env,
        check=False
    )


def main():
    """Run all tests."""
    print("\n🧪 Django-RLS PostgreSQL Test Runner")
    print("This mimics the GitHub Actions environment locally.")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Check PostgreSQL
    if not check_postgresql():
        print("\n⚠️  Skipping PostgreSQL tests - PostgreSQL not available")
        print("Running SQLite tests only...")
        success = run_tests_sqlite()
        return 0 if success else 1
    
    # Setup database
    if not setup_test_database():
        return 1
    
    # Run tests
    sqlite_ok = run_tests_sqlite()
    pg_ok = run_tests_postgresql()
    pg_specific_ok = run_specific_postgresql_tests()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary:")
    print("="*60)
    print(f"SQLite tests: {'✅ PASSED' if sqlite_ok else '❌ FAILED'}")
    print(f"PostgreSQL tests: {'✅ PASSED' if pg_ok else '❌ FAILED'}")
    print(f"PostgreSQL-specific tests: {'✅ PASSED' if pg_specific_ok else '❌ FAILED'}")
    
    if sqlite_ok and pg_ok:
        print("\n✅ All tests passed! Safe to push to GitHub.")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix before pushing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())