# Code Quality Checking Guide

## Quick Start

### Run All Checks
```bash
./check_code.sh
```

## Individual Tools

### 1. Python Built-in Compile Check (Catches Undefined Names!)
**This would have caught your `DatabaseConnectionPool` error!**

```bash
# Check all files
python -m py_compile data/*.py

# Check specific file
python -m py_compile data/news_sentiment_analyzer.py
```

### 2. Ruff (Already Installed)
```bash
# Current style check
ruff check .

# Check specific rules
ruff check . --select G  # Logging format issues (we just fixed these!)
ruff check . --select F  # PyFlakes errors (undefined names, unused imports)
```

### 3. Install & Use Mypy (Highly Recommended!)
```bash
# Install
pip install mypy

# Run on your data directory
mypy data/ --ignore-missing-imports

# Run on specific file
mypy data/news_sentiment_analyzer.py
```

**Mypy would have caught the `DatabaseConnectionPool` error before runtime!**

### 4. Install & Use Pylint (Comprehensive)
```bash
# Install
pip install pylint

# Run on directory
pylint data/

# Run with only error messages
pylint data/ --disable=all --enable=E
```

## VS Code Integration

Add to `.vscode/settings.json`:

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.analysis.typeCheckingMode": "basic",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        },
        "editor.defaultFormatter": "charliermarsh.ruff"
    },
    "ruff.organizeImports": true,
    "ruff.fixAll": true
}
```

## Recommended Workflow

1. **Before Committing:**
   ```bash
   ./check_code.sh
   ```

2. **During Development (in VS Code):**
   - Enable Pylint/Mypy in settings
   - They'll show errors as you type

3. **Pre-commit Hook (Optional):**
   ```bash
   # Create .git/hooks/pre-commit
   #!/bin/bash
   python -m py_compile data/*.py
   ruff check .
   ```

## What Each Tool Catches

| Error Type | Compile Check | Ruff | Mypy | Pylint |
|------------|---------------|------|------|--------|
| Undefined names | ✅ | ❌ | ✅ | ✅ |
| Type errors | ❌ | ❌ | ✅ | ⚠️ |
| Import errors | ✅ | ⚠️ | ✅ | ✅ |
| Style issues | ❌ | ✅ | ❌ | ✅ |
| Logic errors | ❌ | ⚠️ | ⚠️ | ✅ |
| Unused code | ❌ | ✅ | ❌ | ✅ |

## Summary

- **Ruff**: Fast style checking ✅ (already using)
- **Python Compile**: Quick undefined name check ✅ (free, built-in)
- **Mypy**: Type checking 🎯 (INSTALL THIS - catches most runtime errors)
- **Pylint**: Comprehensive analysis 🔍 (optional but thorough)

**Bottom Line:** Install Mypy to catch errors like the `DatabaseConnectionPool` issue before runtime!
