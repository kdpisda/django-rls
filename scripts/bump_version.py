#!/usr/bin/env python3
"""
Version bumping script for django-rls
Handles semantic versioning with major.minor.patch and pre-release support
"""

import argparse
import re
import sys
from pathlib import Path

VERSION_FILE = Path(__file__).parent.parent / "django_rls" / "__version__.py"
PYPROJECT_FILE = Path(__file__).parent.parent / "pyproject.toml"


def parse_version(version_str):
    """Parse version string into components"""
    # Match version with optional pre-release
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    pre_release_type = match.group(4)
    pre_release_num = int(match.group(5)) if match.group(5) else None
    
    return major, minor, patch, pre_release_type, pre_release_num


def format_version(major, minor, patch, pre_release_type=None, pre_release_num=None):
    """Format version components into string"""
    version = f"{major}.{minor}.{patch}"
    if pre_release_type and pre_release_num is not None:
        version += f"-{pre_release_type}.{pre_release_num}"
    return version


def get_current_version():
    """Get current version from __version__.py"""
    content = VERSION_FILE.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Could not find __version__ in __version__.py")
    return match.group(1)


def update_version_file(new_version):
    """Update version in __version__.py"""
    content = VERSION_FILE.read_text()
    content = re.sub(
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    VERSION_FILE.write_text(content)


def update_pyproject_toml(new_version):
    """Update version in pyproject.toml"""
    content = PYPROJECT_FILE.read_text()
    content = re.sub(
        r'version\s*=\s*["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content,
        count=1
    )
    PYPROJECT_FILE.write_text(content)


def bump_version(bump_type, pre_release=None):
    """Bump version based on type"""
    current = get_current_version()
    major, minor, patch, pre_type, pre_num = parse_version(current)
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
        pre_type = None
        pre_num = None
    elif bump_type == "minor":
        minor += 1
        patch = 0
        pre_type = None
        pre_num = None
    elif bump_type == "patch":
        if pre_type:  # If current is pre-release, just remove pre-release
            pre_type = None
            pre_num = None
        else:
            patch += 1
    elif bump_type == "pre":
        if not pre_release:
            raise ValueError("Pre-release type required for 'pre' bump")
        
        if pre_type == pre_release:
            # Same pre-release type, increment number
            pre_num = (pre_num or 0) + 1
        else:
            # New pre-release type
            if not pre_type:
                # Moving from stable to pre-release, bump patch
                patch += 1
            pre_type = pre_release
            pre_num = 1
    
    new_version = format_version(major, minor, patch, pre_type, pre_num)
    return new_version


def main():
    parser = argparse.ArgumentParser(description="Bump django-rls version")
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch", "pre"],
        help="Type of version bump"
    )
    parser.add_argument(
        "--pre-release",
        choices=["alpha", "beta", "rc"],
        help="Pre-release type (required for 'pre' bump)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    
    args = parser.parse_args()
    
    try:
        current = get_current_version()
        new_version = bump_version(args.bump_type, args.pre_release)
        
        print(f"Current version: {current}")
        print(f"New version: {new_version}")
        
        if not args.dry_run:
            update_version_file(new_version)
            update_pyproject_toml(new_version)
            print("Version updated successfully!")
        else:
            print("(Dry run - no changes made)")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()