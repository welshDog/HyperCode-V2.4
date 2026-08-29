# agents/mission-executor/test_basic.py
"""
Basic test for mission-executor components.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that we can import the main components."""
    try:
        from models import ExecutionRequest, ExecutionResult, ExecutionStatus
        from agent_delegator import AgentDelegator
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_models():
    """Test that models can be instantiated."""
    try:
        from models import ExecutionRequest, ExecutionResult, ExecutionStatus

        # Test ExecutionRequest
        request = ExecutionRequest(
            mission_id="test_001",
            goal="Test goal",
            plan={"requested_actions": []}
        )
        assert request.mission_id == "test_001"
        assert request.goal == "Test goal"

        # Test ExecutionResult
        result = ExecutionResult(
            mission_id="test_001",
            status=ExecutionStatus.COMPLETED
        )
        assert result.mission_id == "test_001"
        assert result.status == ExecutionStatus.COMPLETED

        print("✓ Model tests successful")
        return True
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running basic tests for mission-executor...")

    tests = [
        test_imports,
        test_models
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        sys.exit(1)