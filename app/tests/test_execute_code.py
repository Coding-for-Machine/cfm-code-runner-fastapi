import pytest
from core.runner import execute_code

# ==================== PYTHON TESTS ====================

@pytest.mark.asyncio
async def test_python_hello():
    """Python - oddiy print"""
    result = await execute_code(
        language="python",
        code='print("Hello World")',
        test_input="",
        expected_output="Hello World"
    )
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
    assert result["status"] == "OK"
    assert result["is_accepted"] is True

@pytest.mark.asyncio
async def test_python_runtime_error():
    """Python - Runtime Error"""
    result = await execute_code(
        language="python",
        code="a, b = map(int, input().split())\nprint(a + b)",
        test_input="2",  # Faqat 1 ta son, xato bo'ladi
        expected_output="5"
    )
    assert result["status"] == "RE"

# ==================== C TESTS ====================

@pytest.mark.asyncio
async def test_c_hello():
    """C - oddiy print"""
    code = """
    #include <stdio.h>
    int main() {
        printf("42");
        return 0;
    }
    """
    result = await execute_code(language="c", code=code, test_input="", expected_output="42")
    assert result["status"] == "OK"
    assert result["is_accepted"] is True

@pytest.mark.asyncio
async def test_c_input():
    """C - input bilan"""
    code = """
    #include <stdio.h>
    int main() {
        int a, b;
        scanf("%d %d", &a, &b);
        printf("%d", a + b);
        return 0;
    }
    """
    result = await execute_code(language="c", code=code, test_input="5 8", expected_output="13")
    assert result["status"] == "OK"
    assert result["is_accepted"] is True

# ==================== CPP TESTS ====================

@pytest.mark.asyncio
async def test_cpp_hello():
    """C++ - oddiy print"""
    code = """
    #include <iostream>
    int main() {
        std::cout << 100;
        return 0;
    }
    """
    result = await execute_code(language="cpp", code=code, test_input="", expected_output="100")
    assert result["status"] == "OK"
    assert result["is_accepted"] is True

# ==================== GO TESTS ====================

@pytest.mark.asyncio
async def test_go_input():
    """Go - input bilan"""
    code = """
    package main
    import "fmt"
    func main() {
        var n int
        fmt.Scan(&n)
        fmt.Println(n * 2)
    }
    """
    result = await execute_code(language="go", code=code, test_input="7", expected_output="14")
    assert result["status"] == "OK"
    assert result["is_accepted"] is True

# ==================== TYPESCRIPT TESTS ====================

@pytest.mark.asyncio
async def test_typescript_input():
    """TypeScript - input bilan"""
    code = """
    const fs = require('fs');
    const n = parseInt(fs.readFileSync(0,'utf8'));
    console.log(n * 3);
    """
    result = await execute_code(language="typescript", code=code, test_input="4", expected_output="12")
    assert result["status"] == "OK"
    assert result["is_accepted"] is True
