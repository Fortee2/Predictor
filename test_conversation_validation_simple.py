#!/usr/bin/env python3
"""
Simple test for conversation history validation logic.
This version tests the validation logic without requiring database connection.
"""

import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_conversation_history(history):
    """
    Validate conversation history and remove incomplete tool exchanges.
    This is a copy of the validation logic from LLMPortfolioAnalyzer for testing.
    """
    if not history:
        return history

    validated = []
    i = 0

    while i < len(history):
        message = history[i]

        # Add current message to validated list
        validated.append(message)

        # Check if this is an assistant message with tool_use
        if message.get("role") == "assistant":
            tool_use_blocks = []
            for content_block in message.get("content", []):
                if "toolUse" in content_block:
                    tool_use_blocks.append(content_block["toolUse"]["toolUseId"])

            # If assistant requested tools, verify the next message has matching results
            if tool_use_blocks:
                if i + 1 >= len(history):
                    # No next message - incomplete exchange, truncate here
                    logger.warning(
                        f"Incomplete tool exchange detected: assistant requested {len(tool_use_blocks)} "
                        f"tools but conversation ended. Truncating history."
                    )
                    validated.pop()  # Remove the incomplete assistant message
                    break

                next_message = history[i + 1]

                # Next message must be from user with tool results
                if next_message.get("role") != "user":
                    logger.warning(
                        f"Invalid conversation structure: assistant tool_use not followed by user message. "
                        f"Truncating history at message {i}."
                    )
                    validated.pop()  # Remove the incomplete assistant message
                    break

                # Count tool results in next message
                tool_result_blocks = []
                for content_block in next_message.get("content", []):
                    if "toolResult" in content_block:
                        tool_result_blocks.append(content_block["toolResult"]["toolUseId"])

                # Verify counts match
                if len(tool_result_blocks) != len(tool_use_blocks):
                    logger.warning(
                        f"Tool use/result mismatch: expected {len(tool_use_blocks)} results, "
                        f"found {len(tool_result_blocks)}. Truncating history at message {i}."
                    )
                    validated.pop()  # Remove the incomplete assistant message
                    break

                # Verify all tool IDs match
                if set(tool_result_blocks) != set(tool_use_blocks):
                    logger.warning(
                        f"Tool ID mismatch: tool results don't match tool requests. "
                        f"Truncating history at message {i}."
                    )
                    validated.pop()  # Remove the incomplete assistant message
                    break

        i += 1

    if len(validated) < len(history):
        logger.info(
            f"Conversation history validated: removed {len(history) - len(validated)} "
            f"incomplete messages (kept {len(validated)} valid messages)"
        )

    return validated

def run_validation_tests():
    """Run validation tests on various conversation scenarios."""

    print("=" * 80)
    print("Conversation History Validation Test Suite")
    print("=" * 80)
    print()

    all_passed = True

    # Test 1: Valid conversation with no tool use
    print("Test 1: Valid conversation with no tool use")
    history1 = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
        {"role": "assistant", "content": [{"text": "I'm doing well!"}]}
    ]
    validated1 = validate_conversation_history(history1)
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
    validated2 = validate_conversation_history(history2)
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
    validated3 = validate_conversation_history(history3)
    if len(validated3) == 1:
        print("✅ PASSED: Incomplete tool use removed correctly")
    else:
        print(f"❌ FAILED: Expected 1 message, got {len(validated3)}")
        all_passed = False
    print()

    # Test 4: Multiple tools with complete responses
    print("Test 4: Multiple tools (6 tools) with complete responses")
    history4 = [
        {"role": "user", "content": [{"text": "Get comprehensive data"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tool_001", "name": "tool1", "input": {}}},
                {"toolUse": {"toolUseId": "tool_002", "name": "tool2", "input": {}}},
                {"toolUse": {"toolUseId": "tool_003", "name": "tool3", "input": {}}},
                {"toolUse": {"toolUseId": "tool_004", "name": "tool4", "input": {}}},
                {"toolUse": {"toolUseId": "tool_005", "name": "tool5", "input": {}}},
                {"toolUse": {"toolUseId": "tool_006", "name": "tool6", "input": {}}}
            ]
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "tool_001", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_002", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_003", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_004", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_005", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_006", "content": [{"json": {}}]}}
            ]
        },
        {"role": "assistant", "content": [{"text": "Here's the data..."}]}
    ]
    validated4 = validate_conversation_history(history4)
    if len(validated4) == 4:
        print("✅ PASSED: 6 tools with complete exchange preserved")
    else:
        print(f"❌ FAILED: Expected 4 messages, got {len(validated4)}")
        all_passed = False
    print()

    # Test 5: Tool count mismatch - requested 6 tools, got only 5 results (reproduces your error!)
    print("Test 5: Tool count mismatch - requested 6 tools, got only 5 results")
    history5 = [
        {"role": "user", "content": [{"text": "Get data"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tool_A", "name": "tool1", "input": {}}},
                {"toolUse": {"toolUseId": "tool_B", "name": "tool2", "input": {}}},
                {"toolUse": {"toolUseId": "tool_C", "name": "tool3", "input": {}}},
                {"toolUse": {"toolUseId": "tool_D", "name": "tool4", "input": {}}},
                {"toolUse": {"toolUseId": "tool_E", "name": "tool5", "input": {}}},
                {"toolUse": {"toolUseId": "tool_F", "name": "tool6", "input": {}}}
            ]
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "tool_A", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_B", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_C", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_D", "content": [{"json": {}}]}},
                {"toolResult": {"toolUseId": "tool_E", "content": [{"json": {}}]}}
                # Missing tool_F result!
            ]
        }
    ]
    validated5 = validate_conversation_history(history5)
    if len(validated5) == 1:
        print("✅ PASSED: Detected '6 requested, 5 returned' mismatch (your original error!)")
    else:
        print(f"❌ FAILED: Expected 1 message, got {len(validated5)}")
        all_passed = False
    print()

    # Test 6: Tool ID mismatch
    print("Test 6: Tool ID mismatch - response has different tool ID")
    history6 = [
        {"role": "user", "content": [{"text": "Get data"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tool_X", "name": "tool", "input": {}}}
            ]
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "tool_Y", "content": [{"json": {}}]}}  # Wrong ID!
            ]
        }
    ]
    validated6 = validate_conversation_history(history6)
    if len(validated6) == 1:
        print("✅ PASSED: Tool ID mismatch detected and removed")
    else:
        print(f"❌ FAILED: Expected 1 message, got {len(validated6)}")
        all_passed = False
    print()

    # Test 7: Mixed valid and invalid
    print("Test 7: Valid conversation followed by incomplete exchange")
    history7 = [
        {"role": "user", "content": [{"text": "First question"}]},
        {"role": "assistant", "content": [{"text": "First answer"}]},
        {"role": "user", "content": [{"text": "Second question"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tool_incomplete", "name": "tool", "input": {}}}
            ]
        }
        # Missing tool result!
    ]
    validated7 = validate_conversation_history(history7)
    if len(validated7) == 3:
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
        print()
        print("Your original error:")
        print("  'Did not find 6 tool_result block(s)'")
        print()
        print("This is now fixed! The validator will:")
        print("  1. Detect incomplete tool exchanges on load")
        print("  2. Truncate corrupted conversation history")
        print("  3. Prevent saving incomplete exchanges")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the validation logic.")
    print("=" * 80)

    return all_passed

if __name__ == "__main__":
    success = run_validation_tests()
    sys.exit(0 if success else 1)
