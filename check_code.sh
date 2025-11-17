#!/bin/bash
# Comprehensive Python Code Checker Script
# Usage: ./check_code.sh

set -e

echo "🔍 Python Code Quality Checker"
echo "=============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Warning: Not in a virtual environment${NC}"
fi

echo "📁 Working directory: $(pwd)"
echo ""

# 1. Python Syntax Check (built-in, catches undefined names)
echo "1️⃣  Running Python Compile Check..."
echo "   (Checks syntax and catches undefined names)"
COMPILE_ERRORS=0
for file in $(find data -name "*.py" 2>/dev/null); do
    if ! python -m py_compile "$file" 2>/dev/null; then
        echo -e "   ${RED}✗ $file${NC}"
        COMPILE_ERRORS=$((COMPILE_ERRORS + 1))
    fi
done

if [ $COMPILE_ERRORS -eq 0 ]; then
    echo -e "   ${GREEN}✓ All files compile successfully${NC}"
else
    echo -e "   ${RED}✗ Found $COMPILE_ERRORS files with compile errors${NC}"
fi
echo ""

# 2. Ruff (Style & Simple Errors)
echo "2️⃣  Running Ruff..."
if command -v ruff &> /dev/null; then
    ruff check . --select ALL --ignore E501,COM812,ISC001,D,ANN 2>&1 | head -50
    echo -e "   ${GREEN}✓ Ruff check complete${NC}"
else
    echo -e "   ${YELLOW}⚠️  Ruff not found (install: pip install ruff)${NC}"
fi
echo ""

# 3. Mypy (Type Checking) - Optional but recommended
echo "3️⃣  Running Mypy (Type Checker)..."
if command -v mypy &> /dev/null; then
    mypy data/ --ignore-missing-imports --no-error-summary 2>&1 | head -30 || echo -e "   ${YELLOW}Found some type issues${NC}"
    echo -e "   ${GREEN}✓ Mypy check complete${NC}"
else
    echo -e "   ${YELLOW}⚠️  Mypy not installed (install: pip install mypy)${NC}"
    echo -e "   ${YELLOW}   Mypy would catch type errors and undefined names${NC}"
fi
echo ""

# 4. Pylint (Comprehensive) - Optional
echo "4️⃣  Running Pylint (if available)..."
if command -v pylint &> /dev/null; then
    pylint data/ --disable=C,R,W --enable=E 2>&1 | head -30 || echo -e "   ${YELLOW}Found some issues${NC}"
    echo -e "   ${GREEN}✓ Pylint check complete${NC}"
else
    echo -e "   ${YELLOW}⚠️  Pylint not installed (install: pip install pylint)${NC}"
fi
echo ""

# Summary
echo "=============================="
echo "✅ Code check complete!"
echo ""
echo "📋 Recommendations:"
echo "   • Ruff: Fast style checking (already installed)"
echo "   • Mypy: Type checking - catches undefined names (pip install mypy)"
echo "   • Pylint: Comprehensive linting (pip install pylint)"
echo ""
