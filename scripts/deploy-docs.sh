#!/bin/bash
# Script to manually deploy documentation
# Usage: ./scripts/deploy-docs.sh

set -e

echo "🚀 Django RLS Documentation Deployment"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "documentations" ]; then
    echo -e "${RED}Error: This script must be run from the project root directory${NC}"
    exit 1
fi

# Navigate to documentation directory
cd documentations

echo -e "${YELLOW}📦 Installing dependencies...${NC}"
npm ci

echo -e "${YELLOW}🔨 Building documentation...${NC}"
npm run build

echo -e "${GREEN}✅ Build completed successfully!${NC}"

# Calculate checksum
CHECKSUM=$(find . -type f -name "*.md" -o -name "*.js" -o -name "*.json" -o -name "*.css" | 
           grep -v node_modules | grep -v build | sort | xargs cat | sha256sum | cut -d' ' -f1)
echo -e "${GREEN}📝 Documentation checksum: $CHECKSUM${NC}"

echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Commit and push changes to trigger automatic deployment"
echo "2. Or manually deploy using GitHub Actions workflow dispatch"
echo "3. Visit https://django-rls.com after deployment"
echo ""
echo -e "${GREEN}✨ Done!${NC}"