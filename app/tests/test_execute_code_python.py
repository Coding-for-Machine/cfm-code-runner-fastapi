import pytest
from core.runner import execute_code

@pytest.mark.asyncio
async def test_python_edge_cases():
    # 1. Bo'sh qatorlar bilan ishlash (Normalization check)
    res = await execute_code("python", "print('\\n\\nResult\\n  ')", "", "Result")
    assert res["status"] == "AC"
    

    # 3. Nolga bo'lish (RE)
    res = await execute_code("python", "print(1/0)", "", "")
    assert res["status"] == "RE"
    assert "ZeroDivisionError" in res["stderr"]

@pytest.mark.asyncio
async def test_js_ts_cases():
    # 1. TS - Interface va Type check
    code = "interface User {id: number}; const u: User = {id: 1}; console.log(u.id);"
    res = await execute_code("typescript", code, "", "1")
    assert res["status"] == "AC"

    # 2. JS - Stdin'dan bir nechta qator o'qish
    code = """
    const fs = require('fs');
    const input = fs.readFileSync(0, 'utf8').split('\\n');
    console.log(parseInt(input[0]) + parseInt(input[1]));
    """
    res = await execute_code("javascript", code, "5\n15", "20")
    assert res["status"] == "AC"

@pytest.mark.asyncio
async def test_system_limits():
    # 1. Time Limit Exceeded (TLE)
    # Python'da cheksiz sikl
    res = await execute_code("python", "import time\nwhile True: pass", "", "")
    assert res["status"] == "TLE"
    assert res["time"] >= 1.0 # 1 soniyadan oshishi kerak

    # 2. Wrong Answer (WA)
    res = await execute_code("python", "print(5)", "", "10")
    assert res["status"] == "WA"
    assert res["is_accepted"] is False
    assert res["message"] == "Wrong Answer"

@pytest.mark.asyncio
async def test_go_system():
    # 2. Go - Mas'uliyatsiz Panic (RE)
    code = """
    package main
    func main() { panic("Custom Error") }
    """
    res = await execute_code("go", code, "", "")
    assert res["status"] == "RE"
