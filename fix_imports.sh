#!/bin/bash
# Fix imports and code formatting
# Usage: ./fix_imports.sh [directory]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TARGET="${1:-.}"

echo "🧹 Cleaning up imports in: $TARGET"
echo "=================================="
echo ""

# 1. Remove unused imports (F401)
echo "1️⃣  Removing unused imports..."
if command -v ruff &> /dev/null; then
    ruff check "$TARGET" --select F401 --fix
    echo -e "   ${GREEN}✓ Unused imports removed${NC}"
else
    echo -e "   ${YELLOW}⚠️  Ruff not found${NC}"
    exit 1
fi
echo ""

# 2. Organize imports (isort rules)
echo "2️⃣  Organizing imports..."
ruff check "$TARGET" --select I --fix
echo -e "   ${GREEN}✓ Imports organized${NC}"
echo ""

# 3. Fix other common issues
echo "3️⃣  Fixing other code issues..."
ruff check "$TARGET" --fix
echo -e "   ${GREEN}✓ All fixable issues resolved${NC}"
echo ""

# 4. Format code
echo "4️⃣  Formatting code..."
ruff format "$TARGET"
echo -e "   ${GREEN}✓ Code formatted${NC}"
echo ""

echo "=================================="
echo -e "${GREEN}✅ Import cleanup complete!${NC}"
echo ""
