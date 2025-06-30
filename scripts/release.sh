#!/bin/bash
# Release script for django-rls
# This script helps with manual releases and local testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  check       Check if ready for release"
    echo "  build       Build distribution packages"
    echo "  test-pypi   Upload to TestPyPI"
    echo "  pypi        Upload to PyPI (requires confirmation)"
    echo "  bump        Bump version (major|minor|patch|pre)"
    echo ""
    echo "Options:"
    echo "  --pre-release [alpha|beta|rc]  Pre-release type for bump"
    echo "  --skip-tests                    Skip running tests"
    echo "  --dry-run                       Show what would be done"
}

print_error() {
    echo -e "${RED}Error: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}Warning: $1${NC}"
}

# Check if Poetry is installed
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed. Please install it first."
        exit 1
    fi
}

# Run tests
run_tests() {
    echo "Running tests..."
    if poetry run pytest --cov=django_rls --cov-report=term-missing; then
        print_success "All tests passed!"
        
        # Check coverage
        COVERAGE=$(poetry run coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
        if (( $(echo "$COVERAGE < 90" | bc -l) )); then
            print_warning "Coverage is below 90% ($COVERAGE%)"
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            print_success "Coverage is $COVERAGE%"
        fi
    else
        print_error "Tests failed!"
        exit 1
    fi
}

# Check if working directory is clean
check_git_status() {
    if [[ -n $(git status -s) ]]; then
        print_error "Working directory is not clean. Please commit or stash changes."
        exit 1
    fi
    print_success "Working directory is clean"
}

# Check if on main branch
check_branch() {
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$BRANCH" != "main" ]; then
        print_warning "Not on main branch (current: $BRANCH)"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "On main branch"
    fi
}

# Get current version
get_version() {
    python -c "from django_rls.__version__ import __version__; print(__version__)"
}

# Check command
cmd_check() {
    echo "Checking release readiness..."
    
    check_poetry
    check_git_status
    check_branch
    
    if [[ "$1" != "--skip-tests" ]]; then
        run_tests
    fi
    
    VERSION=$(get_version)
    print_success "Current version: $VERSION"
    
    # Check if version tag exists
    if git rev-parse "v$VERSION" >/dev/null 2>&1; then
        print_warning "Tag v$VERSION already exists"
    fi
    
    print_success "Ready for release!"
}

# Build command
cmd_build() {
    echo "Building distribution packages..."
    
    # Clean old builds
    rm -rf dist/ build/ *.egg-info
    
    # Build with Poetry
    poetry build
    
    print_success "Build complete!"
    echo "Contents of dist/:"
    ls -la dist/
}

# Bump version command
cmd_bump() {
    BUMP_TYPE=$1
    PRE_RELEASE=$2
    
    if [ -z "$BUMP_TYPE" ]; then
        print_error "Bump type required (major|minor|patch|pre)"
        exit 1
    fi
    
    CURRENT_VERSION=$(get_version)
    echo "Current version: $CURRENT_VERSION"
    
    # Run bump script
    if [ -n "$PRE_RELEASE" ]; then
        python scripts/bump_version.py "$BUMP_TYPE" --pre-release "$PRE_RELEASE"
    else
        python scripts/bump_version.py "$BUMP_TYPE"
    fi
    
    NEW_VERSION=$(get_version)
    print_success "Version bumped to: $NEW_VERSION"
    
    # Commit and tag
    read -p "Commit and tag version $NEW_VERSION? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add django_rls/__version__.py pyproject.toml
        git commit -m "chore: bump version to $NEW_VERSION"
        git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
        print_success "Version committed and tagged"
        
        read -p "Push to origin? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push origin main --tags
            print_success "Pushed to origin"
        fi
    fi
}

# TestPyPI upload command
cmd_test_pypi() {
    echo "Uploading to TestPyPI..."
    
    if [ ! -d "dist" ]; then
        print_error "No dist directory found. Run 'build' first."
        exit 1
    fi
    
    poetry publish -r testpypi
    
    VERSION=$(get_version)
    print_success "Published to TestPyPI!"
    echo ""
    echo "Test installation with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple django-rls==$VERSION"
}

# PyPI upload command
cmd_pypi() {
    echo "Uploading to PyPI..."
    
    VERSION=$(get_version)
    print_warning "About to publish django-rls $VERSION to PyPI"
    read -p "Are you sure? (yes/N) " -r
    if [[ ! $REPLY == "yes" ]]; then
        echo "Aborted."
        exit 1
    fi
    
    poetry publish
    
    print_success "Published to PyPI!"
    echo ""
    echo "Install with:"
    echo "  pip install django-rls==$VERSION"
}

# Main script
check_poetry

case "$1" in
    check)
        cmd_check "${@:2}"
        ;;
    build)
        cmd_build
        ;;
    bump)
        # Parse options
        BUMP_TYPE=""
        PRE_RELEASE=""
        shift
        while [[ $# -gt 0 ]]; do
            case $1 in
                --pre-release)
                    PRE_RELEASE="$2"
                    shift 2
                    ;;
                *)
                    BUMP_TYPE="$1"
                    shift
                    ;;
            esac
        done
        cmd_bump "$BUMP_TYPE" "$PRE_RELEASE"
        ;;
    test-pypi)
        cmd_test_pypi
        ;;
    pypi)
        cmd_pypi
        ;;
    *)
        print_usage
        exit 1
        ;;
esac