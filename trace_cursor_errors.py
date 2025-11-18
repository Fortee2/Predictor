#!/usr/bin/env python3
"""
Diagnostic script to trace 'NoneType' object has no attribute 'cursor' errors.

This script identifies patterns in the codebase that can lead to NoneType cursor errors
and provides recommendations for fixing them.
"""

import re
import sys
from pathlib import Path


class CursorErrorTracer:
    def __init__(self, base_path="."):
        self.base_path = Path(base_path)
        self.issues = []

    def scan_files(self):
        """Scan Python files for problematic patterns"""
        print("=" * 80)
        print("CURSOR ERROR DIAGNOSTIC TOOL")
        print("=" * 80)
        print()

        # Scan for patterns
        self._find_direct_current_connection_usage()
        self._find_dao_without_base_dao()
        self._find_missing_connection_checks()
        self._find_commit_without_context()

        # Print summary
        self._print_summary()

    def _find_direct_current_connection_usage(self):
        """Find files using self.current_connection.cursor() directly"""
        print("\n[ISSUE 1] Direct usage of self.current_connection.cursor()")
        print("-" * 80)
        print("These files access cursor without checking if connection is None:")
        print()

        pattern = re.compile(r"self\.current_connection\.cursor\(\)")
        found = False

        for py_file in self.base_path.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue

            try:
                content = py_file.read_text()
                matches = pattern.finditer(content)

                for match in matches:
                    # Get line number
                    line_num = content[: match.start()].count("\n") + 1
                    lines = content.split("\n")

                    # Check if there's a None check nearby
                    has_check = False
                    for i in range(max(0, line_num - 5), min(len(lines), line_num + 2)):
                        if (
                            "if" in lines[i]
                            and "current_connection" in lines[i]
                            and ("is not None" in lines[i] or "!= None" in lines[i])
                        ):
                            has_check = True
                            break

                    if not has_check:
                        found = True
                        print(f"  📍 {py_file}:{line_num}")
                        print(f"     {lines[line_num - 1].strip()}")
                        self.issues.append(
                            {"type": "direct_cursor_usage", "file": str(py_file), "line": line_num, "severity": "HIGH"}
                        )

            except Exception as e:
                pass

        if not found:
            print("  ✅ No issues found")
        print()

    def _find_dao_without_base_dao(self):
        """Find DAO classes that don't extend BaseDAO"""
        print("\n[ISSUE 2] DAO classes not extending BaseDAO")
        print("-" * 80)
        print("These DAO classes may have connection management issues:")
        print()

        found = False

        for py_file in self.base_path.rglob("*_dao.py"):
            try:
                content = py_file.read_text()

                # Check if it has a DAO class
                class_pattern = re.compile(r"class\s+(\w+DAO)\s*(?:\(([^)]*)\))?:")
                matches = class_pattern.finditer(content)

                for match in matches:
                    class_name = match.group(1)
                    parent_class = match.group(2) if match.group(2) else None

                    if parent_class and "BaseDAO" not in parent_class:
                        found = True
                        line_num = content[: match.start()].count("\n") + 1
                        print(f"  📍 {py_file}:{line_num}")
                        print(f"     class {class_name}({parent_class}):")
                        self.issues.append(
                            {
                                "type": "missing_base_dao",
                                "file": str(py_file),
                                "line": line_num,
                                "class": class_name,
                                "severity": "HIGH",
                            }
                        )
                    elif not parent_class and class_name != "BaseDAO":
                        # Check if it uses self.current_connection
                        if "self.current_connection" in content:
                            found = True
                            line_num = content[: match.start()].count("\n") + 1
                            print(f"  📍 {py_file}:{line_num}")
                            print(f"     class {class_name}: (no parent)")
                            self.issues.append(
                                {
                                    "type": "missing_base_dao",
                                    "file": str(py_file),
                                    "line": line_num,
                                    "class": class_name,
                                    "severity": "HIGH",
                                }
                            )

            except Exception as e:
                pass

        if not found:
            print("  ✅ No issues found")
        print()

    def _find_missing_connection_checks(self):
        """Find usage of connection without proper None checks"""
        print("\n[ISSUE 3] Missing connection None checks")
        print("-" * 80)
        print("These locations should check if connection is None:")
        print()

        pattern = re.compile(r"connection\.cursor\(\)")
        found = False

        for py_file in self.base_path.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue

            try:
                content = py_file.read_text()
                matches = pattern.finditer(content)

                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    lines = content.split("\n")

                    # Check if it's within a with statement (context manager)
                    in_context = False
                    for i in range(max(0, line_num - 10), line_num):
                        if "with" in lines[i] and "connection" in lines[i]:
                            in_context = True
                            break

                    # Check for explicit None check
                    has_check = False
                    for i in range(max(0, line_num - 5), min(len(lines), line_num)):
                        if (
                            "if" in lines[i]
                            and "connection" in lines[i]
                            and ("is not None" in lines[i] or "!= None" in lines[i])
                        ):
                            has_check = True
                            break

                    if not in_context and not has_check:
                        found = True
                        print(f"  📍 {py_file}:{line_num}")
                        print(f"     {lines[line_num - 1].strip()}")
                        self.issues.append(
                            {"type": "missing_none_check", "file": str(py_file), "line": line_num, "severity": "MEDIUM"}
                        )

            except Exception as e:
                pass

        if not found:
            print("  ✅ No issues found")
        print()

    def _find_commit_without_context(self):
        """Find commit calls on current_connection outside context managers"""
        print("\n[ISSUE 4] Commit calls outside proper context")
        print("-" * 80)
        print("These commit calls may fail if connection is None:")
        print()

        pattern = re.compile(r"self\.current_connection\.commit\(\)")
        found = False

        for py_file in self.base_path.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue

            try:
                content = py_file.read_text()
                matches = pattern.finditer(content)

                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    lines = content.split("\n")

                    # Check if within get_connection context manager
                    in_context = False
                    for i in range(max(0, line_num - 15), line_num):
                        if "with" in lines[i] and "get_connection" in lines[i]:
                            in_context = True
                            break

                    if not in_context:
                        found = True
                        print(f"  📍 {py_file}:{line_num}")
                        print(f"     {lines[line_num - 1].strip()}")
                        self.issues.append(
                            {
                                "type": "commit_without_context",
                                "file": str(py_file),
                                "line": line_num,
                                "severity": "HIGH",
                            }
                        )

            except Exception as e:
                pass

        if not found:
            print("  ✅ No issues found")
        print()

    def _print_summary(self):
        """Print summary and recommendations"""
        print("\n" + "=" * 80)
        print("SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        print()

        high_severity = [i for i in self.issues if i["severity"] == "HIGH"]
        medium_severity = [i for i in self.issues if i["severity"] == "MEDIUM"]

        print(f"Total Issues Found: {len(self.issues)}")
        print(f"  - High Severity: {len(high_severity)}")
        print(f"  - Medium Severity: {len(medium_severity)}")
        print()

        if self.issues:
            print("RECOMMENDATIONS:")
            print("-" * 80)
            print()
            print("1. ALWAYS use the get_connection() context manager:")
            print("   ❌ BAD:  cursor = self.current_connection.cursor()")
            print("   ✅ GOOD: with self.get_connection() as connection:")
            print("               cursor = connection.cursor()")
            print()
            print("2. For DAO classes, extend BaseDAO:")
            print("   ❌ BAD:  class MyDAO:")
            print("   ✅ GOOD: class MyDAO(BaseDAO):")
            print()
            print("3. Never commit outside context managers:")
            print("   ❌ BAD:  self.current_connection.commit()")
            print("   ✅ GOOD: Use get_connection() which handles commits")
            print()
            print("4. Add connection None checks when necessary:")
            print("   if self.current_connection and self.current_connection.is_connected():")
            print("       cursor = self.current_connection.cursor()")
            print()
            print("5. Check base_dao.py - the finally block should NOT close connections")
            print("   when using a connection pool (connections should be returned to pool)")
            print()

            # Files that need immediate attention
            priority_files = {}
            for issue in high_severity:
                file_name = issue["file"]
                if file_name not in priority_files:
                    priority_files[file_name] = 0
                priority_files[file_name] += 1

            if priority_files:
                print("PRIORITY FILES (most issues):")
                print("-" * 80)
                sorted_files = sorted(priority_files.items(), key=lambda x: x[1], reverse=True)
                for file_path, count in sorted_files[:5]:
                    print(f"  📌 {file_path} ({count} high-severity issues)")
                print()
        else:
            print("✅ No issues found! Your code looks good.")
            print()


def main():
    """Main entry point"""
    base_path = sys.argv[1] if len(sys.argv) > 1 else "."

    tracer = CursorErrorTracer(base_path)
    tracer.scan_files()

    print("\nTo enable runtime debugging, add this to your code:")
    print("-" * 80)
    print("""
import logging
logging.basicConfig(level=logging.DEBUG)

# In BaseDAO.get_connection():
if self.current_connection is None:
    logger.debug("current_connection is None, getting new connection from pool")
else:
    logger.debug(f"Reusing current_connection: {self.current_connection}")
""")
    print()


if __name__ == "__main__":
    main()
