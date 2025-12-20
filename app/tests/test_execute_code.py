import pytest
from core.runner import execute_code

# ==================== PYTHON ====================

@pytest.mark.asyncio
async def test_python_hello():
    """Python - oddiy print"""
    result = await execute_code(
        language="python",
        code='print("Hello World")',
        test_input="",
        expected_output="Hello World"
    )
    print(f"\n[PYTHON HELLO] Status: {result['status']}, Output: {result['stdout']}")
    assert result["status"] == "OK"
    assert result["is_accepted"] is True

@pytest.mark.asyncio
async def test_python_input():
    """Python - input bilan"""
    result = await execute_code(
        language="python",
        code="a, b = map(int, input().split())\nprint(a + b)",
        test_input="3 7",
        expected_output="10"
    )
    print(f"\n[PYTHON INPUT] Status: {result['status']}, Output: {result['stdout']}")
    assert result["status"] == "OK"
    assert result["is_accepted"] is True

@pytest.mark.asyncio
async def test_python_runtime_error():
    """Python - Runtime Error"""
    result = await execute_code(
        language="python",
        code="a, b = map(int, input().split())\nprint(a + b)",
        test_input="2",  # Faqat 1 ta son (2 kerak edi)
        expected_output="5"
    )
    print(f"\n[PYTHON RE] Status: {result['status']}, Error: {result['stderr'][:100]}")
    assert result["status"] == "RE"
