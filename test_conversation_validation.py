#!/usr/bin/env python3
"""
Test conversation history validation logic.

Tests various scenarios of incomplete tool exchanges to ensure
the validation correctly identifies and truncates corrupted histories.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from data.utility import DatabaseConnectionPool
from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer

def run_validation_tests():
    """Run validation tests on various conversation scenarios."""

    print("=" * 80)
    print("Conversation History Validation Test Suite")
    print("=" * 80)
    print()

    # Initialize analyzer
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME")

    pool = DatabaseConnectionPool(db_user, db_password, db_host, db_name)
    analyzer = LLMPortfolioAnalyzer(pool)

    all_passed = True

    # Test 1: Valid conversation with no tool use
    print("Test 1: Valid conversation with no tool use")
    history1 = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
        {"role": "assistant", "content": [{"text": "I'm doing well!"}]}
    ]
    validated1 = analyzer._validate_conversation_history(history1)
    if len(validated1) == 4:
        print("✅ PASSED: No changes to valid conversation")
    else:
        print(f"❌ FAILED: Expected 4 messages, got {len(validated1)}")
        all_passed = False
    print()

    # Test 2: Valid conversation with complete tool use
    print("Test 2: Valid conversation with complete tool use")
    history2 = [
        {"role": "user", "content": [{"text": "Get portfolio list"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool_123",
                        "name": "get_portfolio_list",
                        "input": {}
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tool_123",
                        "content": [{"json": {"portfolios": []}}]
                    }
                }
            ]
        },
        {"role": "assistant", "content": [{"text": "Here are your portfolios..."}]}
    ]
    validated2 = analyzer._validate_conversation_history(history2)
    if len(validated2) == 4:
        print("✅ PASSED: Valid tool exchange preserved")
    else:
        print(f"❌ FAILED: Expected 4 messages, got {len(validated2)}")
        all_passed = False
    print()

    # Test 3: Incomplete tool use - no response
    print("Test 3: Incomplete tool use - assistant requested tool but conversation ended")
    history3 = [
        {"role": "user", "content": [{"text": "Get portfolio list"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool_456",
                        "name": "get_portfolio_list",
                        "input": {}
                    }
                }
            ]
        }
        # Missing tool result!
    ]
    validated3 = analyzer._validate_conversation_history(history3)
    if len(validated3) == 1:
        print("✅ PASSED: Incomplete tool use removed correctly")
    else:
        print(f"❌ FAILED: Expected 1 message, got {len(validated3)}")
        all_passed = False
    print()

    # Test 4: Multiple tools with complete responses
    print("Test 4: Multiple tools with complete responses")
    history4 = [
        {"role": "user", "content": [{"text": "Get comprehensive data"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool_001",
                        "name": "get_portfolio_list",
                        "input": {}
                    }
                },
                {
                    "toolUse": {
                        "toolUseId": "tool_002",
                        "name": "get_cash_balance",
                        "input": {"portfolio_id": 1}
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tool_001",
                        "content": [{"json": {"portfolios": []}}]
                    }
                },
                {
                    "toolResult": {
                        "toolUseId": "tool_002",
                        "content": [{"json": {"cash_balance": 10000}}]
                    }
                }
            ]
        },
        {"role": "assistant", "content": [{"text": "Here's the data..."}]}
    ]
    validated4 = analyzer._validate_conversation_history(history4)
    if len(validated4) == 4:
        print("✅ PASSED: Multiple tools with complete exchange preserved")
    else:
        print(f"❌ FAILED: Expected 4 messages, got {len(validated4)}")
        all_passed = False
    print()

    # Test 5: Tool count mismatch - requested 2 tools, got 1 result
    print("Test 5: Tool count mismatch - requested 2 tools, got only 1 result")
    history5 = [
        {"role": "user", "content": [{"text": "Get data"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool_A",
                        "name": "get_portfolio_list",
                        "input": {}
                    }
                },
                {
                    "toolUse": {
                        "toolUseId": "tool_B",
                        "name": "get_cash_balance",
                        "input": {"portfolio_id": 1}
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tool_A",
                        "content": [{"json": {"portfolios": []}}]
                    }
                }
                # Missing tool_B result!
            ]
        }
    ]
    validated5 = analyzer._validate_conversation_history(history5)
    if len(validated5) == 1:
        print("✅ PASSED: Mismatched tool count detected and removed")
    else:
        print(f"❌ FAILED: Expected 1 message, got {len(validated5)}")
        all_passed = False
    print()

    # Test 6: Tool ID mismatch - different tool IDs in response
    print("Test 6: Tool ID mismatch - response has different tool ID")
    history6 = [
        {"role": "user", "content": [{"text": "Get data"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool_X",
                        "name": "get_portfolio_list",
                        "input": {}
                    }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tool_Y",  # Wrong ID!
                        "content": [{"json": {"portfolios": []}}]
                    }
                }
            ]
        }
    ]
    validated6 = analyzer._validate_conversation_history(history6)
    if len(validated6) == 1:
        print("✅ PASSED: Tool ID mismatch detected and removed")
    else:
        print(f"❌ FAILED: Expected 1 message, got {len(validated6)}")
        all_passed = False
    print()

    # Test 7: Mixed valid and invalid - should preserve valid part
    print("Test 7: Mixed conversation with valid part followed by incomplete exchange")
    history7 = [
        {"role": "user", "content": [{"text": "First question"}]},
        {"role": "assistant", "content": [{"text": "First answer"}]},
        {"role": "user", "content": [{"text": "Second question"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool_incomplete",
                        "name": "some_tool",
                        "input": {}
                    }
                }
            ]
        }
        # Missing tool result!
    ]
    validated7 = analyzer._validate_conversation_history(history7)
    if len(validated7) == 3:  # Should keep first 3 messages, remove incomplete tool use
        print("✅ PASSED: Preserved valid messages, removed incomplete exchange")
    else:
        print(f"❌ FAILED: Expected 3 messages, got {len(validated7)}")
        all_passed = False
    print()

    # Summary
    print("=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("The conversation validation logic is working correctly.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the validation logic.")
    print("=" * 80)

    return all_passed

if __name__ == "__main__":
    success = run_validation_tests()
    sys.exit(0 if success else 1)
